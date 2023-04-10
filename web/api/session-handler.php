<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

require_once("functions.php");
require_once("/etc/allmon3/config.php");

session_start();

$action = null;
if( sizeof($_POST) > 0 ){
	$action = getPostVar("action");
} 

if(strcmp($action,"login") == 0){
	$user = getPostVar("user");
	$pass = getPostVar("pass");
	
	if(strcmp($user,"") == 0 || strcmp($pass,"") == 0){
		header('Content-Type: application/json');
		print(getJSONError("login with no user or pass"));
		exit;
	}

	$users = array_map("userscsv", file($USERS_TABLE_LOCATION));
	$header = array_shift($users);
	array_walk($users, '_combine_array', $header);
	$uk = array_search($user, array_column($users, "user"));


	if(isset($uk)){
		$comppass = $users[$uk]["pass"];
		if(password_verify($pass, $comppass)){
			session_regenerate_id();
			$_SESSION['user'] = $user;
			$_SESSION['valid'] = true;
			header('Content-Type: application/json');
			print(getJSONSuccess("OK"));
		} else {
			header('Content-Type: application/json');
			print(getJSONError("invalid username or password"));
			exit;
		}
	} else {
		header('Content-Type: application/json');
		print(getJSONError("invalid username or password"));
		exit;
	}
}

if(strcmp($action,"logout") == 0){
	session_destroy();
	print(getJSONSuccess("OK"));
	exit;
}

if(!isset($_SESSION['valid'])){
	header('Content-Type: application/json');
	print(getJSONSecurityEvent("client is not logged in"));
	exit;
}

// If I pass out the bottom, everything is logged in and valid

?>
