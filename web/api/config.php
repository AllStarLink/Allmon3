<?php
#
# Configuration for the Web API of Allmon3
# Note: This is PHP code executed inline of the program
# so proper PHP syntax is required
#

# Name of the .ini file. The full directory path 
# will be appended based on the location of this file
# to match the installation location
$CONFIG_INI_FILE = "allmon3.ini";

# Site Customization Settings

# CONFIG_HEADER_TITLE appears centered in the top nav/header bar
$CONFIG_HEADER_TITLE = "Allmon3 Monitoring Dashboard";

# CONFIG_LOGO_IMG appears aligned right in the top-right corner
# of the page. The max height of this image should be 50px. If
# you do not want a logo to appear, leave this entry as an
# empty string "". Image file is relative to the img/ subdirectory
# of Allmon3
$CONFIG_HEADER_LOGO = "circle.png";


#####                                       #####
##### WARNING - THIS ARE INTERNAL VARIABLES #####
##### IT IS **EXTREMELY** UNLIKELY YOU EVER #####
##### NEED TO CHANGE ANYTHING BELOW!!       #####
#####                                       #####

$CONFIG_ZMQ_LOCALHOST = "127.0.0.1";
$CONFIG_ZMQ_SNDTIMEO = 2000;
$CONFIG_ZMQ_RCVTIMEO = 2000;
$CONFIG_ZMQ_LINGER = 2000;

$CONFIG_ALLMON3_INI = __DIR__ . "/" . $CONFIG_INI_FILE;
?>
