"""Persistent master gating; no playback callbacks or radio commands."""
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from test_audio import audio


class MasterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        async def forbidden(*args):
            raise AssertionError('No playback permitted in master tests')
        self.s = audio.AudioService(Path(self.tmp.name)/'s', Path(self.tmp.name)/'c', [1999,2000], forbidden)
        self.s.initialize()

    def test_default_enabled_disabled_persists_and_permissions_are_scoped(self):
        self.assertTrue(self.s.playback_enabled())
        self.assertFalse(self.s.snapshot([1999])['can_manage_playback'])
        self.assertTrue(self.s.snapshot([1999,2000])['can_manage_playback'])
        self.s.set_playback_enabled(False)
        self.s.initialize()
        self.assertFalse(self.s.playback_enabled())
        self.assertFalse(self.s.snapshot([1999])['playback_enabled'])

    def test_disable_cancels_pending_blocks_queue_and_claim(self):
        ident = self.s.enqueue(1999,'queued',['source:aan'])
        self.s.set_playback_enabled(False)
        self.assertIsNone(self.s._claim_job(1999))
        self.assertEqual(self.s.snapshot([1999])['jobs'][0]['status'],'cancelled')
        with self.assertRaises(audio.AudioError):
            self.s.enqueue(1999,'blocked',['source:aan'])
        self.s.set_playback_enabled(True)
        self.assertIsNone(self.s._claim_job(1999))
        self.s.enqueue(1999,'new',['source:aan'])
        self.assertIsNotNone(self.s._claim_job(1999))

    def test_disabled_schedules_advance_without_transmit_or_catchup(self):
        for recurrence in ['once','daily','weekly']:
            self.s.create_schedule(1999,recurrence,['source:aan'],recurrence,
                run_at=(datetime.now().astimezone()+timedelta(days=2)).isoformat(), weekday=4,local_time='14:00')
        self.s.set_playback_enabled(False)
        with self.s._db() as db:
            db.execute('UPDATE schedules SET next_at=?',(datetime.now().timestamp()-1,))
        # Enabling before the worker's next pass must not replay starts missed while off.
        self.s.set_playback_enabled(True)
        state=self.s.snapshot([1999])
        self.assertEqual(len(state['jobs']),3)
        self.assertTrue(all(j['status']=='missed' for j in state['jobs']))
        for schedule in state['schedules']:
            self.assertEqual(schedule['enabled'],int(schedule['recurrence']!='once'))
            if schedule['enabled']:self.assertGreater(schedule['next_at'],datetime.now().timestamp())
        self.assertIsNone(self.s._claim_job(1999))

    def test_strict_boolean(self):
        for value in [None,'false',0,1,[],{}]:
            with self.assertRaises(audio.AudioError):self.s.set_playback_enabled(value)
        self.assertTrue(self.s.playback_enabled())
