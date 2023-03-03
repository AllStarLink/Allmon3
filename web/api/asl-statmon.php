<?php
require_once("functions.php");
require_once("config.php");

if(!strcmp(php_sapi_name(),"cli")){
	header('Content-Type: application/json');
}

if(!extension_loaded("zm2q")){
	print(getJSONError("PHP instanance does not have the zmq module available"));
	exit(1);
}

if(defined('STDIN')){
	if(array_key_exists(1,$argv)){
		$ASL_NODE = $argv[1];
	} else {
		print "asl-statmon.php NODE\n";
		exit(1);
	}
} else {
	$ASL_NODE = getGetVar("node");
}

if(!$ASL_NODE){
	print(getJSONError("node not specified"));
	exit;
}

$allmon_cfg = parse_ini_file("/usr/local/etc/allmon3.ini", true);

if(! $allmon_cfg){
	print(getJSONError("could not parse /usr/local/etc/allmon3.ini"));
	exit;
}

$z_port = getINIConfigVal($allmon_cfg, $ASL_NODE, "monport");
if( $z_port == "" ){
	print(getJSONError("could not find monport= for node " . $ASL_NODE));
	exit;
}

$zmq_dsn = sprintf("tcp://%s:%d", $CONFIG_ZMQ_LOCALHOST, $z_port);

$r = new ZMQSocket(new ZMQContext(), ZMQ::SOCKET_SUB);
$r->connect ($zmq_dsn);
$r->setSockOpt(ZMQ::SOCKOPT_SUBSCRIBE, $CONFIG_ZMQ_SUBSCRIBE);
$r->setSockOpt(ZMQ::SOCKOPT_SNDTIMEO, $CONFIG_ZMQ_SNDTIMEO);
$r->setSockOpt(ZMQ::SOCKOPT_RCVTIMEO, $CONFIG_ZMQ_RCVTIMEO);
$r->setSockOpt(ZMQ::SOCKOPT_LINGER, $CONFIG_ZMQ_LINGER);
$msg = $r->recv();
$r->disconnect($zmq_dsn);

if($msg){
	print($msg);
	exit(0);
} else {
	print(getJSONError("no response from ZMQ message bus; wrong IP or port?"));
	exit(1);
}
?>
