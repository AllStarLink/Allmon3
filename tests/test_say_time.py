import contextlib
from datetime import datetime
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

loader = SourceFileLoader('say_time', str(Path(__file__).resolve().parents[1] / 'src/allmon3-say-time'))
spec = importlib.util.spec_from_loader('say_time', loader)
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


class SayTimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'time.ini'
        self.config.write_text('[time]\nnodes = 12345\n')

    def test_clock_boundaries_and_minutes(self):
        for hour, minute, words in [(0,0,"twelve o'clock A M"), (12,0,"twelve o'clock P M"),
                (13,1,'one oh one P M'), (6,9,'six oh nine A M'), (6,10,'six ten A M'),
                (18,21,'six twenty one P M'), (23,59,'eleven fifty nine P M')]:
            with self.subTest(hour=hour,minute=minute):
                value=t.report(datetime(2026,11,26,hour,minute,tzinfo=ZoneInfo('America/Los_Angeles')))
                self.assertEqual(value['text'], 'The local time is '+words+'.')
                self.assertEqual(value['timezone'],'PST')

    def test_dst_repeated_hour_retains_offset(self):
        a=t.report(datetime(2026,11,1,1,30,tzinfo=ZoneInfo('America/Los_Angeles'),fold=0))
        b=t.report(datetime(2026,11,1,1,30,tzinfo=ZoneInfo('America/Los_Angeles'),fold=1))
        self.assertEqual(a['text'],b['text'])
        self.assertNotEqual(a['local_time'],b['local_time'])

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError): t.report(datetime(2026,1,1))

    def test_configuration_fails_closed(self):
        for content in ['', '[time]\n', '[typo]\nnodes=12345\n',
                        '[DEFAULT]\nnodes=12345\n[time]\n', '[time]\nnodes=12345\nvoice=bad\n',
                        '[time]\nnodes=12345,0\n']:
            self.config.write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                t.load_settings(self.config,'12345')

    def test_node_permission_and_input(self):
        t.load_settings(self.config,'12345')
        for node in ['12346','0','-1','12345; reboot','12345\n']:
            with self.subTest(node=node), self.assertRaises(ValueError):
                t.load_settings(self.config,node)

    def test_default_text_cannot_play_or_synthesize(self):
        with patch.object(t,'play',side_effect=AssertionError('play')), patch.object(t,'render',side_effect=AssertionError('render')), patch.object(t.subprocess,'run',side_effect=AssertionError('subprocess')), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(t.main(['--node','12345','--config',str(self.config)]),0)
        self.assertIn('local time',json.loads(output.getvalue())['text'])

    def test_render_mode_never_dispatches(self):
        with patch.object(t,'render',return_value=4.0) as render, patch.object(t,'play',side_effect=AssertionError('play')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(t.main(['--node','12345','--config',str(self.config),'--render',str(self.root/'time.ulaw')]),0)
            render.assert_called_once()

    def test_only_localplay_is_dispatched(self):
        responses=[subprocess.CompletedProcess([],0,'Node\n----\n12345\n',''),subprocess.CompletedProcess([],0,'','')]
        with patch.object(t,'CACHE',self.root),patch.object(t.subprocess,'run',side_effect=responses) as run:
            t.play('12345',self.root/'time-12345-123.ulaw')
        self.assertEqual(run.call_args_list[1].args[0],['/usr/sbin/asterisk','-rx','rpt localplay 12345 '+str(self.root/'time-12345-123')])

    def test_remote_node_cannot_dispatch(self):
        with patch.object(t,'CACHE',self.root),patch.object(t.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'Node\n----\n99999\n','')) as run:
            with self.assertRaises(ValueError):t.play('12345',self.root/'time-12345-123.ulaw')
            self.assertEqual(run.call_count,1)

    def test_rejected_dispatch_is_not_success(self):
        with patch.object(t,'CACHE',self.root),patch.object(t,'require_local_node'),patch.object(t.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'Unknown node','')):
            with self.assertRaises(ValueError):t.play('12345',self.root/'time-12345-123.ulaw')

    def test_bad_playback_paths_rejected_before_subprocess(self):
        with patch.object(t,'CACHE',self.root),patch.object(t.subprocess,'run',side_effect=AssertionError('run')):
            for path in [self.root/'time-99999-123.ulaw',self.root/'time-12345-abc.ulaw',Path('/tmp/other.ulaw')]:
                with self.assertRaises(ValueError):t.play('12345',path)

    def test_minute_rollover_rerenders_before_play(self):
        a={'text':'old','local_time':'2026-11-26T18:00:59-08:00'}
        b={'text':'new','local_time':'2026-11-26T18:01:02-08:00'}
        with patch.object(t,'CACHE',self.root),patch.object(t,'require_local_node'),patch.object(t,'report',side_effect=[dict(a),dict(b),dict(b),dict(b)]),patch.object(t,'render',return_value=4) as render,patch.object(t,'play') as play,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(t.main(['--node','12345','--config',str(self.config),'--play']),0)
            self.assertEqual(render.call_count,2)
            self.assertEqual(render.call_args.args[0],'new')
            play.assert_called_once()

    def test_render_failure_never_plays(self):
        with patch.object(t,'CACHE',self.root),patch.object(t,'require_local_node'),patch.object(t,'render',side_effect=ValueError('broken')),patch.object(t,'play') as play,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(t.main(['--node','12345','--config',str(self.config),'--play']),1)
            play.assert_not_called()

    def test_continuous_minute_rollover_fails_without_play(self):
        reports=[{'text':'time','local_time':f'2026-11-26T18:0{x}:00-08:00'} for x in range(4)]
        with patch.object(t,'CACHE',self.root),patch.object(t,'require_local_node'),patch.object(t,'report',side_effect=reports),patch.object(t,'render',return_value=4),patch.object(t,'play') as play,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(t.main(['--node','12345','--config',str(self.config),'--play']),1)
            play.assert_not_called()

if __name__=='__main__':unittest.main()
