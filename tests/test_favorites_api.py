"""Check favorites API access without starting Asterisk or a web server."""

import asyncio
import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


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


class FavoritesAPITest(unittest.TestCase):
    def test_login_and_node_restrictions_apply_to_reads_and_writes(self):
        ServerWS = load_server()
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes = types.SimpleNamespace(all_nodes=[1999], colo_nodes={})
            security = types.SimpleNamespace(
                session_db={"valid": types.SimpleNamespace(user="ham")},
                restricted_users={"ham"}, restrictdb={"ham1999"})
            server = ServerWS(None, nodes, security, Path(temp_dir) / "favorites.json")

            class Request:
                match_info = {"node": "1999"}
                content_type = "application/json"
                url = types.SimpleNamespace(path="/node/1999/favorites")
                session = {}

                async def json(self):
                    return {"action": "save", "node": "62154", "label": "Starbase 4"}

            request = Request()
            write = server._ServerWS__proc_favorites_write
            read = server._ServerWS__proc_node
            self.assertEqual(asyncio.run(write(request)).status, 403)
            self.assertEqual(asyncio.run(read(request)).status, 403)
            request.session = {"auth_sess": "valid"}
            self.assertEqual(asyncio.run(write(request)).status, 200)
            result = json.loads(asyncio.run(read(request)).text)
            self.assertEqual(result["SUCCESS"], [
                {"node": "62154", "label": "Starbase 4"}])
            security.restrictdb.clear()
            self.assertEqual(asyncio.run(write(request)).status, 403)
            self.assertEqual(asyncio.run(read(request)).status, 403)


if __name__ == "__main__":
    unittest.main()
