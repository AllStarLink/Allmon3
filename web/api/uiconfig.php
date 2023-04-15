<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

# Standard stuff
require_once("functions.php");
require_once("config.php");

# Work with CLI or Web
$CMD = "";
if(defined('STDIN')){
    if(array_key_exists(1,$argv)){
        $CMD = $argv[1];
    } else {
        print "uiconfig.php ELEMENT [NODE]\n";
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

	# Get the complete configured node list
	case 'nodelist':
		print_r(getAllNodesJSON($allmon_cfg));
		break;

	case 'pollint':
		if(defined('STDIN')){
			if(array_key_exists(2, $argv)){
				$NODE = $argv[2];
			} else {
				print "uiconfig.php pollint [NODE]\n";
				exit(1);
			}
		} else {
			$NODE = getGetVar("n");
		}
		if(array_key_exists("webpinterval", $allmon_cfg[$NODE])){
			$poll_int = $allmon_cfg[$NODE]["webpinterval"];
			if(array_key_exists("webpsubsec", $allmon_cfg[$NODE])){
				if( strcmp($allmon_cfg[$NODE]["webpsubsec"], "y") == 0 ){
					if( $poll_int < 250 ){
						$poll_int = 250;
					}
				} else {
					$poll_int = $poll_int * 1000;
				}
			} else {
				$poll_int = $poll_int * 1000;
			}
			print(getJSONSuccess($poll_int));

		} else {
			print(getJSONSuccess($DEFAULT_WEB_POLL_INTERVAL));
		}
		break;
		
	# Get the customization variables
	case 'customize':
		$customize = array(
			"HEADER_TITLE" => $CONFIG_HEADER_TITLE ,
			"HEADER_LOGO" => $CONFIG_HEADER_LOGO ,
			"HOME_BUTTON_URL" => $HOME_BUTTON_URL
		);
		print_r(json_encode($customize));
		break;

	# Get any custom menu
	case 'custmenu':
		if( ! file_exists("/etc/allmon3/menu.ini")){
		    print(getJSONError("no /etc/allmon3/menu.ini"));
	    	break;
		}
		$menu = parse_ini_file("/etc/allmon3/menu.ini", true);
		print(json_encode($menu));
		break;

	# Get the system commands
	case 'syscmd':
		if( ! file_exists("/etc/allmon3/web.ini")){
            print(getJSONError("no /etc/allmon3/web.ini"));
            break;
        }
        $webini = parse_ini_file("/etc/allmon3/web.ini", true);

		$commands = array();
		foreach( $webini["syscmds"] as $c => $l ){
			$commands = array_merge($commands, array($c => $l));
		}
		print_r(json_encode($commands));
		break;

	case 'voter':
		$voter_cfg = readVoterConfig();
		if(! $voter_cfg){
		    print(getJSONError("could not parse config file /etc/allmon3/voter.ini - likely misformatted"));
		    exit;
		}

		if(defined('STDIN')){
            if(array_key_exists(2, $argv)){
                $NODE = $argv[2];
            } else {
                print "uiconfig.php voter NODE\n";
                exit(1);
            }
        } else {
            $NODE = getGetVar("n");
        }

		if( array_key_exists("webvpinterval", $voter_cfg[$NODE])){
			$poll_int = $voter_cfg[$NODE]["webvpinterval"];
            if(array_key_exists("webvpsubsec", $voter_cfg[$NODE])){
                if( strcmp($voter_cfg[$NODE]["webvpsubsec"], "y") == 0 ){
                    if( $poll_int < 250 ){
                        $poll_int = 250;
                    }
                } else {
                    $poll_int = $poll_int * 1000;
                }
            } else {
                $poll_int = $poll_int * 1000;
            }
		} else {
			$poll_int = 1000;
		}
		$msg = sprintf("{ \"SUCCESS\" : { \"TITLE\" : \"%s\" , \"POLLTIME\" : \"%s\" } }",
			$voter_cfg[$NODE]["votertitle"], $poll_int);
		print($msg);
		break;

	case 'overrides':
		if( ! file_exists("/etc/allmon3/web.ini")){
            print(getJSONError("no /etc/allmon3/web.ini"));
            break;
        }
        $webini = parse_ini_file("/etc/allmon3/web.ini", true);

		$overrides = array();
		foreach( $webini["node-overrides"] as $n => $t ){
			$overrides += array($n => $t);
		}
		print_r(json_encode($overrides));
		break;

	# Otherwise error...
	default:
		print(getJSONError("unknown command " . $CMD));
		break;
}
?>
