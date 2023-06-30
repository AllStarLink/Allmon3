#!/usr/bin/python3
# almon3.py - Monitor ASL Asterisk server for events
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import logging
import re
import socket
import uuid

_BUILD_ID = "0.11.2"
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
        
        if not self.asl_create_connection():
            raise AMIException(f"could not initialize a connection to {hostname}:{port}")

    def asl_create_connection(self):
        log.debug("asl_create_connection()")
        try:
            log.debug("connect() using %s:%s", self.ami_host, self.ami_port)
            self.socket = socket.create_connection((self.ami_host, self.ami_port), timeout=5)
    
            # Check this connected to an Asterisk Call Manager (ACM)
            part = self.socket.recv(1024).decode("UTF-8")
            log.debug("AIM version: %s", self.__rern.sub("",part))
    
            if not re.match("^Asterisk Call Manager", part):
                log.error("Connection to %s:%d does not appear to be an Asterisk Call Manager", self.ami_host, self.ami_port)
                self.socket.close()
                raise AMIException(f"Connection to {self.ami_host}:{self.ami_port} does not appear to be an Asterisk Call Manager")
        
            # Logon to the ACM
            logon = "ACTION: LOGIN\r\nUSERNAME: %s\r\nSECRET: %s\r\nEVENTS: 0\r\n" % ( self.ami_user, self.ami_pass )
    
            logon_response = self.asl_cmd_response(logon)
            log.debug(self.__rern.sub(" ",logon_response))
            lp = re.compile('Response: Success\r\n', re.MULTILINE)
            logon_success = lp.match(logon_response)
            if not logon_success:
                lr = self.__rern.sub("  ", logon_response)
                log.error("Logon failure msg=(%s)", lr)
                self.socket.close()
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
    def asl_cmd_response(self, cmd):
        log.debug("enter asl_cmd_response()")
        try:
            aid = uuid.uuid4()
            cmd += " ActionID: %s\r\n\r\n" % aid
            self.socket.settimeout(5)
            if not cmd is None:
                log.debug("command >> %s", self.__rern.sub(" ", cmd))
                self.socket.sendall(str.encode(cmd))
            
            cont_recv = True
            resp = ""
            while cont_recv:        
                part = self.socket.recv(1024)
                if part == b'':
                    log.debug("asl_cmd_response() socket went away on the far side")
                    raise BrokenPipeError("other side went away")
                resp += part.decode("UTF-8")
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
    def __asl_logout(self):    
        try:
            self.socket.sendall(str.encode("ACTION: Logoff\r\n\r\n"))
        except Exception as e:
            log.warning(e)

    def close(self):
        try:
            self.__asl_logout()
            self.socket.close()
        except Exception as e:
            log.warning(e)

class AMIException(Exception):
    """ Exceptions for the AMI class """
