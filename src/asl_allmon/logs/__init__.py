"""Bounded local log access and per-node connection-hook recording controls."""
import asyncio
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile

DEFAULT_LOG_SETTINGS = '/etc/allmon3/logging/nodes.json'

class LogError(ValueError):
    pass

class LogService:
    def __init__(self, local_nodes, manifest='/etc/allmon3/logging-nodes.json',
                 settings=DEFAULT_LOG_SETTINGS):
        self.settings = Path(settings)
        try:
            configured = json.loads(Path(manifest).read_text())['nodes']
            if not isinstance(configured, list) or not all(isinstance(n, str) and re.fullmatch(r'[0-9]{1,10}', n) for n in configured):
                raise ValueError('Invalid logging nodes')
        except FileNotFoundError:
            configured = []
        self.nodes = sorted(set(configured) & {str(n) for n in local_nodes})
        self.host_nodes = {str(n) for n in local_nodes}
        self.reader_lock = asyncio.Semaphore(2)

    def _settings(self):
        try:
            if self.settings.stat().st_size > 65536:
                raise LogError('Logging settings are too large')
            data = json.loads(self.settings.read_text())
            if not isinstance(data, dict) or any(not re.fullmatch(r'[0-9]{1,10}', k) or type(v) is not bool for k, v in data.items()):
                raise LogError('Invalid logging settings')
            return data
        except FileNotFoundError:
            return {}
        except (ValueError, OSError) as exc:
            raise LogError('Unable to read logging settings') from exc

    def snapshot(self, allowed):
        settings = self._settings()
        allowed = set(map(str, allowed))
        return {'nodes': [{'node': n, 'enabled': settings.get(n, True)} for n in self.nodes if n in allowed],
                'messages_allowed': bool(self.host_nodes) and self.host_nodes <= allowed,
                'refresh_seconds': 5}

    def set_enabled(self, node, enabled):
        if node not in self.nodes or type(enabled) is not bool:
            raise LogError('Choose a supported node and a boolean enabled value')
        # Separate stable lock inode: atomic settings replacement is safe across processes.
        with open(self.settings.parent / '.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._settings()
            data[node] = enabled
            temp = None
            try:
                fd, temp = tempfile.mkstemp(prefix='.nodes-', dir=self.settings.parent)
                with os.fdopen(fd, 'w') as stream:
                    os.fchmod(stream.fileno(), 0o644)  # hook (asterisk) needs read-only access
                    json.dump(data, stream, sort_keys=True)
                    stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
                os.replace(temp, self.settings)
                dirfd = os.open(self.settings.parent, os.O_DIRECTORY)
                try: os.fsync(dirfd)
                finally: os.close(dirfd)
            finally:
                if temp and os.path.exists(temp): os.unlink(temp)
        return {'node': node, 'enabled': enabled}

    async def read(self, kind, node, limit):
        if kind not in ('connections', 'messages') or not 1 <= limit <= 1000:
            raise LogError('Invalid log selection or line count')
        if kind == 'connections' and node not in self.nodes:
            raise LogError('Unknown logging node')
        async with self.reader_lock:
            proc = await asyncio.create_subprocess_exec(
                '/usr/bin/sudo', '-n', '-u', 'asterisk', '--',
                '/usr/lib/allmon3/log-reader', kind, node if kind == 'connections' else '-', str(limit),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill(); await proc.communicate()
                raise LogError('Log read timed out')
            if proc.returncode:
                raise LogError('Log unavailable; check the installed log reader permissions')
            return json.loads(out)
