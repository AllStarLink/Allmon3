#!/usr/bin/python3
#
# Copyright(C) 2023 AllStarLink
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
import time
import websockets
from .. import node_configs, security, web_configs

__BUILD_ID = "1.0.0"
log = logging.getLogger(__name__)

class ServerWS:
    """ Node command WS client """

    __MAX_MSG_LEN = 256

    def __init__(self, configs_web, configs_node, server_security):
        self.config_web = configs_web
        self.config_nodes = configs_node
        self.httpserver = web.Application()
        self.server_security = server_security

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

        finally:
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
            log.info("invalid login %s:%s from %s", 
                req.get("user"), req.get("pass"), client_ip)

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
        
        finally:
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
                    else:
                        r_txt = "NONE"
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
            log.debug("index error")
            r_txt = None

        except Exception as e:
            log.debug(e)

        finally:
            if r_txt:
                r_json = self.__get_json_success(r_txt)
                return web.Response(text=r_json, content_type="text/json")
    
            return web.Response(status=400)

    def __proc_ui_html(self):
        ui_html = dict()
        ui_html.update({ "HEADER_TITLE" : self.config_web.header_title })
        ui_html.update({ "HEADER_LOGO" : self.config_web.header_logo })
        ui_html.update({ "HOME_BUTTON_URL" : self.config_web.home_loc })
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
