"""Exercise registered HTTP routes and cookie sessions without Asterisk."""

import importlib
import inspect
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from aiohttp import ClientSession, CookieJar, web

# Load the server without the package's unrelated AMI/status imports. Keep real
# aiohttp and aiohttp_session so route matching and awaited authorization run.
PACKAGE = '_favorites_api_test'
package = types.ModuleType(PACKAGE)
package.__path__ = [str(Path(__file__).resolve().parents[1] / 'src/asl_allmon')]
sys.modules[PACKAGE] = package
for name in ('node_configs', 'security', 'web_configs'):
    sys.modules[f'{PACKAGE}.{name}'] = types.ModuleType(f'{PACKAGE}.{name}')
ServerWS = importlib.import_module(f'{PACKAGE}.allmon3_server').ServerWS


class FavoritesAPITest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'custom-favorites.json'
        self.nodes = types.SimpleNamespace(
            all_nodes=[1999, 2000, 2001], colo_nodes={2000: 1999},
            nodes={1999: types.SimpleNamespace(
                monport=1234, cmdport=1235, iframepre='', iframepost='',
                voterports={2000: 1236})})
        self.security = types.SimpleNamespace(
            session_db={}, restricted_users={'ham'}, restrictdb={'ham1999'},
            validate=lambda user, password: user == 'ham' and password == 'test-only',
            create_session=self.create_session)
        self.config = types.SimpleNamespace(
            favorite_groups=[['1999', '2000']], voter_titles={},
            ws_bind_addr='127.0.0.1', http_port=0)
        self.server = ServerWS(self.config, self.nodes, self.security, self.path)
        runner_class = web.AppRunner

        def capture_runner(app):
            self.runner = runner_class(app)
            return self.runner

        with patch.object(web, 'AppRunner', side_effect=capture_runner):
            await self.server.main()
        self.addAsyncCleanup(self.runner.cleanup)
        port = self.runner.addresses[0][1]
        self.client = ClientSession(
            base_url=f'http://127.0.0.1:{port}', cookie_jar=CookieJar(unsafe=True))
        self.addAsyncCleanup(self.client.close)

    def create_session(self, address, user):
        self.security.session_db['valid'] = types.SimpleNamespace(user=user)
        return 'valid'

    async def login(self):
        response = await self.client.post('/login', data={'user': 'ham', 'pass': 'test-only'})
        self.assertEqual(await response.json(content_type=None), {'SUCCESS': 'OK'})

    async def read(self, source=1999, endpoint='favorites', status=200):
        response = await self.client.get(f'/node/{source}/{endpoint}')
        self.assertEqual(response.status, status)
        return await response.json(content_type=None)

    async def write(self, source=1999, status=200, **payload):
        response = await self.client.post(f'/node/{source}/favorites', json=payload)
        self.assertEqual(response.status, status)
        return await response.json()

    async def test_cookie_login_and_all_group_permissions_on_reads_and_writes(self):
        for endpoint in ('favorites', 'favorite-group'):
            await self.read(endpoint=endpoint, status=403)
        await self.write(status=403, action='save', node='111', label='Shared')
        response = await self.client.post('/login', data={'user': 'ham', 'pass': 'wrong'})
        self.assertIn('SECURITY', await response.json(content_type=None))
        await self.read(status=403)
        await self.login()
        for endpoint in ('favorites', 'favorite-group'):
            await self.read(endpoint=endpoint, status=403)
        await self.write(status=403, action='save', node='111', label='Shared')
        self.assertFalse(self.path.exists())
        self.security.restrictdb.add('ham2000')
        await self.write(action='save', node='111', label='Shared')
        self.assertEqual((await self.read(2000))['SUCCESS'], [{'node': '111', 'label': 'Shared'}])
        self.assertEqual((await self.read(2000, 'favorite-group'))['SUCCESS'], ['1999', '2000'])
        for endpoint in ('favorites', 'favorite-group'):
            await self.read(2001, endpoint, status=403)
        await self.write(2001, status=403, action='save', node='222', label='Denied')
        self.security.restrictdb.clear()
        for endpoint in ('favorites', 'favorite-group'):
            await self.read(endpoint=endpoint, status=403)
        await self.write(status=403, action='delete', node='111')
        await self.client.get('/auth/logout')
        await self.read(status=403)

    async def test_specific_routes_precede_general_and_preserve_list_config_voter(self):
        self.assertFalse(inspect.iscoroutinefunction(self.server._ServerWS__proc_node))
        self.assertEqual((await self.read(endpoint='favorites', status=403))['SECURITY'],
                         'Log in to manage favorites')
        response = await self.client.get('/node/listall')
        self.assertEqual(await response.json(content_type=None), {'SUCCESS': [1999, 2000, 2001]})
        expected = {'statport': 1234, 'cmdport': 1235, 'iframepre': '', 'iframepost': ''}
        self.assertEqual((await self.read(1999, 'config'))['SUCCESS'], expected)
        self.assertEqual((await self.read(2000, 'config'))['SUCCESS'], expected)
        self.assertEqual((await self.read(2000, 'voter'))['SUCCESS'],
                         {'voterport': 1236, 'votertitle': 'Voter 2000'})
        for path in ('/node/bad/favorites', '/node/1999/unknown'):
            response = await self.client.get(path)
            self.assertEqual(response.status, 400)
        for endpoint in ('favorites', 'favorite-group'):
            await self.read(9999, endpoint, status=404)
        await self.write(9999, status=404, action='delete', node='111')

    async def test_mutations_custom_path_restart_and_ungrouped_permissions(self):
        await self.login()
        self.security.restrictdb.update({'ham2000', 'ham2001'})
        self.assertEqual((await self.read(2001, 'favorite-group'))['SUCCESS'], ['2001'])
        await self.write(action='save', node='111', label='First')
        await self.write(2000, action='save', node='222', label='Second')
        await self.write(2000, action='save', node='333', label='Renamed', original_node='111')
        await self.write(action='delete', node='222')
        await self.write(2001, action='save', node='444', label='Independent')
        restarted = ServerWS(self.config, self.nodes, self.security, self.path)
        self.assertEqual(restarted.favorites.list(2000), [{'node': '333', 'label': 'Renamed'}])
        self.assertEqual(restarted.favorites.list(2001), [{'node': '444', 'label': 'Independent'}])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o640)

    async def test_invalid_requests_and_corrupt_storage_do_not_overwrite_data(self):
        await self.login()
        self.security.restricted_users.clear()
        await self.write(action='save', node='111', label='Keep')
        before = self.path.read_bytes()
        response = await self.client.post('/node/1999/favorites', data={'action': 'delete', 'node': '111'})
        self.assertEqual(response.status, 415)
        response = await self.client.post('/node/1999/favorites', json=[])
        self.assertEqual(response.status, 400)
        response = await self.client.post('/node/1999/favorites', data='{bad', headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status, 400)
        await self.write(status=400, action='save', node='*3', label='Bad')
        self.assertEqual(self.path.read_bytes(), before)
        self.path.write_text('{bad')
        await self.read(status=500)
        await self.write(status=400, action='save', node='222', label='Bad')
        self.assertEqual(self.path.read_text(), '{bad')
        with patch.object(self.server.favorites, 'list', side_effect=OSError('unreadable')):
            await self.read(status=500)
        with patch.object(self.server.favorites, 'change', side_effect=OSError('unwritable')):
            await self.write(status=500, action='delete', node='111')

    async def test_unmanaged_group_rejected_before_migration(self):
        nodes = types.SimpleNamespace(all_nodes=[1999], colo_nodes={})
        with self.assertRaisesRegex(ValueError, 'only managed nodes'):
            ServerWS(self.config, nodes, None, self.path)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
