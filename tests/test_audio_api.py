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
    return importlib.import_module("asl_allmon.allmon3_server").ServerWS


class AudioAPITest(unittest.TestCase):
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
            state = server._ServerWS__audio_state
            mutate = server._ServerWS__audio_mutation
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
