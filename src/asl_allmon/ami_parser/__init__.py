#!/usr/bin/python3
#
# Copyright(C) 2023-2024 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import asyncio
import base64
from datetime import datetime
from itertools import cycle
import logging
import re

_BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

## Command Execution Portions
##

# Wrapper for asl_cmd_response to handle ACTION:COMMAND
class AMIParser:
    """ parser for messages to/from Asterisk AMI for ASL """

    def __init__(self, ami_conn):
        self.__ami_conn = ami_conn

    def set_ami_conn(self, ami_conn):
        log.debug("enter set_ami_conn()")
        self.__ami_conn = ami_conn

    async def asl_cmd(self, cmdstr):
        log.debug("enter asl_cmd()")
        
        try:
            cmd = f"ACTION: COMMAND\r\nCOMMAND: {cmdstr}\r\n"
            c_response = await self.__ami_conn.asl_cmd_response(cmd)
    
            # For Asterisk 20/ASL3 look for Output:
            if  re.match(r"^Response\:\s+Error\s", c_response):
                output = re.search(r"^.*Output:\s+(.*)", c_response, re.MULTILINE)
                if output:
                    return "ERR: {}".format(output.group(1))
    
            # For Asterisk 20/ASL3 we look for Output: lines
            if  re.match(r"^Response\:\s+Success\s", c_response):
                output = re.split("\r\n", c_response)
                r = "OK:\r\n"
                for l in output:
                    if re.match(r"^Output:\s", l):
                        output = re.search(r"^Output:\s(.*)$", l)
                        log.debug(output.group(1))
                        r += output.group(1) + "\r\n"
                return r
    
            # For Asterisk 1.4/Classic ASL we have to assume the ordering
            # and there's no valid command check
            if  re.match(r"^Response\:\s+Follows\s", c_response):
                cmd_output = re.sub(r"Response:\s+Follows\s+Privilege:\s+Command\s+", "", c_response)
                log.debug(cmd_output)
                if not re.match(r"No such command", cmd_output) and not re.match(r"Unknown action name", cmd_output):
                    return f"OK:\r\n{cmd_output}"
                
                return f"ERR:\r\n{cmd_output}"
    
            return "ERR: command output responded with something I didn't understand"
    
        except Exception as e:
            log.error("asl_cmd() exception %s", e.__class__)
            log.error("asl_cmd() message %s", e.__class__)
            raise e    
    
    ##
    ## Status Broadcasting Functions
    ##
    
    # Parse the (String) response from a SawStat command
    async def parse_saw_stat(self, curr_node, node_mon_list):
        log.debug("enter parse_saw_stat(%s)", curr_node)
        
        # Clear the CONNKEYED* status
        node_mon_list[curr_node].update( { "CONNKEYED" : False } )
        node_mon_list[curr_node].update( { "CONNKEYEDNODE" : False } )

        sawstat_cmd = f"ACTION: RptStatus\r\nCOMMAND: SawStat\r\nNODE: {curr_node}\r\n"
        response = await self.__ami_conn.asl_cmd_response(sawstat_cmd)
        # Process the SawStat message
        ra = re.split(r'[\n\r]+', response)
        for l in ra:
            if re.match("^Conn", l):
                ce = re.split(r"\s+", l)
                # Conn: NODE PTT SEC_SINCE_KEY SEC_SINCE_UNKEY
                if ce[1] in node_mon_list[curr_node]["CONNS"]:
                    node_mon_list[curr_node]["CONNS"][ce[1]].update( { "PTT" : ce[2] , "SSK" : ce[3] , "SSU" : ce[4] } )                
                    if int(ce[2]) == 1:
                        node_mon_list[curr_node].update( { "CONNKEYED" : True } )
                        node_mon_list[curr_node].update( { "CONNKEYEDNODE" : ce[1] } )
        log.debug("exiting parse_saw_stat(%s)", curr_node)
    
    # Query/Parse Echolink Node Info
    async def get_echolink_name(self, echolink_id):
        log.debug("enter get_echolink_name(%s)", echolink_id)
        elnodecmd = "ACTION: COMMAND\r\nCOMMAND: echolink dbget nodename %s\r\n" % (echolink_id)
        el_info = await self.__ami_conn.asl_cmd_response(elnodecmd)
        ra = re.split(r'[\n\r]+', el_info)
        for l in ra:
            if re.match(r"^[0-9]+\|", l):
                ell = re.split(r'\|', l)
                log.debug("exiting get_echolink_name(%s)", echolink_id)
                return "%s - Echolink" % (ell[1])
        log.debug("Invalid response about echolink - exiting get_echolink_name")
        return "No Database Information"
    
    # Parse the (String) response from XStat command
    async def parse_xstat(self, curr_node, node_database, node_mon_list):
        log.debug("entering parse_xstat(%s)", curr_node)
        conn_count = 0
        rens = re.compile(r'\s', re.MULTILINE)
        renol = re.compile(r'LinkedNodes:', re.MULTILINE)
    
        # {
        #    NODE : {
        #       IP : str            (ip adderss)
        #       DIR : str           (direction of link)
        #       CTIME: str          (connection time)
        #       CSTATE: str         (connection state)
        #       PTT : TRUE|FALSE    (current PTT state)
        #       SSK : int           (sec since key)
        #       SSU : int           (sec since unkey)
        #       MODE : str          (mode)
        #   } , 
        #    NODE { ... } ,
        #    ... 
        # }
        node_conns = {}

        xstat_cmd = f"ACTION: RptStatus\r\nCOMMAND: XStat\r\nNODE: {curr_node}\r\n"
        xstat = await self.__ami_conn.asl_cmd_response(xstat_cmd)
        ra = re.split(r'[\n\r]+', xstat) 
        for l in ra:
            if re.match("^Conn", l):
                ce = re.split(r"\s+", l)
                node_conns.update( { ce[1] : {} } )
                # For each Conn: line, a node starting with 3 and seven digits long is an echolink    
                # node which is missing an IP entry. Treat everything else normally
                if re.match(r'^3[0-9]{6}$', ce[1]):
                    node_conns[ce[1]].update( { "IP" : None , "DIR" : ce[3] , "CTIME" : ce[4] ,
                        "CSTATE" : ce[5] , "PTT" : False, "SSK" : -1, "SSU" : -1, "MODE" : "Echolink"} )
                    ename = await self.get_echolink_name(ce[1][-6:])
                    node_conns[ce[1]]["DESC"] = ename
                else:
                    node_conns[ce[1]].update( { "IP" : ce[2] , "DIR" : ce[4] , "CTIME" : ce[5] ,
                        "CSTATE" : ce[6] , "PTT" : False, "SSK" : -1, "SSU" : -1, "MODE" : "Local Monitor" } )
                    if ce[1] in node_database:
                        node_conns[ce[1]]["DESC"] = "{0} {1} {2}".format(node_database[ce[1]]['CALL'], 
                            node_database[ce[1]]['DESC'], node_database[ce[1]]['LOC'])
                    elif re.match(r'^.*\-P$', ce[1]):
                        node_conns[ce[1]].update( { "DESC" : "Allstar Telephone Portal User",
                            "MODE" : "Transceive" } )
                    elif re.match(r'[A-Za-z]', ce[1]):
                        node_conns[ce[1]].update( { "DESC" : "Direct Client" } )
                    else:
                        node_conns[ce[1]]["DESC"] = "Private or Unavailable"
                    
                conn_count += 1
            elif re.match(r"^LinkedNodes:", l):
                for link in l.split(","):
                    link = rens.sub("", link)            
                    link = renol.sub("", link)
                    if re.match(r"^[A-Z]\S+", link):
                        ns = re.search(r'^([A-Z])(\S+)', link)
                        if ns.group(2) in node_conns:
                            if ns.group(1) == "T":
                                node_conns[ns.group(2)].update( { "MODE" : "Transceive" } )
                            elif ns.group(1) == "R":
                                node_conns[ns.group(2)].update( { "MODE" : "Monitor" } )
                            elif ns.group(1) == "C":
                                node_conns[ns.group(2)].update( { "MODE" : "Connecting" } )
                            else:
                                node_conns[ns.group(2)].update( { "MODE" : "Unknown" } )
            elif re.match(r"^Var:\sRPT_TXKEYED=1", l):
                node_mon_list[curr_node].update( { "TXKEYED" : True } )
            elif re.match(r"^Var:\sRPT_TXEKEYED=1", l):
                node_mon_list[curr_node].update( { "TXEKEYED" : True } )
            elif re.match(r"^Var:\sRPT_RXKEYED=1", l):
                node_mon_list[curr_node].update( { "RXKEYED" : True } )
            elif re.match(r"^Var:\sRPT_TXKEYED=0", l):
                node_mon_list[curr_node].update( { "TXKEYED" : False } )
            elif re.match(r"^Var:\sRPT_TXEKEYED=0", l):
                node_mon_list[curr_node].update( { "TXEKEYED" : False } )
            elif re.match(r"^Var:\sRPT_RXKEYED=0", l):
                node_mon_list[curr_node].update( { "RXKEYED" : False } )
    
        if conn_count == 0:
            log.debug("no nodes connected")
        else:
            log.debug("processed %s connections", conn_count)
    
        node_mon_list[curr_node]["CONNS"] = node_conns

        uptimes = await self.get_node_uptime()
        node_mon_list[curr_node]["UPTIME"] = uptimes[0]
        node_mon_list[curr_node]["RELOADTIME"] = uptimes[1]

        log.debug("exiting parse_xstat(%s)", curr_node)
   
    async def parse_voter_data(self, curr_node):
        log.debug("entering parse_voter_data()")
        # voters = { VOTED : None , VOTERS : { clientid : RSSI , .... } }
        voters = { "VOTED" : None , "VOTERS" : {} }
        curr_client = 0

        voterstatus_cmd = f"ACTION: VoterStatus\r\nNODE: {curr_node}\r\n"
        response = await self.__ami_conn.asl_cmd_response(voterstatus_cmd)    

        lines = re.split(r'[\n\r]+', response)
        for line in lines:
            if re.match(r'^Client', line):
                client = re.split(r":\s", line)
                curr_client = client[1]
                voters["VOTERS"][curr_client] = 0
            elif re.match(r'^RSSI', line):
                rssi = re.split(r":\s", line)
                voters["VOTERS"][curr_client] = int(rssi[1])
            elif re.match(r'Voted', line):
                voted = re.split(r":\s", line)
                voters["VOTED"] = voted[1]
    
        voter_html = ""
        for n, r in voters["VOTERS"].items():
            rssipct = 0
            if r == 255:
                rssipct = 100
            else:
                rssipct = int(r) * .35 + 10
    
            barcolor = "primary"
            if n == voters["VOTED"]:
                barcolor = "success"
            if re.match(r"\s[Mm]ix", n):
                barcolor = "info"
    
            voter_html += "<div class=\"row justify-content-md-center\">"
            voter_html += "  <div class=\"col-4 col-md-2 text-end\">"
            voter_html += "    <b>{}</b>".format(n)
            voter_html += "  </div>"
            voter_html += "  <div class=\"col-8 col-md-10\">"
            voter_html += "    <div class=\"progress\" role=\"progressbar\" aria-valuenow=\"{}\"".format(rssipct)
            voter_html += "    aria-valuemin=\"0\" aria-valuemax=\"100\">"
            voter_html += "      <div class=\"progress-bar progress-bar-striped bg-{}\" style=\"width: {}%\">{}</div>".format(barcolor, rssipct, r)
            voter_html += "    </div>"
            voter_html += "  </div>"
            voter_html += "</div>"
    
    
        voter_html += "<div class=\"row d-flex align-items-center\">"
        voter_html += "  <div class=\"col-2\">&nbsp</div>"
        voter_html += "  <div class=\"col-8\">"
        voter_html += "    Last Update: {}".format(datetime.now())
        voter_html += "  </div>"
        log.debug("exiting parse_voter_data()")
    
        return voter_html

    async def get_node_uptime(self):
        log.debug("enter get_node_uptime()")
        sys_uptime = -1
        last_reload = -1

        try:
            uptimecmd = "core show uptime seconds"
            uptime_info = await self.asl_cmd(uptimecmd)
            ra = re.split(r'[\n\r]+', uptime_info)
            for l in ra:
                if re.match(r"^System uptime\:\s+", l):
                    t = re.split(r"\s+", l)
                    sys_uptime = int(t[2])
                    log.debug("system uptime seconds: %d", sys_uptime)
                if re.match(r"^Last reload\:\s+", l):
                    t = re.split(r"\s+", l)
                    last_reload = int(t[2])
                    log.debug("last reload seconds: %d", last_reload)

            return (sys_uptime, last_reload)
    
        except Exception as e:
            log.error(e)
 
# To prevent casual interception/hacking, the cmd messages
# are xor'd with the node admin key. The messages are base64-encoded.
# Note: this is _not_ cryptographically secure... if you're concerned
# about that you shouldn't be doing whatever it is you're doing
# with this program.
def decrypt_msg(data, key):
    log.debug("entering decrypt_msg")
    log.debug("msg: %s", data)
    data_bytes = data.encode("UTF-8")
    msg_bytes = base64.b64decode(data_bytes)
    msg_x = msg_bytes.decode("UTF-8")
    msg = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in zip(msg_x, cycle(key)))
    log.debug("msg: %s", msg)
    return msg
