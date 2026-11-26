"""Command schedules use fake AMI only; never execute the weather script or RF."""
import asyncio
import json
import tempfile
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from aiohttp import web
from test_audio import audio
from test_audio_api import load_server

WEATHER = 'rpt cmd 59521 cmd /usr/lib/allmon3-weather/say-weather-59521'


class CommandSchedulerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dispatch = AsyncMock()
        self.play = AsyncMock(side_effect=AssertionError('Audio must not run for a command'))
        self.s = audio.AudioService(Path(self.tmp.name)/'s', Path(self.tmp.name)/'c',
                                    [59521, 529991], self.play, command_dispatch=self.dispatch)
        self.s.initialize()

    def schedule(self, recurrence='once', **overrides):
        args = dict(node=59521, name='Say weather', items=[], recurrence=recurrence,
                    run_at=(datetime.now().astimezone()+timedelta(days=2)).isoformat(),
                    weekday=4, local_time='14:00', kind='command', command=WEATHER)
        args.update(overrides)
        return self.s.create_schedule(**args)

    def due(self, ident, seconds=1):
        with self.s._db() as db:
            db.execute('UPDATE schedules SET next_at=? WHERE id=?', (datetime.now().timestamp()-seconds, ident))
        self.s._due_schedules()

    def test_exact_weather_roundtrip_dispatches_with_audio_off_and_no_tts(self):
        self.assertFalse(self.s.command_enabled())
        self.s.set_playback_enabled(False)
        self.s.set_command_enabled(True)
        ident = self.schedule()
        self.s.initialize()
        state = self.s.snapshot([59521])
        self.assertTrue(state['command_enabled'])
        self.assertFalse(state['playback_enabled'])
        self.assertEqual(state['schedules'][0]['command'], WEATHER)
        self.due(ident)
        job = self.s._claim_job(59521)
        with patch.object(self.s, 'prepare_stack_name', side_effect=AssertionError('No TTS')):
            asyncio.run(self.s._run_job(job))
        self.dispatch.assert_awaited_once_with(59521, WEATHER)
        self.play.assert_not_awaited()
        history = self.s.snapshot([59521])['jobs'][0]
        self.assertEqual(history['status'], 'dispatched')
        self.assertEqual(history['position'], 1)
        self.assertIsNotNone(history['finished_at'])
        self.assertIsNone(self.s._claim_job(59521))

    def test_worker_loop_dispatches_due_weather_schedule(self):
        self.s.set_command_enabled(True)
        self.s.set_playback_enabled(False)
        ident = self.schedule()
        with self.s._db() as db:
            db.execute('UPDATE schedules SET next_at=? WHERE id=?', (datetime.now().timestamp()-1, ident))
        async def exercise():
            reached = asyncio.Event()
            async def dispatch(node, command):
                self.assertEqual((node, command), (59521, WEATHER))
                reached.set()
            self.s.command_dispatch = dispatch
            self.s._collect_friday = AsyncMock()
            task = asyncio.create_task(self.s.run())
            try:
                await asyncio.wait_for(reached.wait(), 2)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        asyncio.run(exercise())
        self.assertEqual(self.s.snapshot([59521])['jobs'][0]['status'], 'dispatched')
        self.play.assert_not_awaited()

    def test_all_recurrences_skip_while_off_without_catchup(self):
        for recurrence in ('once', 'daily', 'weekly'):
            self.schedule(recurrence)
        with self.s._db() as db:
            db.execute('UPDATE schedules SET next_at=?', (datetime.now().timestamp()-1,))
        self.s.set_command_enabled(True)
        snapshot = self.s.snapshot([59521])
        self.assertEqual(len(snapshot['jobs']), 3)
        self.assertTrue(all(j['status'] == 'missed' for j in snapshot['jobs']))
        for schedule in snapshot['schedules']:
            self.assertEqual(bool(schedule['enabled']), schedule['recurrence'] != 'once')
            if schedule['enabled']:
                self.assertGreater(schedule['next_at'], datetime.now().timestamp())
        self.assertIsNone(self.s._claim_job(59521))
        self.dispatch.assert_not_awaited()

    def test_toggles_only_cancel_their_own_pending_kind(self):
        self.s.set_command_enabled(True)
        audio_job = self.s.enqueue(59521, 'News', ['source:aan'])
        self.due(self.schedule())
        self.s.set_playback_enabled(False)
        jobs = self.s.snapshot([59521])['jobs']
        self.assertEqual(next(j for j in jobs if j['id'] == audio_job)['status'], 'cancelled')
        self.assertEqual(next(j for j in jobs if j['kind'] == 'command')['status'], 'pending')
        self.s.set_playback_enabled(True)
        new_audio = self.s.enqueue(59521, 'New audio', ['source:aan'])
        self.s.set_command_enabled(False)
        self.assertEqual(self.s._claim_job(59521)['id'], new_audio)
        self.assertEqual(next(j for j in self.s.snapshot([59521])['jobs'] if j['kind'] == 'command')['status'], 'cancelled')

    def test_deadlines_at_due_claim_and_dispatch(self):
        self.s.set_command_enabled(True)
        self.due(self.schedule(), 301)
        self.assertEqual(self.s.snapshot([59521])['jobs'][0]['status'], 'missed')
        self.due(self.schedule())
        with self.s._db() as db:
            db.execute("UPDATE jobs SET scheduled_for=? WHERE status='pending'", (datetime.now().timestamp()-301,))
        self.assertIsNone(self.s._claim_job(59521))
        self.due(self.schedule())
        job = self.s._claim_job(59521)
        job['scheduled_for'] = datetime.now().timestamp()-301
        asyncio.run(self.s._run_job(job))
        self.assertTrue(all(j['status'] == 'missed' for j in self.s.snapshot([59521])['jobs']))
        self.dispatch.assert_not_awaited()

    def test_disable_between_claim_and_dispatch_and_restart_no_replay(self):
        self.s.set_command_enabled(True)
        self.due(self.schedule())
        job = self.s._claim_job(59521)
        self.s.set_command_enabled(False)
        asyncio.run(self.s._run_job(job))
        self.dispatch.assert_not_awaited()
        self.s.set_command_enabled(True)
        self.due(self.schedule())
        job = self.s._claim_job(59521)
        self.s.initialize()
        self.assertEqual(next(j for j in self.s.snapshot([59521])['jobs'] if j['id']==job['id'])['status'], 'interrupted')
        self.assertIsNone(self.s._claim_job(59521))

    def test_node_scope_and_single_line_validation(self):
        for command in (WEATHER.replace('59521', '529991', 1), WEATHER+'\ncore stop now',
                        WEATHER+'\r\nAction: Command', WEATHER+'\x00', 'core stop now',
                        '/bin/sh -c true', 'rpt cmd 595210 cmd foo', 'rpt cmd 59521 ',
                        None, ['bad'], 'rpt cmd 59521 cmd '+('a'*512)):
            with self.subTest(command=command), self.assertRaises(audio.AudioError):
                self.schedule(command=command)
        for overrides in ({'node': 99999}, {'kind': 'shell'}, {'items': ['source:aan']},
                          {'kind': 'audio', 'items': ['source:aan']}):
            with self.subTest(overrides=overrides), self.assertRaises(audio.AudioError):
                self.schedule(**overrides)
        self.schedule(command='rpt fun 59521 *80')
        for value in (None, 1, 0, 'false', []):
            with self.assertRaises(audio.AudioError):
                self.s.set_command_enabled(value)
        self.assertFalse(self.s.command_enabled())

    def test_failure_and_cancellation_record_uncertain_outcome_without_retry(self):
        self.s.set_command_enabled(True)
        self.dispatch.side_effect = RuntimeError('AMI unavailable')
        self.due(self.schedule())
        asyncio.run(self.s._run_job(self.s._claim_job(59521)))
        self.assertEqual(self.s.snapshot([59521])['jobs'][0]['status'], 'failed')
        self.dispatch.side_effect = asyncio.CancelledError()
        self.due(self.schedule())
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(self.s._run_job(self.s._claim_job(59521)))
        self.assertIn('interrupted', [j['status'] for j in self.s.snapshot([59521])['jobs']])
        self.assertIsNone(self.s._claim_job(59521))
        self.assertEqual(self.dispatch.await_count, 2)

    def test_delete_and_scoped_snapshot(self):
        ident = self.schedule()
        self.assertEqual(self.s.snapshot([529991])['schedules'], [])
        with self.assertRaises(audio.AudioError):
            self.s.delete_schedule(ident, [529991])
        self.s.delete_schedule(ident, [59521])
        self.assertEqual(self.s.snapshot([59521])['schedules'], [])

    def test_legacy_database_migration_preserves_audio_rows_and_master(self):
        ident = self.s.create_schedule(59521, 'Legacy audio', ['source:aan'], 'daily', local_time='14:00')
        self.s.enqueue(59521, 'Legacy queue', ['source:aan'])
        self.s.set_playback_enabled(False)
        with self.s._db() as db:
            for table in ('schedules', 'jobs'):
                db.execute(f'ALTER TABLE {table} DROP COLUMN kind')
                db.execute(f'ALTER TABLE {table} DROP COLUMN command')
            db.execute("DELETE FROM settings WHERE key='command_enabled'")
        self.s.initialize()
        self.s.initialize()
        state = self.s.snapshot([59521])
        self.assertEqual(state['schedules'][0]['id'], ident)
        self.assertEqual(state['schedules'][0]['kind'], 'audio')
        self.assertEqual(state['schedules'][0]['items'], ['source:aan'])
        self.assertEqual(state['jobs'][0]['kind'], 'audio')
        self.assertFalse(state['command_enabled'])
        self.assertFalse(state['playback_enabled'])


