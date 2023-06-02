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

_BUILD_ID = "0.10.2"
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
        self.socket = self.asl_create_connection_fail()

    ## Use this creator as part of a retry interval
    def asl_create_connection_nofail(self):
        return self.asl_create_connection(False)
    
    ## Use this creator to fail immediately on any
    ## network-level connect failure
    def asl_create_connection_fail(self):
        return self.asl_create_connection(True)
    
    ## If failhard=True then sys.exit() is called on network-level issues
    def asl_create_connection(self, failhard):
        log.debug("asl_create_connection(failhard=%s)", failhard)
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
            log.error("connection failed to %s:%s: %s", self.ami_host, self.ami_port, error)
            if failhard:
                raise AMIException("connection failed to {self.ami_host}:{self.ami_port}: {error}") from error

        except TypeError as e:
            log.error("failed connection on connect(): %s", e)
            if failhard:
                raise AMIException("connection failed") from e

        return self.socket
    
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
            log.error("asl_cmd_response() TimeoutError")
            raise e
        except BrokenPipeError as e:
            log.error("asl_cmd_response() BrokenPipeError")
            raise e
        except socket.timeout as e:
            log.error("asl_cmd_response() socket.timeout")
            raise e
        except ConnectionResetError as e:
            log.error("asl_cmd_response() ConnectionResetError")
            raise e
        except Exception as e:
            log.error("asl_cmd_response() Exception: %s", e.__class__)
            log.error("asl_cmd_response() Message: %s", e)
            raise e

        log.debug("exit asl_cmd_response()")
    
    # (try) to logout of ASL Manager neatly
    def __asl_logout(self):    
        try:
            self.socket.sendall(str.encode("ACTION: Logoff\r\n\r\n"))
        except Exception as e:
            log.error(e)

    def close(self):
        try:
            self.__asl_logout()
            self.socket.close()
        except Exception as e:
            log.error(e)

class AMIException(Exception):
    """ Exceptions for the AMI class """
