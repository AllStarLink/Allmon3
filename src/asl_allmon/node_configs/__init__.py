#!/usr/bin/python3
#
# Copyright(C) 2023-2024 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import configparser
import logging
import pprint
import re

_BUILD_ID = "1.3.0"
log = logging.getLogger(__name__)

class NodeConfigs:
    """ stored configurations for nodes """

    def __init__(self, config_file, filter_list = None):
        config_full = configparser.ConfigParser()
        config_full.read(config_file)
        self.all_nodes = list()
        self.nodes = dict()
        self.colo_nodes = dict()

        if filter_list is None:
            filter_list = []
            for k in config_full:
                if k != "DEFAULT":
                    filter_list.append(k)

        for k_node in config_full:
            if k_node != "DEFAULT" and not "colocated_on" in config_full[k_node] and k_node in filter_list:
                k_node = int(k_node)
                self.all_nodes.append(k_node)
                node_config = AllmonNodeConfig(k_node, config_full[str(k_node)])
                self.nodes.update({ k_node : node_config })
                log.debug("nodes_on_host: %d", len(node_config.nodes_on_host))
                if len(node_config.nodes_on_host) > 1:
                    for m_node in node_config.nodes_on_host:
                        m_node = int(m_node)
                        if m_node != k_node:
                            self.colo_nodes.update({ m_node : k_node })
                            self.all_nodes.append(m_node)

class AllmonNodeConfig:
    """ a signle node's configuration """
    
        
    def __init__(self, node, config):

        # create instance vars for all optional items
        self.node = int(node) 
        self.host = str()
        self.port = int()
        self.user = str()
        self.password = str()
        self.monport = int(0)
        self.cmdport = int(0)
        self.voterports = dict()
        self.pollinterval = float(1)
        self.vpollinterval = float(1)
        self.retryinterval = int(15)
        self.retrycount = -1
        self.votertitle = str()
        self.nodes_on_host = set()
        self.node_mon_list = dict()

        if "colocated_on" in config:
            raise ASLNodeConfigException("colocated_on no longer supported; remove from configuration")
    
        if not "host" in config:
            raise ASLNodeConfigException(f"Missing required attribute host= for {self.node}")
        self.host = config["host"]
    
        if not "user" in config:
            raise ASLNodeConfigException(f"Missing required attribute user= for {self.node}")
        self.user = config["user"]
    
        if not "pass" in config:
            raise ASLNodeConfigException(f"Missing required attribute pass= for {self.node}")
        self.password = config["pass"]
    
        if not "port" in config:
            self.port = 5038
        else:
            self.port = int(config["port"])
    
        if "pollinterval" in config:
            self.pollinterval = float(config["pollinterval"])
               
        if "vpollinterval" in config:
            self.vpollinterval = float(config["vpollinterval"])
    
        if "retryinterval" in config:
            self.retryinterval = int(config["retryinterval"])
    
        if "retrycount" in config:
            self.retrycount = int(config["retrycount"])
    
        if "voters" in config:
            self.voter = True
            for v in re.split(r',', config["voters"]):
                self.voterports.update({ int(v) : -1 }) 
        else:
            self.voter = False
    
        if "multinodes" in config:
            for mn in re.split(r',', config["multinodes"]):
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
