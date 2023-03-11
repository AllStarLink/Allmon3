<?php
#
# Common functions for all Allmon3 web API
#

# Sanitize and return a GET parameter
function getGetVar($id) {
    return filter_var(trim($_GET[$id]), FILTER_SANITIZE_STRING);
}

# Format and return a JSON error
function getJSONError($errmsg) {
	return sprintf("{ \"%s\" : \"%s\" }", "ERROR", $errmsg);
}

# Find and parse the configuration file
function readConfig(){
	if( file_exists(__DIR__ . "/allmon3.ini.php") ){
		return parse_ini_file(__DIR__ . "/allmon3.ini.php", true);
	}

	if( file_exists("/usr/local/etc/allmon3.ini") ){
		return parse_ini_file("/usr/local/etc/allmon3.ini", true);
	}

	print(getJSONError("no config found at /usr/local/etc/allmon3.ini or " . __DIR__ . "/allmon3.ini"));
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


?>
