<?php
#
# Copyright(C) 2023 AllStarLink
# Allmon3 and all components are Licensed under the AGPLv3
# see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
#

require_once("functions.php");
require_once("/etc/allmon3/config.php");
require_once("session-handler.php");

if(strcmp(php_sapi_name(),"cli") != 0){
	header('Content-Type: application/json');
}

print getJSONSuccess("OK");
exit(0);

?>
