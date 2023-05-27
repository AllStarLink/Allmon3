#!/usr/bin/python3
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import configparser
import logging
import re
import sys

_BUILD_ID = "@@HEAD-DEVELOP@@"
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

        if "HOME_BUTTON_URL" in config["web"]:
            self.home_loc = re.sub(r'[\'\"]', '', config["web"]["HOME_BUTTON_URL"])
        else:
            self.home_loc = "/allmon3/"

        if "HTTP_PORT" in config["web"]:
            self.http_port = config["web"]["HTTP_PORT"]
        else:
            self.http_port = 16080

        if "WS_PORT_START" in config["web"]:
            self.ws_port_start = int(config["web"]["WS_PORT_START"])
        else:
            self.ws_port_start = 16700

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
            
class WebConfigsException(Exception):
    """ Exception for ASLNodeConfig{,s} """
