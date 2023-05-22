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
import websockets
from .. import ami_conn, ami_parser, node_configs, node_db, ws_broadcaster


__BUILD_ID = "0.10.0"
log = logging.getLogger(__name__)

class NodeStatusWS:
    """ Node status WS client """

    def __init__(self, node, node_config, nodedb):
        self.node_id = node
        self.node_config = node_config
        self.nodedb = nodedb
        self.ami = None
        self.connections = set()
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
    
        except asyncio.exceptions.IncompleteReadError:
            log.info("Other side went away: %s", websocket.remote_address)
    
        except websockets.exceptions.ConnectionClosedError:
            log.info("ConnctionClosed with Error from %s", websocket.remote_address)
            self.connections.remove(websocket)
    
        except websockets.exceptions.ConnectionClosedOK:
            log.info("ConnctionClosed from %s", websocket.remote_address)
            self.connections.remove(websocket)
    
    async def broadcast(self):
        log.debug("enter node_status_broadcast()")
        asl_ok = True
        parser = ami_parser.AMIParser(self.ami)
    
        while True:
            if asl_ok:
                if len(self.connections) > 0:
                    log.debug("Node %s - status_connections: %s", self.node_id, len(self.connections))
                    try:
                        for c_node in self.node_config.node_mon_list:
                            log.debug("broadcasting %s", c_node)
                            parser.parse_xstat(c_node, self.nodedb.node_database, self.node_config.node_mon_list)
                            parser.parse_saw_stat(c_node, self.node_config.node_mon_list)
                            message = json.dumps(self.node_config.node_mon_list[c_node])
                            self.bcast_ws.publish(f"{{ \"{c_node}\" : {message} }}")
    
                    except BrokenPipeError as e:
                        log.error("received BrokenPipeError; trying to reconnect")
                        asl_ok = False
                    except socket.timeout as e:
                        log.error("received socket.timeout; trying to reconnect")
                        asl_ok = False
                    except ConnectionResetError as e:
                        log.error("received ConnectionResetError; trying to reconnect")
                        asl_ok = False
                    except Exception as e:
                        log.error(e)
                        raise e
    
                else:
                    log.debug("Node %s: status_connections: 0", self.node_id)
    
                # Sleep for the polling time
                log.debug("status asyncio.sleep(%d)", self.node_config.pollinterval)
                await asyncio.sleep(self.node_config.pollinterval)
    
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
                        raise NodeStatusWSException(f"count not reestablish connection after {retry_counter} retries - exiting")
    
                # re-enable the innter loop processing
                asl_ok = True
    
    # Primary broadcaster
    async def main(self):
        log.debug("enter node_status_main(%s)", self.node_config.node)

        try:
            loop = asyncio.get_event_loop()
            self.bcast_ws.set_waiter(asyncio.Future(loop=loop))
            self.ami = ami_conn.AMI(self.node_config.host, self.node_config.port, 
                self.node_config.user, self.node_config.password)
            async with websockets.serve(
                self.handler,
                host = None,
                port = self.node_config.monport,
                logger = log,
                compression = None,
                ping_timeout = None
                ):
                log.info("broadcasting status for %s on port %s", 
                    self.node_config.node, self.node_config.monport)
                await self.broadcast()

        except ami_conn.AMIException:
            log.error("Terminating asyncio worker for %s:%s on %s due to unreachable AMI",
                self.node_config.host, self.node_config.port, self.node_config.monport)
            log.error("AMI instances must be available at start. See --nodes or remove the config")
            return None

class NodeStatusWSException(Exception):
    """ exception class """
