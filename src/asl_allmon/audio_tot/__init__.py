"""Crash-recoverable, bounded playback-only app_rpt timeout leases.

COP 7/8 have audible TOTENA/TOTDIS telemetry on ASL; never use as probes.
Only leases that observed an enabled timer may enable it during recovery.
"""
import asyncio
from contextlib import asynccontextmanager
import fcntl
import json
import logging
import os
from pathlib import Path
import re
import time
import uuid

log = logging.getLogger(__name__)


class TimeoutGuardError(RuntimeError):
    pass


def parse_status(text, node):
    if not re.search(rf'NODE {node} STATISTICS', text):
        raise TimeoutGuardError('Cannot verify timeout node identity')
    state = re.search(r'^Selected system state\.+:\s*(\d+)\s*$', text, re.M)
    timer = re.search(r'^Time out timer\.+:\s*(ENABLED|DISABLED)\s*$', text, re.M)
    if not state or not timer:
        raise TimeoutGuardError('Cannot verify timeout protection state')
    return int(state[1]), timer[1] == 'ENABLED'


class TimeoutGuard:
    def __init__(self, directory, command, identities, clock=time.monotonic, boot_id=None):
        self.directory = Path(directory)
        self.command = command
        self.identities = identities
        self.clock = clock
        self.boot_id = boot_id or Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.owned = {}

    @asynccontextmanager
    async def _lock(self, node):
        self.directory.mkdir(mode=0o750, parents=True, exist_ok=True)
        with (self.directory / f'{node}.lock').open('a') as lock:
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    await asyncio.sleep(.1)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _path(self, node):
        return self.directory / f'{node}.json'

    def _sync_dir(self):
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _save(self, node, record):
        path = self._path(node)
        temp = path.with_suffix('.tmp')
        with temp.open('w') as out:
            os.chmod(temp, 0o640)
            json.dump(record, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
        self._sync_dir()

    def _load(self, node):
        path = self._path(node)
        if not path.exists():
            return None
        record = json.loads(path.read_text())
        if (record.get('node') != node or record.get('identity') != self.identities.get(node)
                or record.get('prior_enabled') is not True or type(record.get('state')) is not int):
            raise TimeoutGuardError('Timeout recovery journal identity mismatch; playback blocked')
        return record

    async def _status(self, node):
        return parse_status(await self.command(node, f'rpt stats {node}'), node)

    async def _set(self, node, enabled, state):
        async with asyncio.timeout(20):
            if (await self._status(node))[0] != state:
                raise TimeoutGuardError('System state changed; timeout journal retained for recovery')
            await self.command(node, f'rpt cmd {node} cop {7 if enabled else 8} 0')
            # rpt cmd is dispatched by the node loop, not synchronously by CLI.
            for _ in range(25):
                observed = await self._status(node)
                if observed == (state, enabled):
                    return
                if observed[0] != state:
                    break
                await asyncio.sleep(.2)
            raise TimeoutGuardError('Timeout state change was not verified; recovery required')

    async def _restore(self, node, record):
        state, enabled = await self._status(node)
        if state != record['state']:
            raise TimeoutGuardError('System state changed; timeout recovery pending for original state')
        if not enabled:
            await self._set(node, True, state)
        self._path(node).unlink()
        self._sync_dir()
        log.info('Restored timeout protection on node %s', node)

    async def recover(self, force=False):
        failures = []
        if not self.directory.exists():
            return
        for path in self.directory.glob('*.json'):
            if not re.fullmatch(r'[0-9]+', path.stem):
                failures.append(path.name)
                continue
            node = int(path.stem)
            try:
                async with self._lock(node):
                    record = self._load(node)
                    if record and (force or record['boot_id'] != self.boot_id or record['expires'] <= self.clock()):
                        await self._restore(node, record)
            except Exception:
                log.exception('Timeout recovery pending on node %s', node)
                failures.append(str(node))
        if failures:
            raise TimeoutGuardError('Timeout recovery unresolved for: ' + ', '.join(failures))

    async def before_playback(self, node, seconds):
        # A finite lease survives process death without an indefinite bypass.
        if not 0 < seconds <= 150:
            raise TimeoutGuardError('Invalid playback segment duration')
        async with self._lock(node):
            record = self._load(node)
            if node in self.owned:
                expected = self.owned[node]
                state, enabled = await self._status(node)
                if expected is None:  # Already disabled by operator: never take ownership.
                    if record or enabled:
                        raise TimeoutGuardError('Operator timeout state changed during playback')
                    return
                if (not record or record['token'] != expected or record['boot_id'] != self.boot_id
                        or record['expires'] <= self.clock() or state != record['state'] or enabled):
                    raise TimeoutGuardError('Playback timeout lease lost; further dispatch blocked')
            else:
                if record:
                    await self._restore(node, record)
                state, enabled = await self._status(node)
                if not enabled:
                    self.owned[node] = None
                    return
                record = {'node': node, 'identity': self.identities[node], 'state': state,
                          'prior_enabled': True, 'token': uuid.uuid4().hex, 'boot_id': self.boot_id}
                record['expires'] = self.clock() + seconds + 30
                self._save(node, record)  # WAL before any command that can disable TOT.
                self.owned[node] = record['token']
                await self._set(node, False, state)
            record['expires'] = self.clock() + seconds + 30
            self._save(node, record)

    async def announce(self, node, seconds, playback):
        """Short opening speech before any audible timeout-toggle command."""
        if node not in self.identities or not 0 < seconds <= 60:
            raise TimeoutGuardError('Invalid opening announcement')
        async with self._lock(node):
            # Do not bypass a pending recovery just to speak an intro.
            if node in self.owned or self._load(node):
                raise TimeoutGuardError('Timeout recovery pending; opening announcement blocked')
            await self._status(node)
            await playback()

    async def dispatch(self, node, seconds, playback):
        await self.before_playback(node, seconds)
        async with self._lock(node):
            record = self._load(node)
            token = self.owned[node]
            if token is not None:
                if (not record or record['token'] != token or record['expires'] <= self.clock()
                        or await self._status(node) != (record['state'], False)):
                    raise TimeoutGuardError('Playback timeout lease lost before dispatch')
                record['expires'] = self.clock() + seconds + 30
                self._save(node, record)
            # Serializes watchdog restoration against command dispatch. Production
            # playback AMI calls are limited to ten seconds; lease covers this too.
            await playback()

    async def finish(self, node):
        async with self._lock(node):
            token = self.owned.pop(node, None)
            record = self._load(node)
            if record:
                if token != record['token']:
                    raise TimeoutGuardError('Unexpected timeout lease owner; recovery required')
                await self._restore(node, record)


def ami_command(configs):
    from .. import ami_conn, ami_parser
    async def command(node, text):
        config = configs.nodes[configs.colo_nodes.get(node, node)]
        connection = ami_conn.AMI(config.host, config.port, config.user, config.password)
        async def execute():
            try:
                if not await connection.asl_create_connection():
                    raise TimeoutGuardError('Cannot connect to Asterisk for timeout protection')
                response = await ami_parser.AMIParser(connection).asl_cmd(text)
                if not response.startswith('OK:') or any(s in response for s in ['No such command', 'Usage:', 'Unknown node']):
                    raise TimeoutGuardError('Asterisk rejected timeout/playback command')
                return response
            finally:
                await connection.close()
        return await asyncio.wait_for(execute(), 10)
    return command


def identities(configs, nodes):
    return {n: f'{configs.nodes[configs.colo_nodes.get(n, n)].host}:{configs.nodes[configs.colo_nodes.get(n, n)].port}/{n}' for n in nodes}
