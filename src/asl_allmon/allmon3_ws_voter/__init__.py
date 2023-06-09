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
import socket
import time
from time import sleep
import websockets
from .. import ami_conn, ami_parser, node_configs, node_db, ws_broadcaster

__BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class NodeVoterWS:
    """ Node voter WS client """

    def __init__(self, node, node_config, web_config):
        self.node_id = node
        self.node_config = node_config
        self.ami = None
        self.connections = set()
        self.web_config = web_config
        self.voter_ws = ws_broadcaster.WebsocketBroadcaster()

    async def handler(self, websocket):
        log.debug("entering voter handler(%s} for %s", self.node_id, websocket.remote_address)
        self.connections.add(websocket)
        try:
            async for message in self.voter_ws:
                await websocket.send(message)

        except asyncio.exceptions.IncompleteReadError:
            log.info("Other side went away: %s", websocket.remote_address)

        except websockets.exceptions.ConnectionClosedError:
            log.info("ConnctionClosed with Error from %s", websocket.remote_address)
            self.connections.remove(websocket)

        except websockets.exceptions.ConnectionClosedOK:
            log.info("ConnctionClosed from %s", websocket.remote_address)
            self.connections.remove(websocket)


    # Websocket broadcaster
    async def broadcast(self):
        log.debug("enter node_voter_broadcast()")
        asl_ok = True
        parser = ami_parser.AMIParser(self.ami)
        last_socket_send = time.time()
 
        while True:
            if asl_ok:
                try:
                    if len(self.connections) > 0:
                        log.debug("node %s voter connections: %d", self.node_id, len(self.connections))
                        last_socket_send = time.time()
                        message = parser.parse_voter_data(self.node_id)
                        self.voter_ws.publish(message)

                    else:
                        log.debug("node %s voter connections: %s", self.node_id, len(self.connections))
                        now = time.time()
                        if ( now - last_socket_send ) > 60 :
                            log.debug("Node %s: sending keepalive command", self.node_id)
                            parser.asl_cmd("core show version")
                            last_socket_send = time.time()

                except BrokenPipeError:
                    log.error("received BrokenPipeError; trying to reconnect")
                    asl_ok = False
                except socket.timeout:
                    log.error("received socket.timeout; trying to reconnect")
                    asl_ok = False
                except ConnectionResetError:
                    log.error("received ConnectionResetError; trying to reconnect")
                    asl_ok = False
                except OSError as e:
                    log.error("received OSError: %s; trying to reconnect", e)
                    asl_ok = False

                # Sleep for the polling time
                log.debug("voter asyncio.sleep(%s)", self.node_config.vpollinterval)
                await asyncio.sleep(self.node_config.vpollinterval)
    
            else:
                # If we exited out of asl_ok without throwing an exception
                # then something went wrong with the asl socket. Loop around
                # here trying to reconnect for the timeout interval and then
                # let the main_loop continue
                self.ami.close()
                asl_dead = True
                retry_counter = 0
    
                while asl_dead:
                    log.debug("sleeping for RETRY_INTERVAL of %s", self.node_config.retryinterval)
                    sleep(self.node_config.retryinterval)
                    retry_counter += 1
    
                    if self.node_config.retrycount == -1 or self.node_config.retrycount <= retry_counter:
                        log.debug("attempting reconnection retry #%d", retry_counter)
    
                        c_stat = self.ami.asl_create_connection_nofail()
                        if c_stat:
                            log.info("connection reestablished after %d retries", retry_counter)
                            asl_dead = False
                    else:
                        log.error("count not reestablish connection after %d retries - exiting", retry_counter)
                        raise NodeVoterWSException(f"count not reestablish connection after {retry_counter} retries - exiting")
 
                # re-enable the innter loop processing
                asl_ok = True
    
    
    # Primary broadcaster
    async def main(self):
        log.debug("enter node_voter_main()")
        try:
	        loop = asyncio.get_event_loop()
	        self.voter_ws.set_waiter(asyncio.Future(loop=loop))
	        self.ami = ami_conn.AMI(self.node_config.host, self.node_config.port,
	            self.node_config.user, self.node_config.password)
	        async with websockets.serve(
	            self.handler,
	            host = self.web_config.ws_bind_addr,
	            port = self.node_config.voterports[self.node_id],
	            logger = log
	        ):
	            await self.broadcast()

        except ami_conn.AMIException:
            log.error("Terminating asyncio worker for %s:%s on %s due to unreachable AMI",
                self.node_config.host, self.node_config.port, self.node_config.voterports[self.node_id])
            log.error("AMI instances must be available at start. See --nodes or remove the config")
            return None

	
class NodeVoterWSException(Exception):
    """ exception for class """
