"""Scheduled jobs must not transmit late after being queued before downtime."""
import test_audio
import unittest
from datetime import datetime, timedelta

class QueuedDeadlineTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_audio.AudioServiceTest.asyncSetUp
    async def test_already_queued_schedule_expires_after_downtime(self):
        asset = await self.service.ingest(self.wav, 'ID', '.wav')
        ident = self.service.create_schedule(1999, 'Delayed', ['asset:' + asset], 'once',
            run_at=(datetime.now().astimezone() + timedelta(hours=1)).isoformat())
        with self.service._db() as db:
            db.execute('UPDATE schedules SET next_at=? WHERE id=?', (datetime.now().timestamp()-1, ident))
        self.service._due_schedules()
        with self.service._db() as db:
            db.execute('UPDATE jobs SET scheduled_for=?', (datetime.now().timestamp()-600,))
        self.service.initialize()
        self.assertIsNone(self.service._claim_job(1999))
        self.assertEqual(self.service.snapshot([1999])['jobs'][0]['status'], 'missed')
        self.assertEqual(self.calls, [])
