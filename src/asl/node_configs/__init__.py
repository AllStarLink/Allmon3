#!/usr/bin/python3
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import configparser
import logging
import re

_BUILD_ID = "@@HEAD-DEVELOP@@"
log = logging.getLogger(__name__)

class NodeConfigs:
    """ stored configurations for nodes """

    node_list = dict()

    def __init__(self, config_file, filter_set = None):
        config_full_dict = configparser.ConfigParser()
        config_full_dict.read(config_file)
        
        for k_node in dict(config_full_dict):
            if k_node != "DEFAULT" and not "colocated_on" in config_full_dict[k_node]:
                node_config = AllmonNodeConfig(k_node, dict(config_full_dict[k_node]))
                self.node_list.update( { k_node : node_config } )

class AllmonNodeConfig:
    """ a signle node's configuration """
    
    node = int()
    host = str()
    port = int()
    user = str()
    password = str()
    monport = int()
    cmdport = int()
    vmonport = int()
    pollinterval = float(1)
    vpollinterval = float(1)
    retryinterval = int(15)
    retrycount = -1
    votertitle = str()
    nodes_on_host = set()
    node_mon_list = dict()

    def __init__(self, node, config_dict):
        self.node = int(node) 

        if "colocated_on" in config_dict:
            raise ASLNodeConfigException("ASLNodeConfig was called on a colocated_on node")
    
        if not "host" in config_dict:
            raise ASLNodeConfigException("Missing required attribute host= for %s" % (self.node))
        self.host = config_dict["host"]
    
        if not "user" in config_dict:
            raise ASLNodeConfigException("Missing required attribute user= for %s" % (self.node))
        self.user = config_dict["user"]
    
        if not "pass" in config_dict:
            raise ASLNodeConfigException("Missing required attribute pass= for %s" % (self.node))
        self.passwd = config_dict["pass"]
    
        if not "port" in config_dict:
            log.debug("No port= attribute specified, using default 5038")
            self.port = 5038
        else:
            self.port = int(config_dict["port"])
    
        if "pollinterval" in config_dict:
            self.pollinterval = float(config_dict["pollinterval"])
               
        if "vpollinterval" in config_dict:
            self.vpollinterval = float(config_dict["vpollinterval"])
    
        if "retryinterval" in config_dict:
            self.retryinterval = int(config_dict["retryinterval"])
    
        if "retrycount" in config_dict:
            self.retrycount = int(config_dict["retrycount"])
    
        if not "cmdport" in config_dict:
            raise ASLNodeConfigException("Missing required attribute cmdport= for %s" % (self.node))
        self.cmdport = int(config_dict["cmdport"])
    
        if not "monport" in config_dict:
            raise ASLNodeConfigException("Missing required attribute monport= for %s" % (self.node))
        self.monport = int(config_dict["monport"])
    
        if "vmonport" in config_dict:
            self.vmonport = int(config_dict["vmonport"])
        else:
            log.info("no vmonport specified - disabling votermon on %s", node)
    
        if "votertitle" in config_dict:
            self.votertitle = config_dict["vmonport"]
        else:
            self.votertitle = f"{node} Voter"
    
        if "multinodes" in config_dict:
            for mn in re.split(r',', config_dict["multinodes"]):
                self.nodes_on_host.add(int(mn))
                self.node_mon_list.update({ int(mn): {
                    "ME" : int(mn) , "DESC" : None , "RXKEYED" : False, "TXKEYED" : False ,
                    "TXEKEYED" : False, "CONNKEYED" : False, "CONNKEYEDNODE" : None , "CONNS" : None }})
        else:
            self.nodes_on_host.add(node)
            self.node_mon_list.update({ node : {
                    "ME" : self.node , "DESC" : None , "RXKEYED" : False, "TXKEYED" : False ,
                    "TXEKEYED" : False, "CONNKEYED" : False, "CONNKEYEDNODE" : None , "CONNS" : None }})
    

class ASLNodeConfigException(Exception):
    """ Exception for ASLNodeConfig{,s} """
