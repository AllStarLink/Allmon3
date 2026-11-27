"""Daily calendar recurrence and persistent non-transmitting scheduling checks."""
import importlib.util
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('daily_audio', Path(__file__).resolve().parents[1] / 'src/asl_allmon/audio/__init__.py')
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


def stamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=audio.ZoneInfo('America/Los_Angeles')).timestamp()


class DailyTests(unittest.TestCase):
    def test_today_tomorrow_and_year_boundary(self):
        for after, expected in [('2026-12-31T13:00', '2026-12-31T14:00'),
                                ('2026-12-31T14:00', '2027-01-01T14:00'),
                                ('2026-12-31T23:59', '2027-01-01T14:00')]:
            self.assertEqual(audio.ScheduleClock('America/Los_Angeles').daily_next('14:00', stamp(after)), stamp(expected))

    def test_calendar_time_survives_dst_offset_changes(self):
        for start, end, hours in [('2026-03-07T14:00', '2026-03-08T14:00', 23),
                                  ('2026-10-31T14:00', '2026-11-01T14:00', 25)]:
            result = audio.ScheduleClock('America/Los_Angeles').daily_next('14:00', stamp(start))
            self.assertEqual(result, stamp(end))
            self.assertEqual(result - stamp(start), hours * 3600)

    def test_spring_gap_skipped_and_autumn_fold_not_repeated(self):
        self.assertEqual(audio.ScheduleClock('America/Los_Angeles').daily_next('02:30', stamp('2026-03-07T02:30')), stamp('2026-03-09T02:30'))
        self.assertEqual(audio.ScheduleClock('America/Los_Angeles').daily_next('01:30', stamp('2026-11-01T01:30')), stamp('2026-11-02T01:30'))

    def test_invalid_times_are_user_errors(self):
        for value in [None, 1400, '', '24:00', '14:60', '2:00', '14:00:60']:
            with self.subTest(value=value), self.assertRaises(audio.AudioError):
                audio.ScheduleClock('America/Los_Angeles').daily_next(value)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        async def forbidden(*args):
            raise AssertionError('Scheduling tests must never play audio')
        self.service = audio.AudioService(Path(self.tmp.name) / 'state', Path(self.tmp.name) / 'cache', [1999], forbidden)
        self.service.clock = audio.ScheduleClock('America/Los_Angeles')
        self.service.initialize()

    def create(self):
        return self.service.create_schedule(1999, 'Daily bulletin', ['source:aan'], 'daily', local_time='14:00', weekday=4)

    def test_persistence_and_scoped_deletion(self):
        ident = self.create()
        self.service.initialize()
        row = self.service.snapshot([1999])['schedules'][0]
        self.assertEqual((row['recurrence'], row['local_time'], row['weekday'], row['enabled']), ('daily', '14:00', None, 1))
        with self.assertRaises(audio.AudioError):
            self.service.delete_schedule(ident, [2000])
        self.service.delete_schedule(ident, [1999])
        self.assertEqual(self.service.snapshot([1999])['schedules'], [])

    def run_due(self, due, now):
        with self.service._db() as db:
            db.execute('UPDATE schedules SET next_at=?', (stamp(due),))
        with patch.object(audio, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime.fromtimestamp(stamp(now), audio.ZoneInfo('America/Los_Angeles'))
            self.service._due_schedules()
            self.service._due_schedules()
        return self.service.snapshot([1999])

    def test_due_daily_enqueues_once_and_advances(self):
        self.create()
        state = self.run_due('2026-11-20T14:00', '2026-11-20T14:01')
        self.assertEqual(len(state['jobs']), 1)
        self.assertEqual(state['jobs'][0]['status'], 'pending')
        self.assertEqual(state['jobs'][0]['scheduled_for'], stamp('2026-11-20T14:00'))
        self.assertEqual(state['schedules'][0]['next_at'], stamp('2026-11-21T14:00'))
        self.assertEqual(state['schedules'][0]['enabled'], 1)

    def test_downtime_skips_backlog_and_keeps_next_daily_run(self):
        self.create()
        state = self.run_due('2026-11-17T14:00', '2026-11-20T14:10')
        self.assertEqual(len(state['jobs']), 1)
        self.assertEqual(state['jobs'][0]['status'], 'missed')
        self.assertEqual(state['schedules'][0]['next_at'], stamp('2026-11-21T14:00'))

    def test_already_queued_daily_expires_before_dispatch(self):
        self.create()
        self.run_due('2026-11-20T14:00', '2026-11-20T14:01')
        with patch.object(audio, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime.fromtimestamp(stamp('2026-11-20T14:06'), audio.ZoneInfo('America/Los_Angeles'))
            self.assertIsNone(self.service._claim_job(1999))
        self.assertEqual(self.service.snapshot([1999])['jobs'][0]['status'], 'missed')


if __name__ == '__main__':
    unittest.main()
