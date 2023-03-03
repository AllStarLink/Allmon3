<?php
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
$allmon_cfg = parse_ini_file("/usr/local/etc/allmon3.ini", true);
if(! $allmon_cfg){
    print(getJSONError("could not parse /usr/local/etc/allmon3.ini"));
    exit;
}

# Process the command
switch($CMD){
	case 'nodelist':
		print_r(getAllNodesJSON($allmon_cfg));
		break;
	default:
		print(getJSONError("unknown command " . $CMD));
		break;
}
?>
