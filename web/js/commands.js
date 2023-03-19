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

//
// General Send Command
//
function sendCommand(node, cmdStr) {
	const cmdForm = new FormData();
	cmdForm.append('node', node);
	cmdForm.append('cmd', cmdStr);
	const xmlhttp = new XMLHttpRequest();
	const url = "api/asl-cmdlink.php"
	xmlhttp.onreadystatechange = function () {
	if( this.readyState == 4 && this.status == 200 ){
		const cmdout = JSON.parse(this.responseText);
		displayCommandResults(cmdout);
	} else if( this.readyState == 4 && this.status != 200 ){
		console.log("HTTP error sending command");
		}
	};
	xmlhttp.open("POST", url, true);
	xmlhttp.send(cmdForm);
}

//
// Command Results
//
function displayCommandResults(output){
	let res = "";
	if( output["SUCCESS"] ){
		let out = atob(output["SUCCESS"]);
		res = `
			<div class="alert alert-success" role="alert">Command Successful</div>
			<pre>${out}<pre>
		`;
	} else {
		let out = output["ERROR"];
		res = `
			<div class="alert alert-danger" role="alert">Command Error</div>
			<pre>${out}<pre>
		`;
	}

	document.getElementById("command-modal-body").innerHTML = res;
}

//
// Command Handling
//
function openCmdModal(node){
	const modal = new bootstrap.Modal(document.getElementById("commandModal"), {});
	document.getElementById("commandModalTitleBox").innerHTML = `Execute Command on ${node}`;
	document.getElementById("command-modal-body").innerHTML = getCommandModalForm(node);
	modal.show();
}

//
// Command Modal Interface
//
function getCommandModalForm(node){
	return `
<div class="container-fluid">
	<form id="command-modal-form">
		<div class="row mb-2">
			<div class="col-4">
				<label for="cmf-link-node-cmd">Link Command</label>
			</div>
			<div class="col-8">
				<select id="cmf-link-node-cmd" name="cmf-link-node-cmd" class="form-select" aria-label="Connect Disconnect command">
					<option selected>Choose a command</option>
					<option value="rpt cmd ${node} ilink 3">Connect</option>
					<option value="rpt cmd ${node} ilink 1">Disconnect</option>
					<option value="rpt cmd ${node} ilink 6">Disconnect All</option>
					<option value="rpt cmd ${node} ilink 2">Connect - Monitor Only</option>
					<option value="rpt cmd ${node} ilink 13">Connect Permanent</option>
					<option value="rpt cmd ${node} ilink 12">Connect Permanent - Monitor Only</option>
					<option value="rpt cmd ${node} ilink 8">Local Monitor</option>
					<option value="rpt cmd ${node} ilink 18">Local Monitor Permanent</option>
				</select>
			</div>
		</div>
		<div class="row mb-2">
			<div class="col-4">
				<label for="cmf-link-node-num">Node #</label>
			</div>
			<div class="col-8">
				<input id="cmf-link-node-num" name="cmf-link-node-num" class="form-control" type="text">
			</div>
		</div>
		<div class="row mb-2">
			<div class="col-4">
			</div>
			<div class="col-8">
				<button type="button" class="btn btn-secondary" onclick="executeNodeLinkCmd(${node})">Execute</button>
			</div>
		</div>
	<form>
</div>

`;
}

function executeNodeLinkCmd(node){
	let command = document.getElementById("cmf-link-node-cmd").value;
	let linknode = document.getElementById("cmf-link-node-num").value;
	sendCommand(node, `${command} ${linknode}`);	
}
