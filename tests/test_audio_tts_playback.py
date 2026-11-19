"""End-to-end job sequencing with fake AMI, no radio transmissions."""
import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from test_audio import audio

class BoundaryTTSTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.events=[];self.block_at=None;self.fail_at=None;self.reached=asyncio.Event()
        self.gate=asyncio.Event();self.count=0
        owner=self
        class Guard:
            enabled=True
            async def announce(self,node,seconds,callback):
                owner.assertTrue(self.enabled)
                await callback()
            async def dispatch(self,node,seconds,callback):
                if self.enabled:owner.events.append('tot-off')
                self.enabled=False
                await callback()
            async def finish(self,node):
                if not self.enabled:owner.events.append('tot-on')
                self.enabled=True
        self.guard=Guard()
        async def playback(node,path):
            self.count+=1;self.events.append(path.name)
            if self.count==self.fail_at:raise OSError('playback failed')
            if self.count==self.block_at:
                self.reached.set();await self.gate.wait()
        async def stop(node):self.events.append('stop')
        self.s=audio.AudioService(Path(self.temp.name)/'s',Path(self.temp.name)/'c',[1998],playback,self.guard,stop)
        self.s.initialize();self.asset='a'*32
        with self.s._db() as db:
            db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(self.asset,'test',None,'.wav',1,0,'sha'))
        (self.s.converted/f'{self.asset}_000.ulaw').write_bytes(b'\xff'*800)
        name=self.s.converted/'spoken-name.ulaw';name.write_bytes(b'\xff'*800)
        self.s.prepare_stack_name=AsyncMock(return_value=name)
        self.delay=patch.object(audio.asyncio,'sleep',AsyncMock());self.delay.start();self.addCleanup(self.delay.stop)
    async def asyncTearDown(self):
        for task in self.s.active.values():task.cancel()
        await asyncio.gather(*self.s.active.values(),return_exceptions=True)
    def job(self,scheduled=False):
        if scheduled:
            ident=self.s.create_schedule(1998,'QST EXAMPLE PLAY BACK TEST',['asset:'+self.asset],'once',
                run_at=(datetime.now().astimezone()+timedelta(days=1)).isoformat())
            with self.s._db() as db:db.execute('UPDATE schedules SET next_at=? WHERE id=?',(datetime.now().timestamp()-1,ident))
            self.s._due_schedules()
        else:self.s.enqueue(1998,'QST EXAMPLE PLAY BACK TEST',['asset:'+self.asset])
        return self.s._claim_job(1998)
    def status(self,job):
        with self.s._db() as db:return db.execute('SELECT status FROM jobs WHERE id=?',(job['id'],)).fetchone()[0]
    async def test_queued_and_scheduled_boundary_order_inside_timeout_guard(self):
        for scheduled in (False,True):
            self.events.clear();job=self.job(scheduled)
            await self.s._run_job(job)
            self.assertEqual(self.events,['spoken-name','tot-off',self.asset+'_000','spoken-name','tot-on'])
            self.assertEqual(self.status(job),'done');self.assertTrue(self.guard.enabled)
            self.s.prepare_stack_name.assert_called_with('QST EXAMPLE PLAY BACK TEST')
    async def check_pause(self,index,expected_speech):
        job=self.job();self.block_at=index
        task=asyncio.create_task(self.s._run_job(job));self.s.active[1998]=task
        await asyncio.wait_for(self.reached.wait(),1)
        await self.s.control_job(1998,job['id'],'pause')
        self.assertEqual(self.status(job),'paused');self.assertTrue(self.guard.enabled)
        self.block_at=None
        await self.s.control_job(1998,job['id'],'resume');await self.s.active[1998]
        self.assertEqual(self.status(job),'done');self.assertTrue(self.guard.enabled)
        self.assertEqual(self.events.count('spoken-name'),expected_speech)
        self.s.prepare_stack_name.assert_awaited_once()
    async def test_pause_content_does_not_repeat_completed_intro(self):await self.check_pause(2,2)
    async def test_pause_intro_repeats_interrupted_announcement(self):await self.check_pause(1,3)
    async def test_pause_outro_repeats_only_interrupted_outro(self):await self.check_pause(3,3)
    async def test_stop_during_opening_never_plays_content_or_closing(self):
        job=self.job();self.block_at=1
        task=asyncio.create_task(self.s._run_job(job));self.s.active[1998]=task
        await asyncio.wait_for(self.reached.wait(),1)
        await self.s.control_job(1998,job['id'],'stop')
        self.assertEqual(self.events,['spoken-name','stop'])
        self.assertEqual(self.status(job),'cancelled')
    async def test_announcement_dispatch_failure_restores_timeout(self):
        for index in (1,3):
            self.count=0;self.events.clear();self.fail_at=index
            job=self.job();await self.s._run_job(job)
            self.assertEqual(self.status(job),'failed');self.assertTrue(self.guard.enabled)
            self.assertEqual(self.events[-2:],['stop','tot-on'] if index==3 else ['spoken-name','stop'])
    async def test_generation_failure_does_not_key_radio(self):
        self.s.prepare_stack_name.side_effect=OSError('speech engine unavailable')
        job=self.job();await self.s._run_job(job)
        self.assertEqual(self.events,[]);self.assertEqual(self.status(job),'failed')
        self.assertTrue(self.guard.enabled)

    async def test_all_downloads_finish_before_opening_speech_and_tot_disable(self):
        async def fetch(source):
            self.assertTrue(self.guard.enabled)
            self.assertEqual(self.events,[])
            self.events.append('download')
            return self.asset
        self.s.fetch_source=AsyncMock(side_effect=fetch)
        self.s.enqueue(1998,'news',['asset:'+self.asset,'source:arn'])
        job=self.s._claim_job(1998);await self.s._run_job(job)
        self.assertEqual(self.events,['download','spoken-name','tot-off',self.asset+'_000',self.asset+'_000','spoken-name','tot-on'])
        self.assertEqual(self.status(job),'done')
