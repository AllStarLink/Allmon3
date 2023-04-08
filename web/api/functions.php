<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

#
# Common functions for all Allmon3 web API
#

# Sanitize and return a GET parameter
function getGetVar($id) {
    return filter_var(trim($_GET[$id]), FILTER_SANITIZE_STRING);
}

# Sanitize and return a POST parameter
function getPostVar($id) {
    return filter_var(trim($_POST[$id]), FILTER_SANITIZE_STRING);
}

# Format and return a JSON SUCCESS
function getJSONSuccess($msg) {
	return sprintf("{ \"%s\" : \"%s\" }", "SUCCESS", $msg);
}

# Format and return a JSON error
function getJSONError($errmsg) {
	return sprintf("{ \"%s\" : \"%s\" }", "ERROR", $errmsg);
}

# Format and return a JSON security event
function getJSONSecurityEvent($secmsg) {
	return sprintf("{ \"%s\" : \"%s\" }", "SECURITY", $secmsg);
}

# Find and parse the configuration file
function readConfig(){
	if( file_exists("/etc/allmon3/allmon3-web.ini") ){
		return parse_ini_file("/etc/allmon3/allmon3-web.ini", true);
	}

	if( file_exists("/etc/allmon3/allmon3.ini") ){
		return parse_ini_file("/etc/allmon3/allmon3.ini", true);
	}

	print(getJSONError("no config found at /etc/allmon3/allmon3.ini or /etc/allmon3/allmon3-web.ini"));
	exit;
}

# Return the value from an .ini-sourced file
# $ini - INI Array, $section - [SECTION], $key = field
# returns the value or false
function getINIConfigVal($ini, $section, $key){
	if( ! array_key_exists($section, $ini)){
		return false;
	} else {
		if( array_key_exists($key, $ini[$section])){
			return $ini[$section][$key];
		} else
			return false;
		}
}

# Return all defined single nodes
function getAllNodes($ini){
	$nodes = array();
	foreach($ini as $node => $data){
		array_push($nodes, $node);
	}
	return $nodes;
}

# Return all defined single nodes as JSON array
function getAllNodesJSON($ini){
	return json_encode(getAllNodes($ini));
}

# XOR "crypt" function
function xor_crypt($string, $key){
	for($i = 0; $i < strlen($string); $i++) 
		$string[$i] = ($string[$i] ^ $key[$i % strlen($key)]);
	return base64_encode($string);
}

# Generalized function for ZMQ socket
function zmq_client_socket($client_type){
	$client_socket = new ZMQSocket(new ZMQContext(), $client_type);
	$client_socket->setSockOpt(ZMQ::SOCKOPT_SNDTIMEO, CONFIG_ZMQ_SNDTIMEO);
	$client_socket->setSockOpt(ZMQ::SOCKOPT_RCVTIMEO, CONFIG_ZMQ_RCVTIMEO);
	$client_socket->setSockOpt(ZMQ::SOCKOPT_LINGER, CONFIG_ZMQ_LINGER);
	return $client_socket;
}

?>
