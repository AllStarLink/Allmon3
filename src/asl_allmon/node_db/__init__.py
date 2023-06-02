#!/usr/bin/python3
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import asyncio
import logging
import re
import time
import urllib.request
from .. import node_configs

_BUILD_ID = "0.10.2"
log = logging.getLogger(__name__)

class ASLNodeDB:
    """ AllStarLink Node Dadabase """
    
    __url = "http://allmondb.allstarlink.org/"

    def __init__(self):
        self.node_database = dict()
        self.get_allmon_db()
        
    # Read and load in the ASL Database
    def get_allmon_db(self):
        log.debug("entering get_allmon_db()")
        try:
            req = urllib.request.Request(self.__url, data=None, headers={ "User-Agent" : "Mozilla/5.0" })
            log.info("Retrieving database from %s", self.__url)
            start_time = time.time()
            with urllib.request.urlopen(req) as response:
                dbf = response.read().decode("UTF-8")
        except Exception as e:
            raise e
        nodedb = re.split(r"\n", dbf)
    
        for ni in nodedb:
            r = re.split(r"\|", ni)
            if len(r) == 4:
                self.node_database.update( { str(r[0]) : {} } )
                self.node_database[str(r[0])].update( { "CALL" : r[1] , "DESC" : r[2] , "LOC" : r[3] } )
        elapsed_time = time.time() - start_time
        log.info("Updated node database in {0:.2f} seconds".format(elapsed_time))
        log.debug("exiting getAllMonDB()")
    
    def set_my_info(self, node_conf):
        log.debug("entering set_my_info()")
        for n in node_conf.node_mon_list:
            if str(n) in self.node_database:
                node_conf.node_mon_list[n]["DESC"] = "{0} {1} {2}".format(self.node_database[str(n)]['CALL'],
                self.node_database[str(n)]['DESC'], self.node_database[str(n)]['LOC'])
            else:
                node_conf.node_mon_list[n]["DESC"] = "Unavailable"
        log.debug("exiting set_my_info()")

    async def db_updater(self, node_configuration):
        while True:
            await asyncio.sleep(15*60)
            self.get_allmon_db()
            for n, c in node_configuration.nodes.items():
                self.set_my_info(c)
