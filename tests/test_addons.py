"""Optional-package isolation, node scoping, and timezone regression checks."""
import asyncio
import importlib
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from asl_allmon import addons
from asl_allmon.announcement_config import AnnouncementConfig
from test_audio import audio
from test_audio_api import load_server

class AddonTests(unittest.TestCase):
    def test_no_registry_means_no_addon_imports(self):
        with tempfile.TemporaryDirectory() as d,patch.object(addons.importlib,'import_module',side_effect=AssertionError('No optional import')):
            self.assertEqual(addons.load(None,None,None,d),[])
    def test_removed_optional_package_with_preserved_config_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'example.ini').write_text('[addon]\nenabled=true\nmodule=asl_allmon.missing_addon\nfactory=Missing\n')
            self.assertEqual(addons.load(None,None,None,d),[])
    def test_base_server_starts_without_audio_dependencies(self):
        load_server()  # Existing lightweight session/security mocks.
        core=importlib.import_module('asl_allmon.allmon3_server')
        with patch.object(core.addons,'load',return_value=[]):
            server=core.ServerWS(None,None,None)
        self.assertEqual(server.addons,[]);self.assertFalse(hasattr(server,'audio'))
    def test_explicit_node_cannot_relabel_remote_asterisk_as_local(self):
        cls=load_server()
        nodes=types.SimpleNamespace(all_nodes=[1999,2000],colo_nodes={},nodes={
            1999:types.SimpleNamespace(host='localhost',port=5038),
            2000:types.SimpleNamespace(host='remote.example',port=5038)})
        settings=AnnouncementConfig();settings.local_nodes={1999,2000}
        module=importlib.import_module('asl_allmon.announcements')
        with patch.object(module,'AnnouncementConfig',return_value=settings):
            addon=cls(None,nodes,types.SimpleNamespace())
        self.assertEqual(addon.audio.nodes,[1999])
    def test_ini_bounds_and_timezone(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d,'announcements.ini')
            path.write_text('[announcements]\ntimezone=Europe/London\ngap_seconds=9\nmax_upload_mb=2\n')
            c=AnnouncementConfig(path);self.assertEqual(c.gap_seconds,9);self.assertEqual(c.max_upload,2*1024*1024)
            self.assertEqual(c.timezone,'Europe/London')
            for field in ['gap_seconds=0','max_upload_mb=101','segment_seconds=151','unknown=1']:
                path.write_text('[announcements]\n'+field+'\n')
                with self.assertRaises(ValueError):AnnouncementConfig(path)
    def test_system_timezone_is_read_not_hardcoded(self):
        c=audio.ScheduleClock()
        with patch.object(Path,'resolve',return_value=Path('/usr/share/zoneinfo/Europe/Berlin')):
            self.assertEqual(c.zone.key,'Europe/Berlin')
        with patch.object(Path,'resolve',return_value=Path('/usr/share/zoneinfo/UTC')):
            self.assertEqual(c.zone.key,'UTC')
    def test_weekly_nonexistent_time_skips_to_following_week(self):
        from datetime import datetime
        c=audio.ScheduleClock('America/Los_Angeles')
        start=datetime(2026,3,7,3,tzinfo=c.zone).timestamp()
        expected=datetime(2026,3,15,2,30,tzinfo=c.zone).timestamp()
        self.assertEqual(c.weekly_next(6,'02:30',start),expected)

    def test_existing_announcements_config_cannot_silently_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'announcements.ini')
            for content in ['', '[announcement]\nlocal_nodes=1999\n',
                            '[announcements]\n[other]\nx=1\n',
                            '[DEFAULT]\nlocal_nodes=1999\n[announcements]\n',
                            '[announcements]\nlocal_nodes=0,-1999\n']:
                with self.subTest(content=content):
                    path.write_text(content)
                    with self.assertRaises(ValueError):
                        AnnouncementConfig(path)
            path.unlink()
            self.assertEqual(AnnouncementConfig(path).gap_seconds, 15)

    def test_ini_storage_overrides_reach_addon_runtime_and_survive_restart(self):
        # Keep the real INI parser, add-in constructor and AudioService. Redirect
        # only the config filename, not parsed settings or runtime storage fields.
        cls = load_server()
        module = importlib.import_module('asl_allmon.announcements')
        nodes = types.SimpleNamespace(all_nodes=[1999], colo_nodes={}, nodes={
            1999: types.SimpleNamespace(host='localhost', port=5038)})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'announcements.ini'
            state, cache = root / 'custom-state', root / 'custom-cache'
            path.write_text(f'[announcements]\nstate_dir={state}\ncache_dir={cache}\ntimezone=UTC\n')
            with patch.object(module, 'AnnouncementConfig', side_effect=lambda: AnnouncementConfig(path)):
                addon = cls(None, nodes, types.SimpleNamespace())
                addon.audio.initialize()
                self.assertEqual(addon.audio.state, state)
                self.assertEqual(addon.audio.cache, cache)
                self.assertEqual(addon.audio.db_path, state / 'audio.sqlite3')
                self.assertEqual(addon.audio.originals, state / 'audio-originals')
                self.assertEqual(addon.audio.converted, cache / 'audio')
                self.assertTrue(addon.audio.db_path.is_file())
                self.assertTrue(addon.audio.originals.is_dir())
                self.assertTrue(addon.audio.converted.is_dir())
                addon.audio.set_playback_enabled(False)
                restarted = cls(None, nodes, types.SimpleNamespace())
                restarted.audio.initialize()
                self.assertFalse(restarted.audio.playback_enabled())
                self.assertEqual(restarted.audio.db_path, addon.audio.db_path)
