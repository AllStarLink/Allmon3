<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#
#
# NOTE: YOU ARE 99.9% LIKELY TO BE LOOKING FOR /etc/allmon3/web.ini!!
#
# This file is only for tuning/testing various timer related
# items as it relates to the internals of Allmon3's web interface.
# This file is NOT preserved across upgrades and should
# not be changed unless you are actively debugging and issue and
# coordinating changes with the developers via GitHub
#
#####                                        #####
##### WARNING - THESE ARE INTERNAL VARIABLES #####
##### IT IS **EXTREMELY** UNLIKELY YOU EVER  #####
##### NEED TO CHANGE ANYTHING BELOW!!        #####
#####                                        #####
#
define("CONFIG_ZMQ_LOCALHOST", "127.0.0.1");
define("CONFIG_ZMQ_SNDTIMEO", 2000);
define("CONFIG_ZMQ_RCVTIMEO", 2000);
define("CONFIG_ZMQ_LINGER", 0);
define("CONFIG_ZMQ_STAT_RETRIES", 3);
define("CONFIG_ZMQ_STAT_RETRY_INTERVAL", 1);
define("CONFIG_ZMQ_STAT_POLL_TIMEO", 1000);
define("CONFIG_ZMQ_CMD_RETRIES", 3);
define("CONFIG_ZMQ_CMD_RETRY_INTERVAL", 1);
define("CONFIG_ZMQ_CMD_POLL_TIMEO", 3000);
#
#
# Load in web.ini
if( file_exists("/etc/allmon3/web.ini") ){
	$config_ini = parse_ini_file("/etc/allmon3/web.ini", true);
	$CONFIG_HEADER_TITLE = $config_ini['web']['CONFIG_HEADER_TITLE'];
	$CONFIG_HEADER_LOGO = $config_ini['web']['CONFIG_HEADER_LOGO'];
	$DEFAULT_WEB_POLL_INTERVAL = $config_ini['web']['DEFAULT_WEB_POLL_INTERVAL'] * 1000;
	$USERS_TABLE_LOCATION = $config_ini['web']['USERS_TABLE_LOCATION'];
	$HOME_BUTTON_URL = $config_ini['web']['HOME_BUTTON_URL'];
} else {
	header('Content-Type: application/json');
    print(getJSONError("no config found at /etc/allmon3/web.ini"));
    exit;
}

?>
