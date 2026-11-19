"""Exercise the actual optional web.ini configuration parser."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('favorites_web_config', ROOT/'src/asl_allmon/web_configs/__init__.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FavoritesConfigTest(unittest.TestCase):
    def test_old_config_and_explicit_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'web.ini'
            p.write_text('[web]\n[syscmds]\n[node-overrides]\n[voter-titles]\n')
            self.assertEqual(module.WebConfigs(p).favorite_groups, [])
            with p.open('a') as f:
                f.write('[favorites-groups]\nsite = 1999, 2000\nother = 2001,2002\n')
            self.assertEqual(module.WebConfigs(p).favorite_groups,
                             [['1999','2000'],['2001','2002']])
