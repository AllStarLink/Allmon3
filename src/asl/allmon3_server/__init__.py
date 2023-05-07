#!/usr/bin/python3
# almon3.py - Monitor ASL Asterisk server for events
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import asyncio
import logging
import json
import re
import socket
import websockets
from .. import node_configs, web_configs

__BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class ServerWS:
    """ Node command WS client """

    __MAX_MSG_LEN = 256

    def __init__(self, configs_web, configs_node):
        self.config_web = configs_web
        self.config_nodes = configs_node

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

    def __proc_auth(self, c):
        if c[1] == "auth":
            return "unimplemented"

        raise ServerWSException("unknown secondary command for auth")

    ##
    ## Node Functions
    ##

    def __proc_node(self, c):
        if c[1] == "listall":
            return self.__get_json_success(self.__proc_node_listall())

        try:
            if re.match(r"^[0-9]+$", c[1]):
                if c[2] == "config":
                    if c[1] in self.config_nodes.colo_nodes:
                        node = self.config_nodes.colo_nodes[c[1]]
                    else:
                        node = c[1]
                    if self.config_nodes.nodes[node]:
                        return self.__get_json_success(self.__proc_node_config(node))
    
                    raise ServerWSException("unknown node")
    
                raise ServerWSException("unknown tertiary command for node NODE")
    
            raise ServerWSException("unknown secondary command for node")
        
        except IndexError:
            raise ServerWSException("malformed command")
    
        except KeyError:
            raise ServerWSException("unknown node")

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

    def __proc_ui(self, c):
        if c[1] == "custom":
            if c[2] == "html":
                return self.__get_json_success(self.__proc_ui_html())
            if c[2] == "menu":
                if self.config_web:
                    return self.__get_json_success(json.dumps(self.config_web.menu))
                return self.__get_json_success("NONE")
            if c[2] == "overrides":
                return self.__get_json_success(json.dumps(self.config_web.node_overrides))

            raise ServerWSException(self.__get_json_error("unknown tertiary command for ui custom"))

        raise ServerWSException(self.__get_json_error("unknown secondary commend for ui"))

    def __proc_ui_html(self):
        ui_html = dict()
        ui_html.update({ "HEADER_TITLE" : self.config_web.header_title })
        ui_html.update({ "HEADER_LOGO" : self.config_web.header_logo })
        ui_html.update({ "HOME_BUTTON_URL" : self.config_web.home_loc })
        return json.dumps(ui_html)

    ##
    ## Server Logic
    ##

    async def handler(self, websocket):
        log.debug("entering serverws handler for %s", websocket.remote_address)
    
        try:
            while True:
                message = await websocket.recv()
                log.debug(f"ws: {message}")
                c = message.split(" ")
                log.debug(c)
                if c[0] == "auth":
                    response = self.__proc_auth(c)
                elif c[0] == "node":
                    response = self.__proc_node(c)
                elif c[0] == "ui":
                    response = self.__proc_ui(c)
                elif c[0] == "exit":
                    await websocket.send(self.__get_json_success("bye"))
                    await websocket.clost()
                    continue
                else:
                    raise ServerWSException("unknown command prefix") 
    
                await websocket.send(response)
        
        except asyncio.exceptions.IncompleteReadError:
            log.info("Other side went away: %x", websocket.remote_address)
    
        except websockets.exceptions.ConnectionClosedError:
            log.info("ConnctionClosed with Error from %s", websocket.remote_address)
    
        except websockets.exceptions.ConnectionClosedOK:
            log.info("ConnctionClosed from %s", websocket.remote_address)
    
        except BrokenPipeError as e:
            log.error("received BrokenPipeError")
    
        except socket.timeout as e:
            log.error("received socket.timeout")
    
        except ConnectionResetError as e:
            log.error("received ConnectionResetError")
    
        except ServerWSException as e:
            log.error(e)
            await websocket.send(self.__get_json_error(e))
            await websocket.close()
    
    async def main(self):
        async with websockets.serve(
            self.handler,
            host = None,
            port = self.config_web.http_port,
            logger = log,
            compression = None,
            ping_timeout = None
        ):
            await asyncio.Future()

class ServerWSException(Exception):
    """ specific Exception for class """
