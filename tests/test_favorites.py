"""Regression checks for favorites persistence and edits."""

import importlib.util
import tarfile
import tempfile
import unittest
from pathlib import Path
from favorites_cli import cli_config

spec = importlib.util.spec_from_file_location(
    "allmon_favorites", Path(__file__).resolve().parents[1] / "src/asl_allmon/favorites/__init__.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FavoritesStore = module.FavoritesStore
FavoritesError = module.FavoritesError


class FavoritesTest(unittest.TestCase):
    def test_configuration_backup_restores_favorites_and_group_edits(self):
        # Node backups capture /etc/allmon3, not application state in /var/lib.
        relative = Path(cli_config()["favorites_config_file"]).relative_to("/etc/allmon3")
        self.assertNotEqual(relative.parent, Path("."))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "original/etc/allmon3"
            path = config / relative
            path.parent.mkdir(parents=True, mode=0o750)
            other_config = config / "web.ini"
            other_config.write_text("[favorites-groups]\nsite = 1999,2000\n")
            store = FavoritesStore(path, [["1999", "2000"]])
            store.change(1999, "save", "111", "Keep")
            store.change(2000, "save", "222", "Delete before backup")
            store.change(1999, "delete", "222")

            archive = root / "node-config-backup.tar"
            with tarfile.open(archive, "w") as backup:
                backup.add(config, arcname="etc/allmon3")
            with tarfile.open(archive) as backup:
                backup.extractall(root / "restored", filter="data")

            restored_path = root / "restored/etc/allmon3" / relative
            self.assertEqual(restored_path.read_bytes(), path.read_bytes())
            self.assertEqual(restored_path.stat().st_mode & 0o777, 0o640)
            restored = FavoritesStore(restored_path, [["1999", "2000"]])
            restored.synchronize()
            self.assertEqual(restored.list(2000), [{"node": "111", "label": "Keep"}])
            restored.change(2000, "save", "333", "Renamed", original_node="111")
            self.assertEqual(restored.list(1999), [{"node": "333", "label": "Renamed"}])
            self.assertEqual(other_config.read_text(), "[favorites-groups]\nsite = 1999,2000\n")

    def test_save_rename_delete_and_reload_per_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "favorites.json"
            store = FavoritesStore(path)
            self.assertEqual(store.list(1999), [])
            store.change(1999, "save", "62154", "Starbase 4")
            store.change(2000, "save", "3002560", "WINS 100%")
            self.assertEqual(FavoritesStore(path).list(1999), [
                {"node": "62154", "label": "Starbase 4"}])
            store.change(1999, "save", "62155", "New name", original_node="62154")
            self.assertEqual(store.list(1999), [
                {"node": "62155", "label": "New name"}])
            store.change(1999, "delete", "62155")
            self.assertEqual(store.list(1999), [])
            self.assertEqual(store.list(2000), [
                {"node": "3002560", "label": "WINS 100%"}])
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_conflict_and_invalid_input_do_not_erase_favorites(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FavoritesStore(Path(temp_dir) / "favorites.json")
            store.change(1999, "save", "111", "First")
            store.change(1999, "save", "222", "Second")
            with self.assertRaisesRegex(FavoritesError, "already a favorite"):
                store.change(1999, "save", "222", "Oops", original_node="111")
            with self.assertRaisesRegex(FavoritesError, "numeric node"):
                store.change(1999, "save", "*3222", "Invalid")
            with self.assertRaisesRegex(FavoritesError, "Favorite changed"):
                store.change(1999, "save", "333", "Stale", original_node="444")
            self.assertEqual(store.list(1999), [
                {"node": "111", "label": "First"},
                {"node": "222", "label": "Second"}])

    def test_damaged_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "favorites.json"
            path.write_text("{not json")
            store = FavoritesStore(path)
            with self.assertRaises(FavoritesError):
                store.change(1999, "save", "111", "New")
            self.assertEqual(path.read_text(), "{not json")

class FavoritesGroupsTest(unittest.TestCase):
    def test_union_bidirectional_edits_deletes_and_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'favorites.json'
            independent = FavoritesStore(path)
            independent.change(1999, 'save', '111', 'First')
            independent.change(2000, 'save', '222', 'Second')
            independent.change(2001, 'save', '333', 'Separate')
            store = FavoritesStore(path, [['1999', '2000']])
            store.synchronize()
            self.assertEqual(len(store.list(1999)), 2)
            self.assertEqual(store.list(1999), store.list(2000))
            store.change(2000, 'save', '444', 'Renamed', original_node='111')
            self.assertIn({'node': '444', 'label': 'Renamed'}, store.list(1999))
            store.change(1999, 'delete', '222')
            store = FavoritesStore(path, [['1999', '2000']])
            store.synchronize()
            self.assertEqual(store.list(2000), [{'node': '444', 'label': 'Renamed'}])
            self.assertEqual(store.list(2001), [{'node': '333', 'label': 'Separate'}])
            # Removing the group leaves both nodes with the last synchronized copy.
            self.assertEqual(FavoritesStore(path).list(1999), FavoritesStore(path).list(2000))

    def test_conflicting_startup_is_atomic_for_all_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'favorites.json'
            store = FavoritesStore(path)
            store.change(1999, 'save', '111', 'First')
            store.change(2001, 'save', '222', 'One label')
            store.change(2002, 'save', '222', 'Another label')
            original = path.read_bytes()
            grouped = FavoritesStore(path, [['1999', '2000'], ['2001', '2002']])
            with self.assertRaisesRegex(FavoritesError, 'Conflicting names'):
                grouped.synchronize()
            self.assertEqual(path.read_bytes(), original)

    def test_validation_and_failed_group_edit_preserve_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'favorites.json'
            for groups in ([['1999']], [['1999', '1999']], [['1999', 'bad']],
                           [['1999', '2000'], ['2000', '2001']], [['1999', '01999']]):
                with self.assertRaises(FavoritesError):
                    FavoritesStore(path, groups)
            store = FavoritesStore(path, [['1999', '2000']])
            store.change(1999, 'save', '111', 'First')
            original = path.read_bytes()
            with self.assertRaises(FavoritesError):
                store.change(2000, 'save', '222', 'Stale edit', original_node='333')
            self.assertEqual(path.read_bytes(), original)
            path.write_text('{invalid')
            with self.assertRaises(FavoritesError):
                store.synchronize()
            self.assertEqual(path.read_text(), '{invalid')

    def test_concurrent_writes_from_both_nodes_do_not_lose_updates(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'favorites.json'
            def add(n):
                store = FavoritesStore(path, [['1999', '2000']])
                store.change(1999 if n % 2 else 2000, 'save', str(10000+n), f'Favorite {n}')
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(add, range(20)))
            store = FavoritesStore(path, [['1999', '2000']])
            self.assertEqual(len(store.list(1999)), 20)
            self.assertEqual(store.list(1999), store.list(2000))


if __name__ == "__main__":
    unittest.main()
