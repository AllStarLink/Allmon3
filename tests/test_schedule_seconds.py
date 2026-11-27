"""Second-resolution calendar and durable queue checks; no AMI/RF calls."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from test_audio import audio


def stamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=audio.ZoneInfo('America/Los_Angeles')).timestamp()


class SecondsTest(unittest.TestCase):
    def setUp(self):
        self.clock = audio.ScheduleClock('America/Los_Angeles')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        async def forbidden(*args):
            raise AssertionError('No audio or command dispatch allowed')
        self.service = audio.AudioService(Path(self.temp.name)/'state', Path(self.temp.name)/'cache',
                                          [1999], forbidden, command_dispatch=forbidden)
        self.service.clock = self.clock
        self.service.initialize()
        self.service.set_command_enabled(True)

    def test_next_second_is_not_skipped_and_midnight_rolls_over(self):
        for after, value, expected in [
            ('2030-01-01T14:30:16.900', '14:30:17', '2030-01-01T14:30:17'),
            ('2030-01-01T23:59:58.900', '23:59:59', '2030-01-01T23:59:59'),
            ('2030-01-01T23:59:59', '00:00:00', '2030-01-02T00:00:00'),
        ]:
            with self.subTest(after=after):
                self.assertEqual(self.clock.daily_next(value, stamp(after)), stamp(expected))
                weekday = datetime.fromisoformat(expected).weekday()
                self.assertEqual(self.clock.weekly_next(weekday, value, stamp(after)), stamp(expected))
        self.assertEqual(self.clock.daily_next('23:59:59', stamp('2030-01-01T23:59:59')),
                         stamp('2030-01-02T23:59:59'))
        self.assertEqual(self.clock.weekly_next(1, '23:59:59', stamp('2030-01-01T23:59:59')),
                         stamp('2030-01-08T23:59:59'))

    def test_legacy_minutes_are_equivalent_to_zero_seconds(self):
        for value in ['00:00', '14:00', '23:59']:
            self.assertEqual(self.clock.daily_next(value, stamp('2030-01-01T12:00')),
                             self.clock.daily_next(value+':00', stamp('2030-01-01T12:00')))
            self.assertEqual(self.clock.weekly_next(2, value, stamp('2030-01-01T12:00')),
                             self.clock.weekly_next(2, value+':00', stamp('2030-01-01T12:00')))

    def test_dst_gap_and_fold_with_seconds(self):
        self.assertEqual(self.clock.daily_next('02:30:17', stamp('2026-03-07T02:30:17')),
                         stamp('2026-03-09T02:30:17'))
        self.assertEqual(self.clock.weekly_next(6, '02:30:17', stamp('2026-03-07T12:00')),
                         stamp('2026-03-15T02:30:17'))
        self.assertEqual(self.clock.daily_next('01:30:17', stamp('2026-11-01T01:30:17')),
                         stamp('2026-11-02T01:30:17'))
        self.assertEqual(self.clock.weekly_next(6, '01:30:17', stamp('2026-11-01T01:30:17')),
                         stamp('2026-11-08T01:30:17'))

    def test_invalid_times_are_user_errors_for_both_recurrences(self):
        for value in [None, 140000, '', '24:00:00', '14:60:00', '14:00:60', '2:00:00',
                      '14:00:1', '14:00:00.5', '14:00:00Z', '14:00:00\n']:
            for recurrence in ['daily', 'weekly']:
                with self.subTest(value=value, recurrence=recurrence), self.assertRaises(audio.AudioError):
                    if recurrence == 'daily':
                        self.clock.daily_next(value)
                    else:
                        self.clock.weekly_next(1, value)

    def test_audio_and_command_preserve_seconds_and_never_queue_early(self):
        due = stamp('2030-01-01T14:30:17')
        ids = {}
        with patch.object(audio, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime.fromtimestamp(stamp('2030-01-01T12:00'), self.clock.zone)
            for kind in ['audio', 'command']:
                for recurrence in ['once', 'daily', 'weekly']:
                    ident = self.service.create_schedule(
                        1999, kind+' '+recurrence, ['source:aan'] if kind == 'audio' else [], recurrence,
                        run_at='2030-01-01T14:30:17', weekday=1, local_time='14:30:17', kind=kind,
                        command='rpt fun 1999 *1' if kind == 'command' else None)
                    ids[ident] = recurrence
            self.service.initialize()
            rows = self.service.snapshot([1999])['schedules']
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(row['next_at'] == due for row in rows))
            self.assertTrue(all(row['local_time'] == '14:30:17' for row in rows if row['recurrence'] != 'once'))
            clock.now.return_value = datetime.fromtimestamp(due - .001, self.clock.zone)
            self.service._due_schedules()
            self.assertEqual(self.service.snapshot([1999])['jobs'], [])
            clock.now.return_value = datetime.fromtimestamp(due, self.clock.zone)
            self.service._due_schedules()
            self.service._due_schedules()
            state = self.service.snapshot([1999])
            self.assertEqual(len(state['jobs']), 6)
            self.assertTrue(all(job['status'] == 'pending' and job['scheduled_for'] == due for job in state['jobs']))
            for row in state['schedules']:
                if ids[row['id']] == 'once':
                    self.assertEqual(row['enabled'], 0)
                else:
                    days = 1 if ids[row['id']] == 'daily' else 7
                    self.assertEqual(row['next_at'], due + days * 86400)


if __name__ == '__main__':
    unittest.main()
