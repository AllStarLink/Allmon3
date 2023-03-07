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
