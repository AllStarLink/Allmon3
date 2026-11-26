"""Playback controls use fake audio/AMI callbacks only: never transmit."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from test_audio import audio

class Guard:
    def __init__(self):
        self.enabled = True
        self.fail_finish = False
    async def dispatch(self, node, duration, callback):
        self.enabled = False
        await callback()
    async def finish(self, node):
        if self.fail_finish:
            raise OSError('AMI unavailable')
        self.enabled = True

class ControlsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls=[];self.stops=[];self.fail_stop=False;self.guard=Guard()
        async def play(node,path):self.calls.append((node,path.name))
        async def stop(node):
            self.stops.append(node)
            if self.fail_stop:raise OSError('AMI unavailable')
        self.s=audio.AudioService(Path(self.temp.name)/'s',Path(self.temp.name)/'c',
                                  [1998,1999],play,self.guard,stop)
        self.s.initialize()
        self.s.prepare_stack_name=AsyncMock(return_value=None)
        original_play=self.s._play_segment
        async def content_only(node, segment, control, **kwargs):
            if segment is not None: await original_play(node, segment, control, **kwargs)
        self.s._play_segment=content_only
        self.asset='a'*32
        with self.s._db() as db:
            db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(self.asset,'test',None,'.wav',300,0,'sha'))
        for index in range(2):
            (self.s.converted/f'{self.asset}_{index:03}.ulaw').write_bytes(b'\xff'*1200000)
        self.job_id=self.s.enqueue(1998,'test',['asset:'+self.asset])
        self.job=self.s._claim_job(1998)
        self.task=asyncio.create_task(self.s._run_job(self.job));self.s.active[1998]=self.task
        await self.wait_calls(1)
    async def asyncTearDown(self):
        self.fail_stop=False;self.guard.fail_finish=False
        for task in list(self.s.active.values()):task.cancel()
        await asyncio.gather(*self.s.active.values(),return_exceptions=True)
        self.temp.cleanup()
    async def wait_calls(self,count):
        async def wait():
            while len(self.calls)<count:await asyncio.sleep(.001)
        await asyncio.wait_for(wait(),1)
    def status(self,ident=None):
        with self.s._db() as db:
            return db.execute('SELECT status FROM jobs WHERE id=?',(ident or self.job_id,)).fetchone()[0]
    async def command(self,action):return await self.s.control_job(1998,self.job_id,action)
    async def test_pause_resume_replays_current_segment_and_restores_tot(self):
        self.assertFalse(self.guard.enabled)
        await self.command('pause')
        self.assertEqual(self.status(),'paused');self.assertTrue(self.guard.enabled)
        self.assertIsNone(self.s._claim_job(1998));self.assertEqual(self.stops,[1998])
        await self.command('resume');await self.wait_calls(2)
        self.assertEqual(self.calls[0],self.calls[1]);self.assertFalse(self.guard.enabled)
        await self.command('stop')
        self.assertEqual(self.status(),'cancelled');self.assertTrue(self.guard.enabled)
    async def test_stop_cancels_current_and_pending_only_on_selected_node(self):
        pending=self.s.enqueue(1998,'queued',['asset:'+self.asset])
        other=self.s.enqueue(1999,'other',['asset:'+self.asset])
        schedule=self.s.create_schedule(1998,'later',['asset:'+self.asset],'once',
            run_at=(datetime.now().astimezone()+timedelta(days=1)).isoformat())
        await self.command('stop')
        self.assertEqual(self.status(),'cancelled');self.assertEqual(self.status(pending),'cancelled')
        self.assertEqual(self.status(other),'pending')
        self.assertEqual(self.s.snapshot([1998])['schedules'][0]['id'],schedule)
        self.assertTrue(self.guard.enabled)
    async def test_audio_pause_blocks_command_and_stop_preserves_pending_command(self):
        self.s.set_command_enabled(True)
        ident = self.s.create_schedule(1998, 'Command', [], 'daily', local_time='14:00',
                                       kind='command', command='rpt fun 1998 *80')
        with self.s._db() as db:
            db.execute('UPDATE schedules SET next_at=? WHERE id=?', (datetime.now().timestamp()-1, ident))
        self.s._due_schedules()
        await self.command('pause')
        self.assertIsNone(self.s._claim_job(1998))
        await self.command('stop')
        job = self.s._claim_job(1998)
        self.assertEqual(job['kind'], 'command')
        self.assertEqual(job['command'], 'rpt fun 1998 *80')

    async def test_wrong_node_and_stale_job_do_not_control_playback(self):
        for node,ident in [(1999,self.job_id),(1998,'0'*32)]:
            with self.assertRaises(audio.AudioError):await self.s.control_job(node,ident,'stop')
        self.assertEqual(self.status(),'playing');self.assertEqual(self.stops,[])
    async def test_pause_then_stop_without_resume(self):
        await self.command('pause');await self.command('stop')
        self.assertEqual(self.status(),'cancelled');self.assertEqual(len(self.calls),1)
        self.assertTrue(self.guard.enabled)
    async def test_resume_immediately_paused_before_task_starts(self):
        await self.command('pause');await self.command('resume');await self.command('pause')
        self.assertEqual(self.status(),'paused');self.assertTrue(self.guard.enabled)
        await self.command('stop');self.assertEqual(self.status(),'cancelled')
    async def test_stop_failure_blocks_dispatch_until_retry(self):
        self.fail_stop=True
        with self.assertRaises(audio.AudioError):await self.command('stop')
        self.assertEqual(self.status(),'control_failed');self.assertTrue(self.guard.enabled)
        self.assertIsNone(self.s._claim_job(1998))
        with self.assertRaises(audio.AudioError):await self.command('resume')
        self.fail_stop=False;await self.command('stop')
        self.assertEqual(self.status(),'cancelled');self.assertNotIn(1998,self.s.controls)
    async def test_timeout_restore_failure_does_not_report_paused(self):
        self.guard.fail_finish=True
        with self.assertRaises(audio.AudioError):await self.command('pause')
        self.assertEqual(self.status(),'control_failed');self.assertIsNone(self.s._claim_job(1998))
        self.guard.fail_finish=False;await self.command('stop');self.assertTrue(self.guard.enabled)
    async def test_restart_does_not_replay_paused_job(self):
        await self.command('pause')
        restarted=audio.AudioService(self.s.state,self.s.cache,[1998],self.s.playback,self.guard,self.s.stop_playback)
        restarted.initialize()
        self.assertEqual(self.status(),'interrupted');self.assertIsNone(restarted._claim_job(1998))
    async def test_service_cancellation_flushes_audio_and_restores(self):
        self.task.cancel();await asyncio.gather(self.task,return_exceptions=True)
        self.assertEqual(self.status(),'interrupted');self.assertTrue(self.guard.enabled)
        self.assertEqual(self.stops,[1998])
    async def test_resume_keeps_second_segment_checkpoint(self):
        await self.command('stop')
        self.calls.clear()
        (self.s.converted/f'{self.asset}_000.ulaw').write_bytes(b'\xff'*8)
        self.job_id=self.s.enqueue(1998,'checkpoint',['asset:'+self.asset])
        self.job=self.s._claim_job(1998)
        # This control-only fixture shortens segment 0 deliberately; cache
        # validation/rebuilding is exercised with real audio in test_audio.py.
        segments = sorted(self.s.converted.glob(f'{self.asset}_*.ulaw'))
        with patch.object(self.s.settings,'gap_seconds',0), patch.object(self.s, '_ensure_segments', return_value=segments):
            self.task=asyncio.create_task(self.s._run_job(self.job));self.s.active[1998]=self.task
            await self.wait_calls(2);await self.command('pause');await self.command('resume');await self.wait_calls(3)
            self.assertEqual(self.calls[1],self.calls[2]);self.assertNotEqual(self.calls[0],self.calls[2])
            await self.command('stop')
    async def test_active_job_is_visible_with_more_than_fifty_queued(self):
        for index in range(55):self.s.enqueue(1998,str(index),['asset:'+self.asset])
        self.assertEqual(self.s.snapshot([1998])['jobs'][0]['id'],self.job_id)

    async def test_master_off_does_not_interrupt_current_job(self):
        self.s.set_playback_enabled(False)
        self.assertEqual(self.status(),'playing')
        self.assertFalse(self.task.done())
        self.assertEqual(self.stops,[])
        self.assertIsNone(self.s._claim_job(1999))
        await self.command('stop')
        self.assertEqual(self.status(),'cancelled')
        self.assertTrue(self.guard.enabled)

    async def test_master_off_blocks_resume_but_allows_stop(self):
        await self.command('pause')
        self.s.set_playback_enabled(False)
        with self.assertRaises(audio.AudioError):await self.command('resume')
        await self.command('stop')
        self.assertEqual(self.status(),'cancelled')
        self.assertTrue(self.guard.enabled)
