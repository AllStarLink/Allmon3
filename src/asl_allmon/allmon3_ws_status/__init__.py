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
import json
import logging
import socket
import time
from time import sleep
from websockets.server import serve
from websockets import exceptions as ws_exceptions
from .. import ami_conn, ami_parser, node_configs, node_db, ws_broadcaster


__BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class NodeStatusWS:
    """ Node status WS client """

    def __init__(self, node, node_config, nodedb, web_config):
        self.node_id = node
        self.node_config = node_config
        self.nodedb = nodedb
        self.ami = None
        self.connections = set()
        self.web_config = web_config
        self.bcast_ws = ws_broadcaster.WebsocketBroadcaster()

    def __exit__(self, exc_type, exc_value, traceback):
        for connection in self.connections:
            log.info("closing an AMI connection: %s", connection.ami_host)
            connection.close()
            self.ami.close()

    # Websocket handler
    async def handler(self, websocket):
        log.debug("entering node_status_handler for %s", websocket.remote_address)
        self.connections.add(websocket)
        try:
            async for message in self.bcast_ws:
                await websocket.send(message)
    
        except asyncio.IncompleteReadError:
            log.debug("Other side went away: %s", websocket.remote_address)
            self.connections.remove(websocket)
    
        except ws_exceptions.ConnectionClosedError:
            log.debug("ConnctionClosed with Error from %s", websocket.remote_address)
            self.connections.remove(websocket)
    
        except ws_exceptions.ConnectionClosedOK:
            log.debug("ConnctionClosed from %s", websocket.remote_address)
            self.connections.remove(websocket)

    # Websocket broadcaster 
    async def broadcast(self):
        log.debug("enter node_status_broadcast()")
        asl_ok = True
        parser = ami_parser.AMIParser(self.ami)
        last_socket_send = time.time()
 
        while True:
            if asl_ok:
                try: 
                    if len(self.connections) > 0:
                        log.debug("Node %s - status_connections: %s", self.node_id, len(self.connections))
                        last_socket_send = time.time()
                        for c_node in self.node_config.node_mon_list:
                            log.debug("broadcasting %s", c_node)
                            await parser.parse_xstat(c_node, self.nodedb.node_database, self.node_config.node_mon_list)
                            await parser.parse_saw_stat(c_node, self.node_config.node_mon_list)
                            message = json.dumps(self.node_config.node_mon_list[c_node])
                            self.bcast_ws.publish(f"{{ \"{c_node}\" : {message} }}")
                    else:
                        log.debug("Node %s: status_connections: 0", self.node_id)
                        now = time.time()
                        if ( now - last_socket_send ) > 60 :
                            log.debug("Node %s: sending keepalive command", self.node_id)
                            await parser.asl_cmd("core show version")
                            last_socket_send = time.time()
                
                    # Sleep for the polling time
                    log.debug("status asyncio.sleep(%d)", self.node_config.pollinterval)
                    await asyncio.sleep(self.node_config.pollinterval)
 
                except ami_conn.AMIException as e:
                    log.warning("ami_conn socket problem for node %s: %s", self.node_id, e)
                    error_msg = { self.node_id : "ERROR", "ERROR" : "Allmon3 is trying to re-establish this connection..." }
                    self.bcast_ws.publish(json.dumps(error_msg))
                    asl_ok = False
                except Exception as e:
                    log.error("ERROR: %s", e)
   
            else:
                await self.ami.close()
                asl_dead = True
                retry_counter = 0
    
                while asl_dead:
                    log.info("node: %s - sleeping for RETRY_INTERVAL of %s", self.node_id, self.node_config.retryinterval)
                    await asyncio.sleep(self.node_config.retryinterval)
                    retry_counter += 1
    
                    if self.node_config.retrycount == -1 or self.node_config.retrycount <= retry_counter:
                        log.info("node: %s - attempting reconnection retry #%d", self.node_id, retry_counter)
    
                        c_stat = await self.ami.asl_create_connection()
                        if c_stat:
                            log.info("node: %s - connection reestablished after %d retries", self.node_id, retry_counter)
                            asl_dead = False
                    else:
                        log.error("node: %s - could not reestablish connection after %d retries - exiting", 
                            self.node_id, retry_counter)
                        raise NodeStatusWSException(f"count not reestablish connection after {retry_counter} retries - exiting")
    
                # re-enable the innter loop processing
                asl_ok = True
    
    # Primary broadcaster
    async def main(self):
        log.debug("enter node_status_main(%s)", self.node_config.node)

        have_conn = False
        while not have_conn:
            try:
                self.ami = ami_conn.AMI(self.node_config.host, self.node_config.port, 
                    self.node_config.user, self.node_config.password)
                await self.ami.asl_create_connection()
                have_conn = True
            except ami_conn.AMIException:
                log.error("No connection for %s:%s on %s due to unreachable AMI - waiting %d seconds",
                    self.node_config.host, self.node_config.port, self.node_config.monport,
                    self.node_config.retryinterval)
                await asyncio.sleep(self.node_config.retryinterval)

        loop = asyncio.get_event_loop()
        self.bcast_ws.set_waiter(asyncio.Future(loop=loop))
        async with serve(
            self.handler,
            host = self.web_config.ws_bind_addr,
            port = self.node_config.monport,
            logger = log,
            ):
            log.info("broadcasting status for %s on port %s", 
                self.node_config.node, self.node_config.monport)
            await self.broadcast()

class NodeStatusWSException(Exception):
    """ exception class """
