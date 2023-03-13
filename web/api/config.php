<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

#
# Configuration for the Web API of Allmon3
# Note: This is PHP code executed inline of the program
# so proper PHP syntax is required
#

# Site Customization Settings

# CONFIG_HEADER_TITLE appears centered in the top nav/header bar
$CONFIG_HEADER_TITLE = "Allmon3 Monitoring Dashboard";

# CONFIG_LOGO_IMG appears aligned right in the top-right corner
# of the page. The max height of this image should be 50px. If
# you do not want a logo to appear, leave this entry as an
# empty string "". Image file is relative to the img/ subdirectory
# of Allmon3
$CONFIG_HEADER_LOGO = "circle.png";


#####                                        #####
##### WARNING - THESE ARE INTERNAL VARIABLES #####
##### IT IS **EXTREMELY** UNLIKELY YOU EVER  #####
##### NEED TO CHANGE ANYTHING BELOW!!        #####
#####                                        #####

define("CONFIG_ZMQ_LOCALHOST", "127.0.0.1");
define("CONFIG_ZMQ_SNDTIMEO", 2000);
define("CONFIG_ZMQ_RCVTIMEO", 2000);
define("CONFIG_ZMQ_LINGER", 0);
define("CONFIG_ZMQ_STAT_POLL_TIMEO", 1000);
define("CONFIG_ZMQ_STAT_RETRIES", 3);
define("CONFIG_ZMQ_CMD_RETRIES", 3);
define("CONFIG_ZMQ_CMD_RETRY_INTERVAL", 1);
define("CONFIG_ZMQ_CMD_POLL_TIMEO", 3000);
?>
