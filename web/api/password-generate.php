<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

require_once("functions.php");
require_once("config.php");

if(strcmp(php_sapi_name(),"cli") != 0){
    header('Content-Type: application/json');
	print(getJSONError("CLI interactive use only"));
	exit;
}

print(php_sapi_name());
if(array_key_exists(1,$argv)){
	$user = $argv[1];
} else {
	print "password-generate.php USERNAME\n";
	exit(1);
}

print("        Password: ");
$passa = rtrim(fgets(STDIN));
print("Confirm Password: ");
$passb = rtrim(fgets(STDIN));
if(strcmp($passa,$passb) == 0){
	print("Copy the following line into passwords.php including the ending comma!\n\n");
	$pass = password_hash($passa, PASSWORD_ARGON2ID);
	printf("'%s' => '%s',\n\n", $user, $pass);
} else {
	print "passwords did not match\n";
	exit(1);
}

?>
