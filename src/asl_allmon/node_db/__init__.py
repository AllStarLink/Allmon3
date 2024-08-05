#!/usr/bin/python3
#
# Copyright(C) 2023-2024 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import aiohttp
import asyncio
import logging
import re
import time
import urllib.request
from .. import node_configs

_BUILD_ID = "1.3.2"
log = logging.getLogger(__name__)

class ASLNodeDB:
    """ AllStarLink Node Dadabase """
    
    __url = "https://allmondb.allstarlink.org/"

    def __init__(self):
        self.node_database = dict()
        
    # Read and load in the ASL Database
    async def get_allmon_db(self):
        log.debug("entering get_allmon_db()")
        retries = 0
        db_text = ""
        while retries < 5:
            try:
                log.info("Retrieving database from %s", self.__url)
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.__url) as resp:
                        db_text = await resp.text()
                retries = 255
            except aiohttp.ClientConnectorError as e:
                log.error(e)
            except Exception as e:
                log.error("Failed to retrieve database with error: %s", e)

            if retries != 255:
                retries += 1
                log.info("Will retry %d/5 in 5m", retries)
                await asyncio.sleep(300)

        if retries != 255:
            raise ASLNodeDBException("retrieval of database failed after 5 attempts")

        try:        
            nodedb = re.split(r"\n", db_text) 
    
            for ni in nodedb:
                r = re.split(r"\|", ni)
                if len(r) == 4:
                    self.node_database.update( { str(r[0]) : {} } )
                    self.node_database[str(r[0])].update( { "CALL" : r[1] , "DESC" : r[2] , "LOC" : r[3] } )
            elapsed_time = time.time() - start_time
        
            if len(self.node_database) < 2:
                log.error("Node file successfully retrieved but is empty or contains garbage")
            log.info("Updated node database in {0:.2f} seconds".format(elapsed_time))

        except Exception as e:
            log.error("Error processing nodedb after retrival: %s ", e)
            raise ASLNodeDBException(e)

        log.debug("exiting getAllMonDB()")
    
    def set_my_info(self, node_conf):
        log.debug("entering set_my_info()")
        for n in node_conf.node_mon_list:
            if str(n) in self.node_database:
                node_conf.node_mon_list[n]["DESC"] = "{0} {1} {2}".format(self.node_database[str(n)]['CALL'],
                self.node_database[str(n)]['DESC'], self.node_database[str(n)]['LOC'])
            else:
                if int(n) < 2000:
                    node_conf.node_mon_list[n]["DESC"] = "Private"
                else:
                    node_conf.node_mon_list[n]["DESC"] = "Unavailable"
        log.debug("exiting set_my_info()")

    def add_node_overrides(self, web_node_overrides):
        log.debug("entering add_node_overrides()")
        for k, v in web_node_overrides.items():
            if k not in self.node_database:
                self.node_database.update( { str(k) : {} } )
            self.node_database[k]['DESC'] = v
            self.node_database[k]['CALL'] = str("")
            self.node_database[k]['LOC'] = str("")
        log.debug("exiting add_node_overrideS()")

    async def full_update(self, node_configuration, web_node_overrides):
        log.debug("entering full_update")
        try:
            await self.get_allmon_db()
            for n, c in node_configuration.nodes.items():
                self.set_my_info(c)
                self.add_node_overrides(web_node_overrides)        
            log.info("populated AllStarlink database")
        except ASLNodeDBException as e:
            log.error(e)

    async def db_updater(self, node_configuration, web_node_overrides):
        await self.full_update(node_configuration, web_node_overrides)
        while True:
            await asyncio.sleep(15*60)
            await self.full_update(node_configuration, web_node_overrides)

class ASLNodeDBException(Exception):
    """ sepcific Exception for class """
