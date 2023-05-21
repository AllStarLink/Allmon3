#!/usr/bin/python3
# almon3.py - Monitor ASL Asterisk server for events
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import asyncio
import base64
import binascii
import logging
import re
import socket
import time
from time import sleep
import websockets
from .. import ami_conn, ami_parser, node_configs, node_db, ws_broadcaster

__BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class NodeCmdWS:
    """ Node command WS client """

    __MAX_MSG_LEN = 256

    def __init__(self, node, node_config):
        self.node_id = node
        self.node_config = node_config
        self.cmd_ws = ws_broadcaster.WebsocketBroadcaster()

    async def handler(self, websocket):
        log.debug("entering node_cmd_handler(%s) for %s", self.node_id, websocket.remote_address)
    
        try:
            message = await websocket.recv()
            cmd = ami_parser.decrypt_msg(message, self.node_config.password)
            if len(cmd) > self.__MAX_MSG_LEN:
                log.error("message > len(%d) was ignored from %s", self.__MAX_MSG_LEN, websocket.remote_address)
                await websocket.send(f"ERR: cmd > {self.__MAX_MSG_LEN} chars not permitted")
                await websocket.close()
                return
    
            if not re.match(r"^(core show|iax2|rpt|voter)", cmd):
                log.error("unsupported command: %s from %s", cmd, websocket.remote_address)
                await websocket.send("ERR: last command not a supported type")
                await websocket.close()
                return
    
            log.debug("cmd_asl create")
    
            a = ami_conn.AMI(self.node_config.host, self.node_config.port, 
                self.node_config.user, self.node_config.password)
            parser = ami_parser.AMIParser(a)
            response = parser.asl_cmd(cmd)
            a.close()
            response_b64 = base64.b64encode(response.encode("UTF-8"))
            await websocket.send(response_b64.decode("UTF-8"))

        except ami_conn.AMIException:
            log.error("Could not connect to AMI interface %s:%s",
                self.node_config.host, self.node_config.port)
            log.error("Command was ignored")
    
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
    
        except Exception as e:
            log.error(e)
            await websocket.send("nonsense in command string")
            await websocket.close()
            raise e
    
    async def main(self):
        loop = asyncio.get_event_loop()
        self.cmd_ws.set_waiter(asyncio.Future(loop=loop))
        async with websockets.serve(
            self.handler,
            host = None,
            port = self.node_config.cmdport,
            logger = log,
            compression = None,
            ping_timeout = None
        ):
            await asyncio.Future()

class NodeCmdWSException(Exception):
    """ specific Exception for class """
