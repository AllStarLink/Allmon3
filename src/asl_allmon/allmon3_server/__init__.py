#!/usr/bin/python3
#
# Copyright(C) @@COPYDATE@@ AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

from aiohttp import web
from aiohttp_session import get_session, setup
from aiohttp_session import SimpleCookieStorage
import asyncio
import base64
from itertools import cycle
import json
import logging
import re
import socket
import time
import websockets
from .. import logs, node_configs, security, web_configs

__BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class ServerWS:
    """ Node command WS client """

    __MAX_MSG_LEN = 256

    def __init__(self, configs_web, configs_node, server_security):
        self.config_web = configs_web
        self.config_nodes = configs_node
        self.httpserver = web.Application()
        self.server_security = server_security
        local_hosts = {"127.0.0.1", "localhost", "::1", socket.gethostname(), socket.getfqdn()}
        try:
            local_hosts.update(info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None))
        except socket.gaierror:
            pass
        local_nodes = [n for n in configs_node.all_nodes
                       if configs_node.nodes[configs_node.colo_nodes.get(n, n)].host in local_hosts]
        self.logs = logs.LogService(local_nodes)

    async def __logs_allowed(self, request):
        session = await get_session(request)
        session_id = session.get("auth_sess")
        if session_id not in self.server_security.session_db:
            raise web.HTTPForbidden(text='Log in to view logs')
        user = self.server_security.session_db[session_id].user
        allowed = {n for n in self.logs.host_nodes
                   if user not in self.server_security.restricted_users
                   or f"{user}{n}" in self.server_security.restrictdb}
        if not allowed:
            raise web.HTTPForbidden(text='No permitted local logging nodes')
        return allowed

    @staticmethod
    def __logs_response(data):
        return web.json_response({"SUCCESS": data}, headers={"Cache-Control": "no-store"})

    async def __logs_state(self, request):
        allowed = await self.__logs_allowed(request)
        try:
            return self.__logs_response(self.logs.snapshot(allowed))
        except logs.LogError as exc:
            return web.json_response({"ERROR": str(exc)}, status=503)

    async def __logs_read(self, request):
        allowed = await self.__logs_allowed(request)
        kind = request.match_info["kind"]
        node = request.query.get("node", "")
        if kind == "messages":
            if not self.logs.host_nodes <= allowed:
                raise web.HTTPForbidden(text='Shared messages require access to every local node')
        elif node not in allowed:
            raise web.HTTPForbidden(text='Not permitted on this node')
        try:
            limit = int(request.query.get("limit", "200"))
            return self.__logs_response(await self.logs.read(kind, node, limit))
        except (logs.LogError, ValueError) as exc:
            return web.json_response({"ERROR": str(exc)}, status=400)
        except OSError:
            return web.json_response({"ERROR": "Log reader is unavailable"}, status=503)

    async def __logs_toggle(self, request):
        allowed = await self.__logs_allowed(request)
        node = request.match_info["node"]
        if node not in allowed:
            raise web.HTTPForbidden(text='Not permitted on this node')
        origin = request.headers.get("Origin")
        if origin:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request.host.lower():
                raise web.HTTPForbidden(text='Logging request origin is not allowed')
        if request.content_type != "application/json":
            raise web.HTTPUnsupportedMediaType(text='Expected JSON')
        try:
            payload = await request.json()
            if not isinstance(payload, dict) or set(payload) != {"enabled"}:
                raise logs.LogError('Expected an enabled boolean')
            result = self.logs.set_enabled(node, payload['enabled'])
            log.info('Connection logging for node %s set to %s', node, result['enabled'])
            return self.__logs_response(result)
        except (logs.LogError, ValueError) as exc:
            return web.json_response({"ERROR": str(exc)}, status=400)
        except OSError:
            return web.json_response({"ERROR": "Unable to save logging setting"}, status=503)

    @staticmethod
    def __get_json_error(message):
        return f"{{ \"ERROR\" : \"{message}\" }}"

    @staticmethod
    def __get_json_success(message):
        if re.match(r'^[\{\[]', message):
            return f"{{ \"SUCCESS\" : {message} }}"
        return f"{{ \"SUCCESS\" : \"{message}\" }}"

    @staticmethod
    def __get_json_security(message):
        return f"{{ \"SECURITY\" : \"{message}\" }}"

    ##
    ## Security Auth Functions
    ##
    async def __proc_auth(self, request):
        try:
            c = request.url.path.split("/")
            r_json = None
            if c[2] == "check":
                session = await get_session(request)
                session["last_auth_check"] = time.time()
                r_json = self.__get_json_security("No Session")
                if "auth_sess" in session:
                    if session["auth_sess"] in self.server_security.session_db:
                        r_json = self.__get_json_success("Logged In")

            elif c[2] == "logout":
                session = await get_session(request)
                session["auth_sess"] = ""
                r_json = self.__get_json_security("No Session")

        except (IndexError, KeyError):
            log.debug("IndexError/KeyError")
            r_txt = None

        if r_json:
            return web.Response(text=r_json, content_type="text/json")

        return web.Response(status=400)

    async def __proc_login(self, request):
        req = await request.post()
        session = await get_session(request)

        if "X-Forwarded-For" in request.headers:
            client_ip = request.headers.get("X-Forwarded-For")
        else:
            client_ip = request.remote

        is_valid = self.server_security.validate(req.get("user"), req.get("pass"))
        if is_valid:
            session_id = self.server_security.create_session(client_ip, req.get("user"))
            session["auth_sess"] = session_id
            r_txt = self.__get_json_success("OK")
            log.info("successful login by user %s from %s",
                req.get("user"), client_ip)
        else:
            r_txt = self.__get_json_security("invalid user or pass")
            session["auth_sess"] = None
            log.info("invalid login %s from %s",
                req.get("user"), client_ip)

        return web.Response(text=r_txt, content_type="text/json")

    ##
    ## Node Functions
    ##

    def __proc_node(self, request):
        try:
            c = request.url.path.split("/")
            r_txt = None
            if c[2] == "listall":
                r_txt = self.__proc_node_listall()

            elif re.match(r"^[0-9]+$", c[2]):
                node = int(c[2])
                if int(c[2]) in self.config_nodes.colo_nodes:
                    node = self.config_nodes.colo_nodes[int(c[2])]

                if c[3] == "config":
                    log.debug("self.__proc_node_config(%s)", node)
                    r_txt = self.__proc_node_config(node)

                if c[3] == "voter":
                    log.debug("self.__proc_voter_config(%s, %s)", node, int(c[2]))
                    r_txt = self.__proc_voter_config(node, int(c[2]))

        except (IndexError, KeyError):
            log.debug("IndexError/KeyError")
            r_txt = None

        if r_txt:
            r_json = self.__get_json_success(r_txt)
            return web.Response(text=r_json, content_type="text/json")

        return web.Response(status=400)

    def __proc_node_listall(self):
        ret = []
        for n in self.config_nodes.all_nodes:
            ret.append(int(n))
        return json.dumps(ret)

    def __proc_node_config(self, node):
        nc = dict()
        nc.update({ "statport" : self.config_nodes.nodes[node].monport })
        nc.update({ "cmdport" : self.config_nodes.nodes[node].cmdport })
        nc.update({ "iframepre" : self.config_nodes.nodes[node].iframepre })
        nc.update({ "iframepost" : self.config_nodes.nodes[node].iframepost })
        return json.dumps(nc)

    def __proc_voter_config(self, conf_node, voter_node):
        try:
            vc = dict()
            vc.update({ "voterport" : self.config_nodes.nodes[conf_node].voterports[voter_node] })
            if voter_node in self.config_web.voter_titles:
                vc.update({ "votertitle" : self.config_web.voter_titles[voter_node] })
            else:
                vc.update({ "votertitle" : f"Voter {voter_node}" })
            return json.dumps(vc)

        except Exception as e:
            log.error(e)
            return None

    ##
    ## UI Customizations
    ##

    def __proc_ui(self, request):
        try:
            c = request.url.path.split("/")
            r_txt = None
            if c[2] == "custom":
                if c[3] == "html":
                    r_txt = self.__proc_ui_html()
                elif c[3] == "menu":
                    if self.config_web:
                        r_txt = self.config_web.menu
                        if r_txt == "":
                            r_txt = "{}"
                    else:
                        r_txt = "{}"
                elif c[3] == "overrides":
                    r_txt = json.dumps(self.config_web.node_overrides)
                elif c[3] == "commands":
                    r_txt = json.dumps(self.config_web.commands)
                elif c[3] == "nodecommands":
                    if c[4] in self.config_web.per_node_commands:
                        r_txt = json.dumps(self.config_web.per_node_commands[c[4]])
                    else:
                        r_txt = "{}"

        except (IndexError, KeyError):
            log.exception("index error")
            r_txt = None

        except Exception as e:
            log.debug(e)

        if r_txt:
            r_json = self.__get_json_success(r_txt)
            return web.Response(text=r_json, content_type="text/json")

        return web.Response(status=400)

    def __proc_ui_html(self):
        ui_html = dict()
        ui_html.update({ "HEADER_TITLE" : self.config_web.header_title })
        ui_html.update({ "HEADER_LOGO" : self.config_web.header_logo })
        ui_html.update({ "HOME_BUTTON_URL" : self.config_web.home_loc })
        ui_html.update({ "CONFIG_MENU_SINGLE_TARGET" : self.config_web.menu_target })
        return json.dumps(ui_html)

    ##
    ## Cmd Prep Process
    ##
    async def __proc_cmd(self, request):
        try:
            req = await request.post()
            session = await get_session(request)

            r_json = None
            user_is_authenticated = False
            if "auth_sess" in session:
                if session["auth_sess"] in self.server_security.session_db:
                    user_is_authenticated = True
                    cmd = req.get("cmd")
                    user = self.server_security.session_db[session["auth_sess"]].user
                    node = int(req.get("node"))
                    uncombo = f"{user}{node}"

                    user_is_restricted = False
                    if user in self.server_security.restricted_users:
                        if uncombo not in self.server_security.restrictdb:
                            log.info("%s restricted from commands on node %s", user, node)
                            user_is_restricted = True
                        else:
                            log.info("%s has restrictions but permitted to node %s", user, node)
                    else:
                        log.info("%s has no node restrictions", user)

            if user_is_authenticated and not user_is_restricted:
                if node in self.config_nodes.colo_nodes:
                    node = self.config_nodes.colo_nodes[node]
                log.debug("actionable node: %s", node)
                key = self.config_nodes.nodes[node].password
                log.debug("key: %s", key)
                cmd_x = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in zip(cmd, cycle(key)))
                cmd_x_b = base64.b64encode(cmd_x.encode("UTF-8")).decode("UTF-8")
                log.debug("cmd: %s", cmd_x_b)
                cmdport = self.config_nodes.nodes[node].cmdport
                log.debug("cmdport: %s", cmdport)
                url = f"ws://localhost:{cmdport}"
                async with websockets.connect(url, ping_timeout=None) as websocket:
                    await websocket.send(cmd_x_b)
                    async for message in websocket:
                        r_json = f"{{ \"SUCCESS\" : \"{message}\" }}"
            else:
                r_json = f"{{ \"ERROR\" : \"user not authorized\" }}"

            if r_json:
                return web.Response(text=r_json, content_type="text/json")

            return web.Response(status=400)

        except KeyError as e:
            log.debug(e)

        except Exception:
            pass

    ##
    ## Server Logic
    ##
    async def main(self):

        # Session
        setup(self.httpserver, SimpleCookieStorage())

        # Handlers for different API commands
        api_routes = [
            web.get("/logs/state", self.__logs_state),
            web.get(r"/logs/{kind:connections|messages}", self.__logs_read),
            web.post(r"/logs/nodes/{node:[0-9]+}", self.__logs_toggle),
            web.post("/cmd", self.__proc_cmd),
            web.post("/login", self.__proc_login),
            web.get(r"/auth/{cmd:.*}", self.__proc_auth),
            web.get(r"/node/{cmd:.*}", self.__proc_node),
            web.get(r"/ui/{cmd:.*}", self.__proc_ui)
            ]
        self.httpserver.add_routes(api_routes)
        runner = web.AppRunner(self.httpserver)
        await runner.setup()
        site = web.TCPSite(runner,
            self.config_web.ws_bind_addr,
            self.config_web.http_port)
        await site.start()


class ServerWSException(Exception):
    """ specific Exception for class """
