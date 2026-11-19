"""Fault injection only: no actual AMI connections or radio commands."""
import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tot_module', root/'src/asl_allmon/audio_tot/__init__.py')
tot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tot)
spec = importlib.util.spec_from_file_location('audio_module', root/'src/asl_allmon/audio/__init__.py')
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class GuardTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)/'guard'
        self.enabled = True
        self.state = 0
        self.now = 100.
        self.calls = []
        self.offline = False
        self.ambiguous_disable = False
        self.guard = self.make_guard()

    def make_guard(self, boot='boot'):
        return tot.TimeoutGuard(self.directory, self.command, {1998:'localhost:5038/1998'},
                                clock=lambda: self.now, boot_id=boot)

    async def command(self, node, command):
        self.calls.append(command)
        if self.offline:
            raise OSError('AMI offline')
        if 'cop' in command:
            # Every disable must have durable rollback intent before dispatch.
            self.assertTrue((self.directory/'1998.json').exists())
            self.enabled = 'cop 7' in command
            if self.ambiguous_disable and not self.enabled:
                raise OSError('reply lost after command applied')
            return 'OK:'
        return f'OK:\n*** NODE {node} STATISTICS ***\nSelected system state....: {self.state}\nTime out timer....: {"ENABLED" if self.enabled else "DISABLED"}\n'

    def toggles(self):
        return [c for c in self.calls if 'cop' in c]

    async def test_multisegment_only_toggles_at_job_start_end(self):
        await self.guard.before_playback(1998, 150)
        self.now += 155
        await self.guard.before_playback(1998, 150)
        await self.guard.finish(1998)
        self.assertEqual(self.toggles(), ['rpt cmd 1998 cop 8 0','rpt cmd 1998 cop 7 0'])
        self.assertTrue(self.enabled)
        self.assertFalse((self.directory/'1998.json').exists())

    async def test_prior_disabled_never_changed(self):
        self.enabled = False
        await self.guard.before_playback(1998, 150)
        await self.guard.finish(1998)
        await self.make_guard().recover(force=True)
        self.assertFalse(self.enabled)
        self.assertEqual(self.toggles(), [])

    async def test_reply_lost_after_disable_still_restores(self):
        self.ambiguous_disable = True
        with self.assertRaises(OSError):
            await self.guard.before_playback(1998, 150)
        await self.guard.finish(1998)
        self.assertTrue(self.enabled)

    async def test_crash_lease_and_restart_recovery(self):
        await self.guard.before_playback(1998, 150)
        recovering = self.make_guard()
        await recovering.recover()
        self.assertFalse(self.enabled)
        self.now += 181
        await recovering.recover()
        self.assertTrue(self.enabled)
        with self.assertRaises(tot.TimeoutGuardError):
            await self.guard.before_playback(1998, 150)
        self.guard = self.make_guard()
        await self.guard.before_playback(1998, 150)
        await self.make_guard().recover(force=True)
        self.assertTrue(self.enabled)

    async def test_reboot_recovery_and_already_enabled_no_transmission(self):
        await self.guard.before_playback(1998, 150)
        self.enabled = True  # Asterisk restart reset its runtime state.
        count = len(self.toggles())
        await self.make_guard('new-boot').recover()
        self.assertEqual(len(self.toggles()), count)
        self.assertFalse((self.directory/'1998.json').exists())

    async def test_failed_restore_retains_journal_and_blocks_playback(self):
        await self.guard.before_playback(1998, 150)
        self.offline = True
        with self.assertRaises(OSError):
            await self.guard.finish(1998)
        self.assertTrue((self.directory/'1998.json').exists())
        with self.assertRaises(OSError):
            await self.guard.before_playback(1998, 150)
        self.offline = False
        await self.make_guard().recover(force=True)
        self.assertTrue(self.enabled)

    async def test_state_or_identity_change_never_blindly_changes_other_state(self):
        await self.guard.before_playback(1998, 150)
        self.state = 1
        with self.assertRaises(tot.TimeoutGuardError):
            await self.guard.finish(1998)
        self.assertEqual(len(self.toggles()), 1)
        self.state = 0
        wrong = self.make_guard()
        wrong.identities[1998] = 'otherhost:5038/1998'
        with self.assertRaises(tot.TimeoutGuardError):
            await wrong.recover(force=True)
        await self.make_guard().recover(force=True)
        self.assertTrue(self.enabled)

    async def test_unverifiable_status_and_durable_write_failure_do_not_disable(self):
        async def bad(node, command):
            return 'OK: wrong node output'
        guard = tot.TimeoutGuard(self.directory, bad, self.guard.identities)
        with self.assertRaises(tot.TimeoutGuardError):
            await guard.before_playback(1998, 150)
        with patch.object(self.guard, '_save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                await self.guard.before_playback(1998, 150)
        self.assertEqual(self.toggles(), [])

    async def test_job_success_failure_and_cancellation_restore(self):
        for mode in ['success','failure','cancel']:
            self.guard = self.make_guard()
            async def playback(node, path):
                if path.name == 'name':
                    return
                self.assertFalse(self.enabled)
                if mode == 'failure':
                    raise OSError('playback rejected')
                if mode == 'cancel':
                    raise asyncio.CancelledError()
            service = audio.AudioService(Path(self.temp.name)/mode, Path(self.temp.name)/(mode+'cache'),
                                         [1998], playback, self.guard)
            service.initialize()
            async def fake_name(name):
                output=service.converted/'name.ulaw'
                output.write_bytes(b'\xff'*8000)
                return output
            service.prepare_stack_name=fake_name
            asset = 'a'*32
            (service.converted/(asset+'_000.ulaw')).write_bytes(b'\xff'*8000)
            with service._db() as db:
                db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(asset,'ID',None,'.wav',1,0,'sha'))
            ident = service.enqueue(1998,'test',['asset:'+asset])
            job = service._claim_job(1998)
            async def no_sleep(seconds):
                pass
            with patch.object(audio.asyncio, 'sleep', no_sleep):
                if mode == 'cancel':
                    with self.assertRaises(asyncio.CancelledError):
                        await service._run_job(job)
                else:
                    await service._run_job(job)
            self.assertTrue(self.enabled)
            self.assertEqual(service.snapshot([1998])['jobs'][0]['status'],
                             {'success':'done','failure':'failed','cancel':'interrupted'}[mode])

    async def test_watchdog_serializes_with_dispatch(self):
        entered = asyncio.Event()
        released = asyncio.Event()
        async def playback():
            entered.set()
            await released.wait()
        dispatch = asyncio.create_task(self.guard.dispatch(1998,150,playback))
        await entered.wait()
        self.now += 181
        recovery = asyncio.create_task(self.make_guard().recover())
        await asyncio.sleep(.05)
        self.assertFalse(self.enabled)
        released.set()
        await dispatch
        await recovery
        self.assertTrue(self.enabled)

    async def test_opening_announcement_never_toggles_timeout(self):
        for enabled in [True,False]:
            self.enabled=enabled
            observed=[]
            async def playback():observed.append(self.enabled)
            await self.guard.announce(1998,4,playback)
            self.assertEqual(observed,[enabled]);self.assertEqual(self.toggles(),[])
            self.assertFalse(self.guard._path(1998).exists())
    async def test_opening_blocks_when_recovery_or_status_unresolved(self):
        async def no_play():self.fail('Must not dispatch')
        await self.guard.before_playback(1998,5)
        with self.assertRaises(tot.TimeoutGuardError):await self.make_guard().announce(1998,4,no_play)
        await self.guard.finish(1998)
        self.offline=True
        with self.assertRaises(OSError):await self.guard.announce(1998,4,no_play)
