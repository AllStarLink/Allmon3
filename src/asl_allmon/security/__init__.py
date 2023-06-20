#!/usr/bin/python3
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

import csv
import logging
import uuid
import time
import argon2

_BUILD_ID = "0.11.1"
log = logging.getLogger(__name__)

class Security:
    """ Allmon3 Security Subsystem """

    session_db = None
    userdb = None
    user_file = None

    def __init__(self, user_file):
        self.session_db = dict()
        self.userdb = dict()
        self.user_file = user_file
        self.__load_db()

    def __load_db(self):
        with open(self.user_file, newline="") as uf:
            users = csv.DictReader(uf, delimiter="|")
            for row in users:
                self.userdb.update({ row["user"] : row["pass"] })
        log.debug("loaded %s entries from %s", len(self.userdb), self.user_file)
        uf.close()

    def reload_db(self):
        self.userdb.clear()
        self.session_db.clear()
        self.__load_db()

    def validate(self, user, passwd):
        try:
            if user == "user":
                log.debug("User passed as 'user'; auto-reject")
                return False
    
            if user in self.userdb:
                ph = argon2.PasswordHasher(type=argon2.Type.ID)
                ph.verify(self.userdb[user], passwd)
    
            return True
    
        except argon2.exceptions.VerifyMismatchError:
            return False

    def create_session(self, ipaddr):
        ss = SecuritySession(ipaddr)
        self.session_db.update({ ss.session_id : ss })
        return ss.session_id

    def destroy_session(self, session_id):
        try:
            self.session_db.pop(session_id)
            return True
        except (IndexError, KeyError):
            return False

class SecuritySession:
    """ Basically a stuct """
    def __init__(self, ipaddr):
        self.ipaddr = ipaddr
        self.session_id = str(uuid.uuid4())
        self.creation = int(time.time())

class SecurityException(Exception):
    """ Exceptions for the Security class """
