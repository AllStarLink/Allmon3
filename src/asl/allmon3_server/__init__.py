#!/usr/bin/python3
# almon3.py - Monitor ASL Asterisk server for events
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

from aiohttp import web
import asyncio
import logging
import json
import re
#import socket
#import websockets
from .. import node_configs, web_configs

__BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class ServerWS:
    """ Node command WS client """

    __MAX_MSG_LEN = 256

    def __init__(self, configs_web, configs_node):
        self.config_web = configs_web
        self.config_nodes = configs_node
        self.httpserver = web.Application()

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
    def __proc_auth(self, request):
        return web.Response(status=503)

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
                if c[3] == "config":
                    if c[2] in self.config_nodes.colo_nodes:
                        node = self.config_nodes.colo_nodes[c[2]]
                    else:
                        node = c[2]
                    if self.config_nodes.nodes[node]:
                        r_txt = self.__proc_node_config(node)
    
        except (IndexError, KeyError):
            r_txt = None
        
        finally:
            if r_txt:
                r_json = self.__get_json_success(r_txt)
                return web.Response(text=r_json, content_type="text/json")
    
            return web.Response(status=400)

    def __proc_node_listall(self):
        ret = []
        for n in self.config_nodes.nodes:
            ret.append(int(n))
        return json.dumps(ret)

    def __proc_node_config(self, node):
        nc = dict()
        nc.update({ "statport" : self.config_nodes.nodes[node].monport })
        nc.update({ "cmdport" : self.config_nodes.nodes[node].cmdport })
        nc.update({ "voterport" : self.config_nodes.nodes[node].vmonport })
        return json.dumps(nc)

            

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
                        r_txt = json.dumps(self.config_web.menu)
                    else:
                        r_txt = "NONE"
                elif c[3] == "overrides":
                    r_txt = json.dumps(self.config_web.node_overrides)
    
        except (IndexError, KeyError):
            r_txt = None

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
    ## Server Logic
    ##

    async def handler(self, request):
        log.error("rel_url: " + request.rel_url)
        log.error("path_qs: " + request.path_qs)
        return web.Response(text="Hello")

    async def main(self):

        # Handlers for different API commands
        api_routes = [
            web.get(r"/auth/{cmd:.*}", self.__proc_auth),
            web.get(r"/node/{cmd:.*}", self.__proc_node),
            web.get(r"/ui/{cmd:.*}", self.__proc_ui)
            ]
        self.httpserver.add_routes(api_routes)
        runner = web.AppRunner(self.httpserver)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", self.config_web.http_port)
        await site.start()


class ServerWSException(Exception):
    """ specific Exception for class """
