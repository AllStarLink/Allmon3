<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

require_once("functions.php");
require_once("config.php");
require_once("session-handler.php");

if(strcmp(php_sapi_name(),"cli") != 0){
	header('Content-Type: application/json');
}

if(!extension_loaded("zmq")){
	print(getJSONError("PHP instance does not have the zmq module available"));
	exit(1);
}

if(defined('STDIN')){
	if(array_key_exists(1,$argv) && array_key_exists(2,$argv)){
		$ASL_NODE = $argv[1];
		$CMD = $argv[2];
	} else {
		print "asl-cmdlink.php NODE \"CMD\"\n";
		exit(1);
	}
} else {
	$ASL_NODE = getPostVar("node");
	$CMD = getPostVar("cmd");
}

if(!$ASL_NODE){
	print(getJSONError("node not specified"));
	exit;
}

if(!$CMD){
	print(getJSONError("cmd not specified"));
	exit;
}



$allmon_cfg = readConfig();

if(! $allmon_cfg){
	print(getJSONError("could not parse config file - likely misformatted"));
	exit;
}


$colocated = getINIConfigVal($allmon_cfg, $ASL_NODE, "colocated_on");
if($colocated == ""){
	$z_host = getINIConfigVal($allmon_cfg, $ASL_NODE, "cmdip");
	if( $z_host == "" ){
		$z_host = "127.0.0.1";
	}
	$z_port = getINIConfigVal($allmon_cfg, $ASL_NODE, "cmdport");
	$ASL_PASS = getINIConfigVal($allmon_cfg, $ASL_NODE, "pass");
} else {
    $z_host = getINIConfigVal($allmon_cfg, $colocated, "cmdip");
    if( $z_host == "" ){
        $z_host = "127.0.0.1";
    }
	 $z_port = getINIConfigVal($allmon_cfg, $colocated, "cmdport");
	$ASL_PASS = getINIConfigVal($allmon_cfg, $colocated, "pass");
}

if(!$ASL_PASS){
	print(getJSONError("no pass= for node $ASLNODE"));
	exit;
}

$zmq_dsn = sprintf("tcp://%s:%d", $z_host, $z_port);
$cmd = xor_crypt($CMD, $ASL_PASS);

$c = zmq_client_socket(ZMQ::SOCKET_REQ);
$c->connect ($zmq_dsn);

$retries_left = CONFIG_ZMQ_CMD_RETRIES;
while($retries_left){
	
	$c->send($cmd);

	$poll = new ZMQPoll();
	$poll->add($c, ZMQ::POLL_IN);
	$events = $poll->poll($read, $write, CONFIG_ZMQ_CMD_POLL_TIMEO);
	
	if($events > 0){
		$msg = $c->recv();
		break;
	} elseif(--$retries_left == 0) {
		print(getJSONError("no response from server - retries exhausted"));
	} else {
		// try creating a new socket
		$c = zmq_client_socket(ZMQ::SOCKET_REQ);
		sleep(CONFIG_ZMQ_CMD_RETRY_INTERVAL);
	}
}

try{
	$c->disconnect($zmq_dsn);
} catch( Exception $e){
	# do nothing	
}

if($msg){
	if(preg_match('/^OK\:/', $msg)){
		$output = preg_replace("/OK:\r\n/", "", $msg);
		print(getJSONSuccess(base64_encode($output)));
		exit(0);
	} else {
		print(getJSONError(base64_encode($msg)));
		exit(1);
	}
}
exit(1);
?>
