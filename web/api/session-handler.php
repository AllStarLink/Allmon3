<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

require_once("functions.php");
require_once("config.php");

session_start();

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

	require_once("passwords.php");
	if(isset($_AUTH_TABLE[$user])){
		if(password_verify($pass, $_AUTH_TABLE[$user])){
			session_regenerate_id();
			$_SESSION['user'] = $user;
			$_SESSION['valid'] = true;
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
	exit;
}

if(!isset($_SESSION['valid'])){
	header('Content-Type: application/json');
	print(getJSONError("client is not logged in"));
	exit;
}

// If I pass out the bottom, everything is logged in and valid

?>