class CommandAPITest(unittest.TestCase):
    def test_schedule_and_master_authorization_and_actual_ami_adapter(self):
        Server = load_server()
        with tempfile.TemporaryDirectory() as temp:
            nodes = types.SimpleNamespace(all_nodes=[59521,529991], colo_nodes={}, nodes={
                n: types.SimpleNamespace(host='localhost', port=5038) for n in [59521,529991]})
            security = types.SimpleNamespace(session_db={'valid': types.SimpleNamespace(user='ham')},
                                             restricted_users={'ham'}, restrictdb={'ham59521'})
            server = Server(None, nodes, security)
            server.audio.state = Path(temp)/'state'
            server.audio.originals = server.audio.state/'originals'
            server.audio.converted = Path(temp)/'cache'
            server.audio.db_path = server.audio.state/'audio.sqlite3'
            server.audio.initialize()
            class Request:
                session = {}; headers = {}; host = 'radio.example'; content_type = 'application/json'
                match_info = {'action': 'schedule'}
                payload = dict(node=59521, name='Weather', kind='command', command=WEATHER,
                               recurrence='daily', local_time='14:00')
                async def json(self): return self.payload
            r = Request(); mutate = server._AnnouncementsAddon__audio_mutation
            with self.assertRaises(web.HTTPForbidden): asyncio.run(mutate(r))
            r.session = {'auth_sess': 'valid'}
            r.headers = {'Origin': 'https://evil.example'}
            with self.assertRaises(web.HTTPForbidden): asyncio.run(mutate(r))
            r.headers = {'Origin': 'https://radio.example'}
            r.payload['node'] = 529991
            with self.assertRaises(web.HTTPForbidden): asyncio.run(mutate(r))
            r.payload['node'] = 59521
            r.payload['command'] = WEATHER.replace('59521', '529991', 1)
            self.assertEqual(asyncio.run(mutate(r)).status, 400)
            r.payload['command'] = WEATHER
            self.assertEqual(asyncio.run(mutate(r)).status, 200)
            self.assertEqual(server.audio.snapshot([59521])['schedules'][0]['command'], WEATHER)
            r.match_info = {'action': 'command-enable'}
            r.payload = {'node':59521, 'enabled':True}
            with self.assertRaises(web.HTTPForbidden): asyncio.run(mutate(r))
            security.restrictdb.add('ham529991')
            r.headers = {'Origin': 'https://evil.example'}
            with self.assertRaises(web.HTTPForbidden): asyncio.run(mutate(r))
            r.headers = {'Origin': 'https://radio.example'}
            self.assertEqual(asyncio.run(mutate(r)).status, 200)
            self.assertTrue(server.audio.command_enabled())
            # Real add-in adapter, fake network transport. Exact user command.
            ami = AsyncMock()
            with patch('asl_allmon.announcements.audio_tot.ami_command', return_value=ami):
                asyncio.run(server.audio.command_dispatch(59521, WEATHER))
            ami.assert_awaited_once_with(59521, WEATHER)
