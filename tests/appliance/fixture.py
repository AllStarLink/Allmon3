"""Generation/storage-only fixture; never starts a worker or sends AMI."""
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import wave
from asl_allmon.announcement_config import AnnouncementConfig
from asl_allmon.audio import AudioService

async def no_dispatch(*args):
    raise AssertionError('No dispatch permitted in lifecycle fixture')

settings = AnnouncementConfig()
service = AudioService(settings.state_dir, settings.cache_dir, [1999], no_dispatch, settings=settings,
                       command_dispatch=no_dispatch)
service.initialize()
if sys.argv[1] == 'seed':
    service.set_playback_enabled(False)
    service.set_command_enabled(False)
    source = Path(settings.state_dir) / 'fixture.wav'
    with wave.open(str(source), 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000)
        stream.writeframes(b'\0\0' * 8000)
    asset = asyncio.run(service.ingest(source, 'Disposable silent fixture', '.wav'))
    service.create_schedule(1999, 'Retained disabled fixture', ['asset:' + asset], 'once',
                            run_at='2099-01-01T00:00:00+00:00')
    # This uses the real packaged Piper, but generation only; no playback worker.
    output = asyncio.run(service.prepare_stack_name('Disposable package validation'))
    assert output.stat().st_size > 8000
    print('Packaged Piper render:', output.stat().st_size, 'bytes', file=sys.stderr)
with sqlite3.connect(service.db_path) as db:
    data = {table: db.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall()
            for table in ('assets', 'schedules', 'settings', 'sources', 'jobs')}
data['originals'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(service.originals.iterdir()) if p.is_file()}
assert data['assets'] and data['schedules'] and not data['jobs']
assert dict(data['settings']) == {'command_enabled': '0', 'playback_enabled': '0'}
print(json.dumps(data, sort_keys=True))
