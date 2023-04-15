<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

require_once("functions.php");
require_once("config.php");

if(!extension_loaded("zmq")){
	print(getJSONError("PHP instance does not have the zmq module available"));
	exit(1);
}

if(defined('STDIN')){
	if(array_key_exists(1,$argv)){
		$ASL_NODE = $argv[1];
	} else {
		print "asl-votermon.php NODE\n";
		exit(1);
	}
} else {
	$ASL_NODE = getGetVar("node");
}

if(!$ASL_NODE){
	print(getJSONError("node not specified"));
	exit;
}

$allmon_cfg = readVoterConfig();

if(! $allmon_cfg){
	print(getJSONError("could not parse config file - likely misformatted"));
	exit;
}

$z_port = getINIConfigVal($allmon_cfg, $ASL_NODE, "vmonport");
if( $z_port == "" ){
	print(getJSONError("could not find vmonport= for node " . $ASL_NODE));
	exit;
}

$z_host = getINIConfigVal($allmon_cfg, $ASL_NODE, "vmonip");
if( $z_host == "" ){
	$z_host = CONFIG_ZMQ_LOCALHOST;
}

$zmq_dsn = sprintf("tcp://%s:%d", $z_host, $z_port);

$r = new ZMQSocket(new ZMQContext(), ZMQ::SOCKET_SUB);
$r->connect ($zmq_dsn);
$r->setSockOpt(ZMQ::SOCKOPT_SUBSCRIBE, $ASL_NODE);
$r->setSockOpt(ZMQ::SOCKOPT_SNDTIMEO, CONFIG_ZMQ_SNDTIMEO);
$r->setSockOpt(ZMQ::SOCKOPT_RCVTIMEO, CONFIG_ZMQ_RCVTIMEO);
$r->setSockOpt(ZMQ::SOCKOPT_LINGER, CONFIG_ZMQ_LINGER);

# the other end sends 2 messages in a multipart
$msg = $r->recvMulti();
$r->disconnect($zmq_dsn);

if($msg[1]){
	print($msg[1]);
	exit(0);
} else {
	print(getJSONError("no response from ZMQ message bus; wrong IP or port?"));
	exit(1);
}
?>
