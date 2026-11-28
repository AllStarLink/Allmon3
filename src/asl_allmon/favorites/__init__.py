"""Persist named link favorites for each managed node."""

import fcntl
import json
import os
import re
import tempfile
from pathlib import Path


class FavoritesError(ValueError):
    """Invalid favorite or damaged favorites file."""


class FavoritesStore:
    def __init__(self, path, groups=None):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.groups = []
        self._members = {}
        for group in groups or []:
            if not isinstance(group, (list, tuple)) or len(group) < 2:
                raise FavoritesError("Each favorites group must contain at least two nodes")
            members = []
            for node in group:
                if not isinstance(node, str) or not re.fullmatch(r"[0-9]{1,10}", node):
                    raise FavoritesError("Favorites groups require numeric node IDs")
                node = str(int(node))
                if node in self._members or node in members:
                    raise FavoritesError("A node may belong to only one favorites group")
                members.append(node)
            members = tuple(members)
            self.groups.append(members)
            for node in members:
                self._members[node] = members

    def members(self, source):
        source = str(int(source))
        return self._members.get(source, (source,))

    def _group_nodes(self, data, source):
        nodes = {}
        for member in self.members(source):
            for node, label in data.get(member, {}).items():
                if node in nodes and nodes[node] != label:
                    raise FavoritesError(
                        f"Conflicting names for favorite {node}; resolve them before synchronizing")
                nodes[node] = label
        return nodes

    def synchronize(self):
        """Merge configured groups once, without deleting any unique entries.

        Conflicts abort the entire operation. All later edits use the same
        lock and atomic replacement, so deletes cannot resurrect stale copies.
        """
        if not self.groups:
            return
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._read()
            changed = False
            for group in self.groups:
                nodes = self._group_nodes(data, group[0])
                for member in group:
                    if data.get(member, {}) != nodes:
                        data[member] = dict(nodes)
                        changed = True
            if changed:
                self._write(data)

    def _read(self):
        try:
            with self.path.open(encoding="utf-8") as saved:
                data = json.load(saved)
        except FileNotFoundError:
            return {}
        except (UnicodeError, json.JSONDecodeError) as e:
            raise FavoritesError("Favorites file is damaged; no changes were made") from e
        if not isinstance(data, dict) or any(
            not isinstance(source, str) or not isinstance(nodes, dict)
            or any(not isinstance(node, str) or not isinstance(label, str)
                   for node, label in nodes.items())
            for source, nodes in data.items()
        ):
            raise FavoritesError("Favorites file is damaged; no changes were made")
        return data

    def list(self, source):
        nodes = self._group_nodes(self._read(), source)
        return [{"node": node, "label": label} for node, label in nodes.items()]

    def change(self, source, action, node, label=None, original_node=None):
        if not isinstance(node, str) or not re.fullmatch(r"[0-9]{1,10}", node):
            raise FavoritesError("Enter a valid numeric node ID")
        if action == "save":
            if not isinstance(label, str) or not label.strip() or len(label.strip()) > 80:
                raise FavoritesError("Enter a favorite name of 1 to 80 characters")
            label = label.strip()
            if any(ord(c) < 32 or ord(c) == 127 for c in label):
                raise FavoritesError("Favorite name cannot contain control characters")
            if original_node is not None and (
                not isinstance(original_node, str)
                or not re.fullmatch(r"[0-9]{1,10}", original_node)
            ):
                raise FavoritesError("Invalid original node ID")
        elif action != "delete":
            raise FavoritesError("Unknown favorite action")

        # A separate lock file stays valid across atomic replacements of the data file.
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._read()
            nodes = self._group_nodes(data, source)
            if action == "delete":
                if node not in nodes:
                    raise FavoritesError("Favorite not found")
                del nodes[node]
            else:
                if original_node is not None and original_node not in nodes:
                    raise FavoritesError("Favorite changed; reopen the dialog")
                if original_node != node and node in nodes:
                    raise FavoritesError("That node is already a favorite")
                if original_node is not None and original_node != node:
                    del nodes[original_node]
                nodes[node] = label

            for member in self.members(source):
                data[member] = dict(nodes)
            self._write(data)
            return [{"node": key, "label": value} for key, value in nodes.items()]

    def _write(self, data):
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=".favorites-", delete=False
            ) as temp:
                temp_name = temp.name
                os.chmod(temp.name, 0o640)
                json.dump(data, temp, indent=2, ensure_ascii=False)
                temp.write("\n")
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_name, self.path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
