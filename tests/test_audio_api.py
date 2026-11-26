"""Check audio API access without starting Asterisk or a web server."""

import asyncio
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from aiohttp import web
from unittest.mock import AsyncMock


def load_server():
    root = Path(__file__).resolve().parents[1] / "src/asl_allmon"
    package = types.ModuleType("asl_allmon")
    package.__path__ = [str(root)]
    sys.modules["asl_allmon"] = package
    session = types.ModuleType("aiohttp_session")

    async def get_session(request):
        return request.session

    session.get_session = get_session
    session.setup = lambda *args: None
    session.SimpleCookieStorage = type("SimpleCookieStorage", (), {})
    sys.modules["aiohttp_session"] = session
    for name in ("node_configs", "security", "web_configs"):
        sys.modules[f"asl_allmon.{name}"] = types.ModuleType(f"asl_allmon.{name}")
    return importlib.import_module("asl_allmon.announcements").AnnouncementsAddon


class AudioAPITest(unittest.TestCase):
    def test_configured_upload_limit_is_enforced_reported_and_tempfile_removed(self):
        cls = load_server()
        with tempfile.TemporaryDirectory() as directory:
            server = cls.__new__(cls)
            server.settings = types.SimpleNamespace(max_upload=1024 * 1024)
            server.audio = types.SimpleNamespace(originals=directory, ingest=AsyncMock())
            server._AnnouncementsAddon__audio_authorize = AsyncMock(return_value=[1999])
            part = types.SimpleNamespace(name='file', filename='sample.wav',
                                         read_chunk=AsyncMock(return_value=b'x' * (1024 * 1024 + 1)))
            reader = types.SimpleNamespace(next=AsyncMock(return_value=part))
            request = types.SimpleNamespace(headers={}, query={'node': '1999'},
                                            content_type='multipart/form-data',
                                            multipart=AsyncMock(return_value=reader))
            response = asyncio.run(server._AnnouncementsAddon__audio_upload(request))
            self.assertEqual(response.status, 400)
            self.assertEqual(json.loads(response.text)['ERROR'], 'Audio file exceeds 1 MB')
            server.audio.ingest.assert_not_awaited()
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_audio_api_restricts_node_and_origin(self):
        ServerWS = load_server()
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes = types.SimpleNamespace(all_nodes=[1999, 2000], colo_nodes={},
                                          nodes={1999: types.SimpleNamespace(host="localhost", port=5038),
                                                 2000: types.SimpleNamespace(host="localhost", port=5038)})
            security = types.SimpleNamespace(
                session_db={"valid": types.SimpleNamespace(user="ham")},
                restricted_users={"ham"}, restrictdb={"ham1999"})
            server = ServerWS(None, nodes, security)
            self.assertEqual(server.audio.state, Path("/etc/allmon3/audio"))
            server.audio.state = Path(temp_dir) / "state"
            server.audio.cache = Path(temp_dir) / "cache"
            server.audio.originals = server.audio.state / "audio-originals"
            server.audio.converted = server.audio.cache / "audio"
            server.audio.db_path = server.audio.state / "audio.sqlite3"
            server.audio.initialize()

            class Request:
                session = {}
                headers = {}
                host = "radio.example"
                content_type = "application/json"
                match_info = {"action": "queue"}

                async def json(self):
                    return {"node": 2000, "name": "News", "items": ["source:arn"]}

            request = Request()
            state = server._AnnouncementsAddon__audio_state
            mutate = server._AnnouncementsAddon__audio_mutation
            with self.assertRaises(web.HTTPForbidden):
                asyncio.run(state(request))
            request.session = {"auth_sess": "valid"}
            self.assertEqual(json.loads(asyncio.run(state(request)).text)["SUCCESS"]["nodes"], [1999])
            with self.assertRaises(web.HTTPForbidden):
                asyncio.run(mutate(request))
            request.headers = {"Origin": "https://evil.example"}
            with self.assertRaises(web.HTTPForbidden):
                asyncio.run(mutate(request))


if __name__ == "__main__":
    unittest.main()
