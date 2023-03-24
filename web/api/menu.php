<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

# Standard stuff
require_once("functions.php");
require_once("config.php");

if(!strcmp(php_sapi_name(),"cli")){
    header('Content-Type: application/json');
}

# Parse Config
$allmon_cfg = readConfig();
if(! $allmon_cfg){
    print(getJSONError("could not parse config file - likely misformatted"));
    exit;
}

if( ! file_exists(__DIR__ . "/menu.ini")){
	print(getJSONError("no " . __DIR__ . "/menu.ini"));
	exit;
}

$menu = parse_ini_file(__DIR__ . "/menu.ini", true);

print(json_encode($menu));
exit;
?>
