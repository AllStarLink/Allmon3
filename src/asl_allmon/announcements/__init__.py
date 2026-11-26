"""Optional announcements add-in; not imported by a base-only installation."""
import asyncio
import json
import logging
import os
from pathlib import Path
import re
import socket
import tempfile
import aiohttp
from aiohttp import web
from aiohttp_session import get_session
from .. import audio, audio_tot
from ..announcement_config import AnnouncementConfig

log = logging.getLogger(__name__)

class AnnouncementsAddon:
    metadata = {'id': 'announcements', 'label': 'Announcements',
                'script': 'addons/announcements/audio.js',
                'fragment': 'addons/announcements/panel.html',
                'stylesheet': 'addons/announcements/audio.css'}

    def __init__(self, configs_web, configs_node, server_security):
        self.config_web = configs_web
        self.config_nodes = configs_node
        self.server_security = server_security
        self.settings = AnnouncementConfig()
        self.request_limit = self.settings.max_upload + 1024 * 1024
        local_hosts = {"127.0.0.1", "localhost", "::1", socket.gethostname(), socket.getfqdn()}
        try:
            local_hosts.update(info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None))
        except socket.gaierror:
            pass
        explicit = self.settings.local_nodes
        local_nodes = [n for n in configs_node.all_nodes
                       if (configs_node.nodes[configs_node.colo_nodes.get(n, n)].host in local_hosts
                           and (not explicit or n in explicit))]
        timeout_guard = audio_tot.TimeoutGuard(
            "/var/lib/allmon3/audio-tot", audio_tot.ami_command(configs_node),
            audio_tot.identities(configs_node, local_nodes))
        self.audio = audio.AudioService(self.settings.state_dir, self.settings.cache_dir,
                                        local_nodes, self.__play_audio, timeout_guard, self.__stop_audio, settings=self.settings)

    async def __audio_nodes_for_user(self, request):
        session = await get_session(request)
        session_id = session.get("auth_sess")
        if session_id not in self.server_security.session_db:
            return []
        user = self.server_security.session_db[session_id].user
        return [node for node in self.audio.nodes
                if user not in self.server_security.restricted_users
                or f"{user}{node}" in self.server_security.restrictdb]

    async def __audio_authorize(self, request, node=None):
        allowed = await self.__audio_nodes_for_user(request)
        if not allowed or (node is not None and node not in allowed):
            raise web.HTTPForbidden(text=json.dumps({"SECURITY": "Log in with access to a local playback node"}),
                                    content_type="application/json")
        return allowed

    @staticmethod
    def __audio_check_origin(request):
        # Multipart upload is a simple browser POST, so verify its Origin.
        # Host is preserved by the bundled Apache and Nginx proxy configs.
        origin = request.headers.get("Origin")
        if origin:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request.host.lower():
                raise web.HTTPForbidden(text=json.dumps({"SECURITY": "Audio request origin is not allowed"}),
                                        content_type="application/json")

    async def __play_audio(self, node, filename_no_extension):
        if node not in self.audio.nodes:
            raise audio.AudioError("Playback requires Asterisk on this Allmon3 host")
        await audio_tot.ami_command(self.config_nodes)(
            node, f"rpt playback {node} {filename_no_extension}")

    async def __stop_audio(self, node):
        if node not in self.audio.nodes:
            raise audio.AudioError("Playback requires Asterisk on this Allmon3 host")
        # app_rpt 3.10.8 has no per-file pause API. COP 24 interrupts local
        # telemetry/playback; it can also clear concurrent node announcements.
        await audio_tot.ami_command(self.config_nodes)(node, f"rpt cmd {node} cop 24 xxx")

    async def __audio_state(self, request):
        allowed = await self.__audio_authorize(request)
        return web.json_response({"SUCCESS": self.audio.snapshot(allowed)})

    async def __audio_upload(self, request):
        self.__audio_check_origin(request)
        try:
            node = int(request.query.get("node", ""))
        except ValueError:
            raise web.HTTPBadRequest(text="Select a local node")
        await self.__audio_authorize(request, node)
        if not request.content_type.startswith("multipart/"):
            raise web.HTTPUnsupportedMediaType()
        reader = await request.multipart()
        part = await reader.next()
        if not part or part.name != "file" or not part.filename:
            raise web.HTTPBadRequest(text="Choose an audio file")
        safe_name = part.filename.replace("\\", "/").split("/")[-1]
        extension = os.path.splitext(safe_name)[1].lower()
        if extension not in audio.EXTENSIONS:
            raise web.HTTPBadRequest(text="Unsupported audio format")
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.audio.originals, suffix=extension,
                                             delete=False) as target:
                temp_name = target.name
                size = 0
                while chunk := await part.read_chunk(65536):
                    size += len(chunk)
                    if size > self.settings.max_upload:
                        raise audio.AudioError(f"Audio file exceeds {self.settings.max_upload // (1024 * 1024)} MB")
                    target.write(chunk)
            asset_id = await self.audio.ingest(temp_name, safe_name, extension)
            return web.json_response({"SUCCESS": {"id": asset_id}})
        except audio.AudioError as e:
            return web.json_response({"ERROR": str(e)}, status=400)
        finally:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)

    async def __audio_mutation(self, request):
        self.__audio_check_origin(request)
        if request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType()
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise audio.AudioError("Invalid audio request")
            node = payload.get("node")
            if type(node) is not int:
                raise audio.AudioError("Select a local playback node")
            await self.__audio_authorize(request, node)
            action = request.match_info["action"]
            if action == "enable":
                allowed = await self.__audio_authorize(request)
                if not set(self.audio.nodes).issubset(allowed):
                    raise web.HTTPForbidden(text="Master playback control requires access to every local audio node")
                result = self.audio.set_playback_enabled(payload.get("enabled"))
            elif action == "queue":
                result = self.audio.enqueue(node, payload.get("name"), payload.get("items"))
            elif action == "schedule":
                result = self.audio.create_schedule(node, payload.get("name"), payload.get("items"),
                                                    payload.get("recurrence"), payload.get("run_at"),
                                                    payload.get("weekday"), payload.get("local_time"))
            elif action in {"pause", "resume", "stop"}:
                result = await self.audio.control_job(node, payload.get("id"), action)
            elif action == "fetch":
                result = await self.audio.fetch_source(payload.get("source"))
            else:
                raise audio.AudioError("Unknown audio action")
            return web.json_response({"SUCCESS": {"id": result}})
        except (audio.AudioError, ValueError, TypeError) as e:
            return web.json_response({"ERROR": str(e)}, status=400)
        except (aiohttp.ClientError, OSError, asyncio.TimeoutError) as e:
            log.error("audio action failed: %s", e)
            return web.json_response({"ERROR": "Audio source or storage unavailable"}, status=502)

    async def __audio_remove(self, request):
        self.__audio_check_origin(request)
        allowed = await self.__audio_authorize(request)
        try:
            kind, ident = request.match_info["kind"], request.match_info["id"]
            if not re.fullmatch(r"[0-9a-f]{32}", ident):
                raise audio.AudioError("Invalid ID")
            if kind == "schedule":
                self.audio.delete_schedule(ident, allowed)
            elif kind == "job":
                self.audio.cancel_pending(ident, allowed)
            else:
                raise audio.AudioError("Unknown item")
            return web.json_response({"SUCCESS": "Removed"})
        except audio.AudioError as e:
            return web.json_response({"ERROR": str(e)}, status=400)

    async def __audio_preview(self, request):
        await self.__audio_authorize(request)
        try:
            filename = self.audio.asset_original(request.match_info["id"])
        except audio.AudioError:
            raise web.HTTPNotFound()
        return web.FileResponse(filename, headers={"Cache-Control": "no-store"})


    def routes(self):
        return [
            web.get('/audio/state', self.__audio_state),
            web.post(r'/audio/{action:upload}', self.__audio_upload),
            web.post(r'/audio/{action:queue|schedule|fetch|pause|resume|stop|enable}', self.__audio_mutation),
            web.delete(r'/audio/{kind:schedule|job}/{id:[0-9a-f]+}', self.__audio_remove),
            web.get(r'/audio/preview/{id:[0-9a-f]+}', self.__audio_preview),
        ]

    def initialize(self):
        self.audio.initialize()

    async def run(self):
        await self.audio.run()
