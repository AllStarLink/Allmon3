#!/usr/bin/python3
#
# Copyright(C) 2023-2024 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import configparser
import logging
import re
import sys

_BUILD_ID = "1.2.0"
log = logging.getLogger(__name__)

class WebConfigs:
    """ stored configurations for nodes """

    def __init__(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)

        if "CONFIG_HEADER_TITLE" in config["web"]:
            self.header_title = re.sub(r'[\'\"]', '', config["web"]["CONFIG_HEADER_TITLE"])
        else:
            self.header_title = "Allmon3 Monitoring Dashboard"

        if "CONFIG_HEADER_LOGO" in config["web"]:
            self.header_logo = re.sub(r'[\'\"]', '', config["web"]["CONFIG_HEADER_LOGO"])
        else:
            self.header_logo = None

        if "USERS_TABLE_LOCATION" in config["web"]:
            self.user_table = re.sub(r'[\'\"]', '', config["web"]["USERS_TABLE_LOCATION"])
        else:
            self.user_table = "/etc/allmon3/users"

        if "USERS_RESTRICTIONS_LOCATION" in config["web"]:
            self.restrictions_table = re.sub(r'[\'\"]', '', config["web"]["USERS_RESTRICTIONS_LOCATION"])
        else:
            self.restrictions_table = "/etc/allmon3/user-restrictions"


        if "HOME_BUTTON_URL" in config["web"]:
            self.home_loc = re.sub(r'[\'\"]', '', config["web"]["HOME_BUTTON_URL"])
        else:
            self.home_loc = "/allmon3/"

        if "HTTP_PORT" in config["web"]:
            self.http_port = config["web"]["HTTP_PORT"]
        else:
            self.http_port = 16080
        log.info("Allmon3 Master HTTP port is %s", self.http_port)

        if "WS_PORT_START" in config["web"]:
            self.ws_port_start = int(config["web"]["WS_PORT_START"])
        else:
            self.ws_port_start = 16700
        log.info("Allmon3 websockets starting port is %s", self.ws_port_start)

        if "WS_BIND_ADDR" in config["web"]:
            self.ws_bind_addr = str(config["web"]["WS_BIND_ADDR"])
            log.info("Binding services to %s", self.ws_bind_addr)
        else:
            self.ws_bind_addr = None
            log.info("Binding sevices to all addresses")

        try:
            self.commands = dict()
            for k in config["syscmds"]:
                self.commands.update({ k : config["syscmds"][k] })
    
            self.node_overrides = dict()
            for k in config["node-overrides"]:
                self.node_overrides.update({ k : config["node-overrides"][k] })       
    
            self.voter_titles = dict()
            for k in config["voter-titles"]:
                self.voter_titles.update({ int(k) : config["voter-titles"][k].replace("'","") })

            self.menu = str()
        
        except (KeyError, NameError) as e:
            log.error("Missing required web.ini configuration section %s", e)
            sys.exit(1)

        self.per_node_commands = dict()
        for k in config:
            if re.match(r"syscmds\-", k):
                cmds_node = re.sub(r"syscmds\-([0-9]+)", r"\1", k)
                cmds_node_dict = dict()
                for kn in config[k]:
                    cmds_node_dict.update({ kn : config[k][kn] })
                self.per_node_commands.update({ cmds_node : cmds_node_dict })
            
class WebConfigsException(Exception):
    """ Exception for ASLNodeConfig{,s} """
