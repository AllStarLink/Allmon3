<?php
#
# Common functions for all Allmon3 web API
#

function getGetVar($id) {
    return filter_var(trim($_GET[$id]), FILTER_SANITIZE_STRING);
}

function getJSONError($errmsg) {
	return sprintf("{ \"%s\" : \"%s\" }", "ERROR", $errmsg);
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


?>
