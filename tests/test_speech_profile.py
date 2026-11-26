"""Configuration selection, cache isolation and pre-transmission failure checks."""
import asyncio
import importlib.util
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from asl_allmon.speech import load_profile, FILTER
from test_audio import audio

class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.config=self.root/'speech.ini'
        self.binary=Path(shutil.which('true'))  # /tmp may be mounted noexec on the target.
        for voice in ['en_US-ryan-medium','en_US-lessac-medium']:
            (self.root/(voice+'.onnx')).write_bytes(voice.encode())
            (self.root/(voice+'.onnx.json')).write_text('{"audio":{"sample_rate":22050}}')
        self.configure()
    def configure(self,voice='en_US-ryan-medium'):
        self.config.write_text(f'[speech]\nvoice = {voice}\nmodel_dir = {self.root}\npiper_bin = {self.binary}\nbackend = python\n')
    def profile(self):return load_profile(self.config,environ={})
    def service(self,name):
        async def refuse(*a):raise AssertionError('No transmission permitted')
        service=audio.AudioService(self.root/name,self.root/(name+'-cache'),[59521],refuse)
        service.initialize();return service
    def renderer(self,service,calls):
        def tool(args,timeout,input=None):
            calls.append((args,input))
            Path(args[-1]).write_bytes(b'\xff'*8000)
        service._tool=tool
    def test_shared_config_overrides_legacy_and_environment(self):
        p=load_profile(self.config,legacy={'piper_model':'/bad/legacy'},environ={'ALLMON3_PIPER_MODEL':'/bad/env','ALLMON3_PIPER_BIN':'/bad/bin'})
        self.assertTrue(p.model.endswith('en_US-ryan-medium.onnx'))
        self.assertEqual(p.binary,str(self.binary))
    def test_no_environment_configuration(self):
        with self.assertRaises(ValueError):
            load_profile(self.root/'absent',environ={'ALLMON3_PIPER_BIN':str(self.binary),'ALLMON3_PIPER_MODEL':str(self.root/'en_US-ryan-medium.onnx')})
    def test_rejects_invalid_voice_unknown_option_and_missing_section(self):
        for voice in ['../escape','--help','$(touch x)','']:
            self.configure(voice)
            with self.assertRaises(ValueError):self.profile()
        for content in ['[other]\nvoice=x','[speech]\nvoic=ryan','[DEFAULT]\nx=y\n[speech]\nvoice=ryan']:
            self.config.write_text(content)
            with self.assertRaises(ValueError):self.profile()
    def test_missing_model_companion_and_bad_json_fail(self):
        self.configure('missing')
        with self.assertRaises(ValueError):self.profile()
        self.configure();companion=self.root/'en_US-ryan-medium.onnx.json';companion.unlink()
        with self.assertRaises(FileNotFoundError):self.profile()
        for value in ['broken','[]','{}']:
            companion.write_text(value)
            with self.assertRaises(ValueError):self.profile()
    def test_missing_executable_fails(self):
        self.binary=self.root/'not-executable';self.binary.write_text('not executable');self.configure()
        with self.assertRaises(ValueError):self.profile()
    def test_same_path_replacement_changes_fingerprint(self):
        first=self.profile();model=Path(first.model);model.write_bytes(b'new-model')
        second=self.profile();self.assertNotEqual(first.identity,second.identity)
        with self.assertRaises(ValueError):first.check_model()
        companion=Path(second.model+'.json');companion.write_text('{"new":true}')
        self.assertNotEqual(second.identity,self.profile().identity)
    def test_voice_change_invalidates_stack_and_fallback_but_existing_service_is_frozen(self):
        calls=[];s=self.service('one');self.renderer(s,calls)
        with patch.object(audio,'load_profile',side_effect=self.profile):
            first=asyncio.run(s.prepare_stack_name('Friday news'));fallback=s._render_unavailable()
            self.configure('en_US-lessac-medium')
            self.assertEqual(first,asyncio.run(s.prepare_stack_name('Friday news')))
            self.assertEqual(fallback,s.fallback_path())
            new=self.service('two');self.renderer(new,calls)
            second=asyncio.run(new.prepare_stack_name('Friday news'));newfallback=new._render_unavailable()
        self.assertNotEqual(first.name,second.name);self.assertNotEqual(fallback.name,newfallback.name)
        models=[args[args.index('--model')+1] for args,_ in calls if args[0]=='nice']
        self.assertTrue(all('ryan' in m for m in models[:2]));self.assertTrue(all('lessac' in m for m in models[2:]))
    def test_renderer_preserves_clarity_gain_and_text_as_stdin(self):
        s=self.service('render');calls=[];self.renderer(s,calls)
        with patch.object(audio,'load_profile',side_effect=self.profile):
            asyncio.run(s.prepare_stack_name('$(not-a-command) --help'))
        command,text=calls[0];self.assertEqual(text,'$(not-a-command) --help');self.assertNotIn(text,command)
        for option,value in [('--length-scale','1.25'),('--volume','0.8'),('--sentence-silence','0.18')]:
            self.assertEqual(command[command.index(option)+1],value)
        self.assertIn(FILTER,calls[1][0]);self.assertEqual(s.settings.gap_seconds,15)
    def test_invalid_profile_fails_job_before_dispatch(self):
        s=self.service('invalid');events=[]
        async def playback(*a):events.append(a)
        s.playback=playback
        asset='a'*32
        with s._db() as db:db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?)',(asset,'test',None,'.wav',1,0,'sha'))
        (s.converted/(asset+'_000.ulaw')).write_bytes(b'\xff'*800)
        s.enqueue(59521,'test',['asset:'+asset]);job=s._claim_job(59521)
        self.configure('missing')
        with patch.object(audio,'load_profile',side_effect=self.profile):asyncio.run(s._run_job(job))
        self.assertEqual(events,[])
        with s._db() as db:self.assertEqual(db.execute('SELECT status FROM jobs').fetchone()[0],'failed')
    def test_asl3_backend_uses_packaged_cli_without_privileged_wrapper(self):
        self.config.write_text(self.config.read_text().replace('backend = python','backend = asl3'))
        p=self.profile();command=p.command(self.root/'speech.wav')
        self.assertIn('--length_scale',command);self.assertIn('--sentence_silence',command)
        self.assertIn('--output_file',command);self.assertNotIn('--volume',command)
        self.assertTrue(p.audio_filter.startswith('volume=0.8,'))
        self.assertNotIn('sudo',command);self.assertNotIn('asterisk',command)
    def test_configurable_synthesis_values_are_bounded_and_fingerprinted(self):
        first=self.profile()
        with self.config.open('a') as f:f.write('sentence_silence=0.25\nlength_scale=3/2\n')
        changed=self.profile()
        self.assertEqual(changed.length_scale,'1.5');self.assertEqual(changed.sentence_silence,'0.25')
        self.assertNotEqual(first.identity,changed.identity)
        for bad in ['volume=NaN','gain=1/0','limiter=2','length_scale=-1']:
            self.configure()
            with self.config.open('a') as f:f.write(bad+'\n')
            with self.assertRaises(ValueError):self.profile()
