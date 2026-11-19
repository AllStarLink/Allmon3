import asyncio,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_audio import audio

class StackTTSTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        async def no_transmit(*args):raise AssertionError('No playback allowed in generation checks')
        self.s=audio.AudioService(Path(self.temp.name)/'state',Path(self.temp.name)/'cache',[1998],no_transmit)
        self.s.initialize()
    async def test_name_cache_uses_normalized_text_not_filename_or_shell(self):
        calls=[]
        def render(text,output):calls.append(text);output.write_bytes(b'\xff'*8000);return output
        with patch.object(self.s,'_render_stack_name',render):
            a=await self.s.prepare_stack_name('  Friday   News  ')
            b=await self.s.prepare_stack_name('Friday News')
            c=await self.s.prepare_stack_name('$(touch /tmp/never) --help')
        self.assertEqual(a,b);self.assertNotEqual(a,c)
        self.assertEqual(calls,['Friday News','$(touch /tmp/never) --help'])
        self.assertNotIn('Friday',a.name);self.assertEqual(a.parent,self.s.converted)
        for invalid in ['',None,'x'*81]:
            with self.assertRaises(audio.AudioError):await self.s.prepare_stack_name(invalid)
    @unittest.skipUnless(Path(audio.PIPER_BIN).exists() and Path(audio.PIPER_MODEL).exists() and shutil.which('ffmpeg'),'speech tools required')
    async def test_real_speech_generation_readable_and_cached_without_transmission(self):
        output=await self.s.prepare_stack_name('Amateur Radio News')
        self.assertGreater(output.stat().st_size,8000)
        self.assertLess(output.stat().st_size,60*8000)
        self.assertEqual(output.stat().st_mode & 0o777,0o644)
        before=output.stat().st_mtime_ns
        self.assertEqual(await self.s.prepare_stack_name('Amateur Radio News'),output)
        self.assertEqual(output.stat().st_mtime_ns,before)

    async def test_voice_profile_change_invalidates_existing_speech_cache(self):
        def render(text,output):output.write_bytes(b'\xff'*8000);return output
        with patch.object(self.s,'_render_stack_name',render):
            a=await self.s.prepare_stack_name('Friday News')
            with patch.object(audio,'SPEECH_PROFILE','different-voice-or-speed'):
                b=await self.s.prepare_stack_name('Friday News')
        self.assertNotEqual(a,b)
    async def test_piper_speed_and_stdin_arguments_and_fallback_cache(self):
        calls=[]
        def tool(args,timeout,input=None):
            calls.append((args,timeout,input))
            if args[0]=='nice':Path(args[-1]).write_bytes(b'fake wave')
            else:Path(args[-1]).write_bytes(b'\xff'*8000)
        with patch.object(self.s,'_tool',tool):
            output=await self.s.prepare_stack_name('$(never execute) --help')
            fallback=self.s._render_unavailable()
        args,timeout,text=calls[0]
        self.assertEqual(args[:4],['nice','-n','10',audio.PIPER_BIN])
        self.assertEqual(args[args.index('--length-scale')+1],'1.25')
        self.assertEqual(text,'$(never execute) --help')
        self.assertNotIn(text,args)
        self.assertEqual(calls[2][2],audio.FALLBACK_TEXT)
        self.assertIn('aresample=8000,volume=4/3,alimiter=limit=0.95:level=false:latency=true',calls[1][0])
        self.assertEqual(fallback.name,audio.FALLBACK_FILE)
        self.assertNotEqual(fallback.name,'qst_no_new_file.ulaw')

    @unittest.skipUnless(shutil.which('ffmpeg'),'ffmpeg required')
    async def test_real_gain_one_third_with_peak_limiting(self):
        import math,struct,subprocess,wave
        root=Path(self.temp.name)
        original_tool=self.s._tool
        for amplitude in [0.1,0.79]:
            wav=root/'tone.wav'
            samples=[int(32767*amplitude*math.sin(2*math.pi*400*i/8000)) for i in range(8000)]
            with wave.open(str(wav),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000)
                w.writeframes(struct.pack('<8000h',*samples))
            def tool(args,timeout,input=None):
                if args[0]=='nice':shutil.copyfile(wav,args[-1]);return ''
                return original_tool(args,timeout,input)
            out=root/'gain.ulaw'
            with patch.object(self.s,'_tool',tool):self.s._render_stack_name('gain check',out)
            decoded=subprocess.check_output(['ffmpeg','-v','error','-f','mulaw','-ar','8000','-ac','1','-i',str(out),'-f','f32le','-'])
            values=struct.unpack('<'+'f'*(len(decoded)//4),decoded)[800:-800]
            peak=max(abs(v) for v in values)
            self.assertLessEqual(peak,0.96)
            if amplitude==0.1:
                rms=math.sqrt(sum(v*v for v in values)/len(values))
                self.assertAlmostEqual(rms/(amplitude/math.sqrt(2)),4/3,delta=.03)
            else:self.assertGreater(peak,.90)
