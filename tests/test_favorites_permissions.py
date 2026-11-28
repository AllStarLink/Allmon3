"""Run as root in a disposable machine with the packaged allmon3 account.

Exercises the actual postinst permission block against a temporary directory,
then drops credentials to prove atomic saves and protection of root-owned files.
Never operates on the machine's real /etc/allmon3.
"""
import os
import pwd
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.geteuid() == 0, 'requires disposable root environment')
class FavoritesPermissionsTest(unittest.TestCase):
    def test_postinst_restore_atomic_save_and_root_file_protection(self):
        account = pwd.getpwnam('allmon3')
        postinst = (ROOT / 'debian/postinst').read_text()
        begin = postinst.index('\t# Atomic favorites saves')
        end = postinst.index('\n\t## Apache Management', begin)
        block = postinst[begin:end]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            base.chmod(0o755)
            config = base / 'etc/allmon3'
            config.mkdir(parents=True)
            protected = config / 'web.ini'
            protected.write_text('[web]\n')
            protected.chmod(0o644)
            # Restored files may initially be root-owned and mode 0600.
            data = config / 'favorites.json'
            data.write_text('{"1999":{"111":"Restored"}}\n')
            data.chmod(0o600)
            lock = config / 'favorites.json.lock'
            lock.touch(mode=0o600)
            source = base / 'favorites_store.py'
            source.write_bytes((ROOT / 'src/asl_allmon/favorites/__init__.py').read_bytes())
            source.chmod(0o644)
            script = block.replace('/etc/allmon3', shlex.quote(str(config)))
            subprocess.run(['sh', '-ec', script], check=True)
            self.assertEqual(config.stat().st_uid, 0)
            self.assertEqual(config.stat().st_gid, account.pw_gid)
            self.assertEqual(config.stat().st_mode & 0o7777, 0o1775)
            self.assertEqual(data.stat().st_uid, account.pw_uid)
            self.assertEqual(data.stat().st_mode & 0o777, 0o640)
            child = r'''
import importlib.util, pathlib, sys
source, config = map(pathlib.Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('store', source)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
s = m.FavoritesStore(config / 'favorites.json')
assert s.list(1999) == [{'node': '111', 'label': 'Restored'}]
s.change(1999, 'save', '222', 'Added')
s.change(1999, 'delete', '111')
assert m.FavoritesStore(s.path).list(1999) == [{'node': '222', 'label': 'Added'}]
protected = config / 'web.ini'
replacement = config / '.replacement'; replacement.write_text('replacement')
for action in (lambda: protected.write_text('overwrite'),
               lambda: protected.unlink(), lambda: replacement.replace(protected)):
    try:
        action()
    except PermissionError:
        pass
    else:
        raise AssertionError('service could modify root-owned configuration')
replacement.unlink()
'''
            def drop_privileges():
                os.setgroups([])
                os.setgid(account.pw_gid)
                os.setuid(account.pw_uid)
            subprocess.run([sys.executable, '-c', child, str(source), str(config)],
                           preexec_fn=drop_privileges, check=True)
            self.assertEqual(protected.read_text(), '[web]\n')
            saved = data.read_bytes()
            # An upgrade reapplying permissions must not replace saved content.
            subprocess.run(['sh', '-ec', script], check=True)
            self.assertEqual(data.read_bytes(), saved)
            self.assertFalse(list(config.glob('.favorites-*')))
