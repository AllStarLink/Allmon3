/*
 * Copyright(C) 2023 AllStarLink
 * Allmon3 and all components are Licensed under the AGPLv3
 * see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
 * 
 * This excludes the use of the Bootstrap libraries which are licensed 
 * separately.
 *
 */

var cmdout = "";

// Page Load
window.addEventListener("load", function(){
	const nodeParam = findGetParameter("n");
	document.getElementById("cmd-node").value = nodeParam;
	
});

// Send a command
function sendCommand() {
	var form = new FormData(document.getElementById("command"));
	var xmlhttp = new XMLHttpRequest();
	var url = "api/asl-cmdlink.php"
	xmlhttp.onreadystatechange = function () {
	if( this.readyState == 4 && this.status == 200 ){
		cmdout = JSON.parse(this.responseText);
		displayCommandResults(cmdout);
	} else if( this.readyState == 4 && this.status != 200 ){
		console.log("HTTP error sending command");
		}
	};
	xmlhttp.open("POST", url, true);
	xmlhttp.send(form);
}

function displayCommandResults(output){
	if( output["SUCCESS"] ){
		document.getElementById("test").innerHTML = atob(output["SUCCESS"]);
	} else {
		document.getElementById("test").innerHTML = output["ERROR"];
	}
}
