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

# Work with CLI or Web
$CMD = "";
if(defined('STDIN')){
    if(array_key_exists(1,$argv)){
        $CMD = $argv[1];
    } else {
        print "asl-statmon.php ELEMENT\n";
        exit(1);
    }
} else {
    $CMD = getGetVar("e");
}

# Parse Config
$allmon_cfg = readConfig();
if(! $allmon_cfg){
    print(getJSONError("could not parse config file - likely misformatted"));
    exit;
}

# Process the command
switch($CMD){
	case 'nodelist':
		print_r(getAllNodesJSON($allmon_cfg));
		break;
	case 'customize':
		$customize = array(
			"HEADER_TITLE" => $CONFIG_HEADER_TITLE ,
			"HEADER_LOGO" => $CONFIG_HEADER_LOGO
		);
		print_r(json_encode($customize));
		break;
	default:
		print(getJSONError("unknown command " . $CMD));
		break;
}
?>
