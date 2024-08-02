#!/usr/bin/python3
# almon3.py - Monitor ASL Asterisk server for events
#
# Copyright(C) 2023-2024 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import asyncio
import logging
import re
import socket
import uuid

_BUILD_ID = "1.3.1"
log = logging.getLogger(__name__)

class AMI:
    """ handling an Asterisk AMI connection """

    # Local Variables
    __rern = re.compile(r'\r\n', re.MULTILINE)

    # Init
    def __init__(self, hostname, port, user, password):
        self.ami_host = hostname
        self.ami_port = port
        self.ami_user = user
        self.ami_pass = password
        self.socket = None
        self.ami_reader = None
        self.ami_writer = None
    
    async def asl_create_connection(self):
        log.debug("asl_create_connection()")
        try:
            log.debug("connect() using %s:%s", self.ami_host, self.ami_port)
            self.ami_reader, self.ami_writer = await asyncio.open_connection(self.ami_host, self.ami_port)
    
            # Check this connected to an Asterisk Call Manager (ACM)
            part = await self.ami_reader.read(1024)
            part = part.decode()
            log.debug("AIM version: %s", self.__rern.sub("",part))
    
            if not re.match("^Asterisk Call Manager", part):
                log.error("Connection to %s:%d does not appear to be an Asterisk Call Manager", self.ami_host, self.ami_port)
                self.ami_writer.close()
                await self.ami_writer.wait_closed()
                raise AMIException(f"Connection to {self.ami_host}:{self.ami_port} does not appear to be an Asterisk Call Manager")
        
            # Logon to the ACM
            logon = "ACTION: LOGIN\r\nUSERNAME: %s\r\nSECRET: %s\r\nEVENTS: 0\r\n" % ( self.ami_user, self.ami_pass )
    
            logon_response = await self.asl_cmd_response(logon)
            log.debug(self.__rern.sub(" ",logon_response))
            lp = re.compile('Response: Success\r\n', re.MULTILINE)
            logon_success = lp.match(logon_response)
            if not logon_success:
                lr = self.__rern.sub("  ", logon_response)
                log.error("Logon failure msg=(%s)", lr)
                self.ami_writer.close()
                await self.ami_writer.wait_closed()
                raise AMIException(f"Logon failure msg={lr}")
    
            log.debug("leaving asl_create_connection()")
    
        except socket.error as error:
            log.warning("connection failed to %s:%s: %s", self.ami_host, self.ami_port, error)
            return False

        except TypeError as e:
            log.warning("failed connection on connect(): %s", e)
            return False

        return True
    
    # Generic construct for sending ASL Manager commands and reading responses
    async def asl_cmd_response(self, cmd):
        log.debug("enter asl_cmd_response()")
        try:
            aid = uuid.uuid4()
            cmd += " ActionID: %s\r\n\r\n" % aid
            if not cmd is None:
                log.debug("command >> %s", self.__rern.sub(" ", cmd))
                self.ami_writer.write(cmd.encode())
                await self.ami_writer.drain()
            
            cont_recv = True
            resp = ""
            while cont_recv:        
                part = await self.ami_reader.read(1024)
                if part == b'':
                    log.debug("asl_cmd_response() socket went away on the far side")
                    raise BrokenPipeError("other side went away")
                resp += part.decode()
                if resp[-4:] == "\r\n\r\n":
                    cont_recv = False
    
            log.debug("response >> %s", self.__rern.sub("  ", resp))
            return resp
    
        except TimeoutError as e:
            log.warning("asl_cmd_response() TimeoutError")
            raise AMIException("socket timeout") from e
        except BrokenPipeError as e:
            log.warning("asl_cmd_response() BrokenPipeError")
            raise AMIException("socket broken pipe") from e
        except socket.timeout as e:
            log.warning("asl_cmd_response() socket.timeout")
            raise AMIException("socket timeout") from e
        except ConnectionResetError as e:
            log.warning("asl_cmd_response() ConnectionResetError")
            raise AMIException("socket connection reset") from e
        except OSError as e:
            log.warning("asl_cmd_response() OSError: %s", e)
            raise AMIException(f"socket os error: {e}") from e
        except Exception as e:
            log.error("asl_cmd_response() Exception: %s", e.__class__)
            log.error("asl_cmd_response() Message: %s", e)
            raise AMIException("unhandled error") from e

        log.debug("exit asl_cmd_response()")
    
    # (try) to logout of ASL Manager neatly
    async def __asl_logout(self):    
        try:
            self.ami_writer.write("ACTION: Logoff\r\n\r\n".encode())
            await self.ami_writer.drain()
        except Exception as e:
            log.warning(e)

    async def close(self):
        try:
            await self.__asl_logout()
            self.ami_writer.close()
            await self.ami_writer.wait_closed()

        except Exception as e:
            log.warning(e)

class AMIException(Exception):
    """ Exceptions for the AMI class """
