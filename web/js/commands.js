/*
 * Copyright(C) 2023 AllStarLink
 * Allmon3 and all components are Licensed under the AGPLv3
 * see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
 * 
 * This excludes the use of the Bootstrap libraries which are licensed 
 * separately.
 *
 */

//
// command-specific globals
//
var cmdShortcut = "";

//
// General Send Command
//
async function sendCommand(node, cmdStr) {
	const cmdForm = new FormData();
	cmdForm.append('node', node);
	cmdForm.append('cmd', cmdStr);

	let cmdout = await postAPIForm("api/asl-cmdlink.php", cmdForm);
	let res = "";
	if( cmdout["SUCCESS"] ){
		let out = atob(cmdout["SUCCESS"]);
		res = `
			<div class="alert alert-success" role="alert">Command Successful</div>
			<pre>${out}<pre>
		`;
	} else if ( cmdout["SECURITY"] ){
		let out = cmdout["SECURITY"];
		res = `
            <div class="alert alert-danger" role="alert">Security Error</div>
            <pre>${out}<pre>
        `;
	} else {
		let out = cmdout["ERROR"];
		res = `
			<div class="alert alert-danger" role="alert">Command Error</div>
			<pre>${out}<pre>
		`;
	}

	document.getElementById("cmd-output").innerHTML = res;

    // toggle the buttons
    document.getElementById("cmd-exec-btn").style.display = "inline-block";
    document.getElementById("cmd-exec-spinner").style.display = "none";
	document.getElementById("cmd-exec-close").style.display = "inline-block";
}

//
// Command Handling
//
function openCmdModalLink(node){
	const modal = new bootstrap.Modal(document.getElementById("commandModal"), {});
		document.getElementById("commandModalTitleBox").innerHTML = `Execute Command on ${node}`;
	if(loggedIn){
		document.getElementById("command-modal-body").innerHTML = getLinkCommandModalForm(node);
	} else {
		document.getElementById("command-modal-body").innerHTML = `<div class="alert alert-danger role="alert">Must Logon First</div>`;	
	}
	modal.show();
}

function openCmdModalCLI(node){
	const modal = new bootstrap.Modal(document.getElementById("commandModal"), {});
	document.getElementById("commandModalTitleBox").innerHTML = `Execute Command on ${node}`;
	if(loggedIn){
		document.getElementById("command-modal-body").innerHTML = getCLICommandModalForm(node);
	} else {
		document.getElementById("command-modal-body").innerHTML = `<div class="alert alert-danger role="alert">Must Logon First</div
>`;
	}
	modal.show();
}


//
// Link Command Modal Interface
//
function getLinkCommandModalForm(node){
	return `
<div id="cmd-link-cmd" class="container">
	<form id="command-modal-form" class="needs-validation" novalidate>
		<div class="row row-cols-3 g-3">
			<div class="col fw-bolder">
				<label for="cmf-link-node-cmd">Command</label>
			</div>
				<div class="col fw-bolder">
				<label for="cmf-link-node-num">Node #</label>
			</div>
			<div class="col fw-bolder">
				<label for="cmf-link-node-perm" class="form-check-label">Permanent</label>
			</div>
			<div class="col">
				<select id="cmf-link-node-cmd" name="cmf-link-node-cmd" class="form-select"
						aria-label="Connect Disconnect command" required>
					<option selected disabled value="">Choose a command</option>
					<option value="3">Connect</option>
					<option value="1">Disconnect</option>
					<option value="2">Monitor</option>
					<option value="8">Local Monitor</option>
					<option value="6">Disconnect All</option>
				</select>
				<div class="invalid-feedback">
					Select a command
				</div>
			</div>
			<div class="col">
				<input id="cmf-link-node-num" name="cmf-link-node-num" class="form-control" 
					type="text" value="${cmdShortcut}" required>
				<div class="invalid-feedback">
					Enter a node
				</div>
			</div>
			<div class="col">
				<select id="cmf-link-node-perm" name="cmf-link-node-perm" class="form-select" 
					arial-label="permanent link" required>
					<option value="no" selected>No</option>
					<option value="yes" >Yes</option>
				<select>
			</div>
			<div class="col">
				<button id="cmd-exec-btn" type="button" class="btn btn-secondary" onclick="executeNodeLinkCmd(${node})">
					Execute
				</button>
				<div id="cmd-exec-spinner" class="spinner-grow text-secondary" style="display:none" role="status">
					<span class="visually-hidden">Executing...</span>
				</div>
			</div>
		</div>
	<form>
</div>
<div id="cmd-output" class="container my-2"></div>
`;
}

function executeNodeLinkCmd(node){

	// execute the form
	let formReady = true;
	let cmfCmd = document.getElementById("cmf-link-node-cmd");
	let cmfNode = document.getElementById("cmf-link-node-num");
	let permFlag = document.getElementById("cmf-link-node-perm").value;
	
	if(cmfCmd.checkValidity()){
		cmfCmd.classList.remove("is-invalid");
		cmfCmd.classList.add("is-valid");
	} else {
		cmfCmd.classList.remove("is-valid");
		cmfCmd.classList.add("is-invalid");
		return null;
	}
	let command = Number(cmfCmd.value);

	if( command == 1 || command == 2 || command == 3 || command == 8 ){
		if(cmfNode.checkValidity()){
			cmfNode.classList.remove("is-invalid");
			cmfNode.classList.add("is-valid");
		} else {
			cmfNode.classList.remove("is-valid");
			cmfNode.classList.add("is-invalid");
			return null;
		}
	
		if(permFlag === "yes")
			command += 10;
	}
	let linknode = cmfNode.value;

	if(linknode === ""){
		linknode = "0";
	}

	// toggle the buttons
	document.getElementById("cmd-exec-btn").style.display = "none";
	document.getElementById("cmd-exec-spinner").style.display = "inline-block";
	document.getElementById("cmd-exec-close").style.display = "none";

	sendCommand(node, `rpt cmd ${node} ilink ${command} ${linknode}`);	
}

//
// CLI Command Modal Interface
//
function getCLICommandModalForm(node){
	return `
<div id="cmd-exec-cmd" class="container">
	<form id="command-modal-form" class="needs-validation" novalidate>
		<div class="row justify-content-start d-flex align-items-center mb-2">
			<div class="col-4 fw-bolder text-end">
				<label for="cmf-cmd-node-select">Command Template</label>
			</div>
			<div class="col-8">
                <select id="cmf-cmd-node-select" name="cmf-cmd-node-select"
						class="form-select" aria-label="system command" onchange="buildCLICommandModalCmd()" required>
                    <option selected disabled value="">Choose a command</option>
                    <option value="rpt stats ${node}">Show Node Status</option>
                    <option value="core show uptime">Show Uptime</option>
                    <option value="iax2 show registry">Show IAX Registry</option>
                    <option value="iax2 show channels">Show IAX Channels</option>
                    <option value="iax2 show netstats">Show Network Status</option>
                    <option value="rpt lstats ${node}">Show Link Status</option>
                    <option value="rpt show registrations">Show HTTP Registrations</option>
					<option value="custom">Custom command</option>
				</select>
			</div>
		</div>
		<div class="row justify-content-start d-flex align-items-center mb-2">
			<div class="col-4 fw-bolder text-end">
				<label for="cmf-cmd-node-cmd">Command</label>
			</div>
			<div class="col-8">
				<input id="cmf-cmd-node-cmd" type="text" class="form-control" readonly required>
			</div>
		</div>
		<div class="row justify-content-start">
			<div class="col-4 text-end">
				<button id="cmd-exec-btn" type="button" class="btn btn-secondary" onclick="executeNodeCLICmd(${node})">
					Execute
				</button>
				<div id="cmd-exec-spinner" class="spinner-grow text-secondary" style="display:none" role="status">
					<span class="visually-hidden">Executing...</span>
				</div>
			</div>
		</div>
	<form>
</div>
<div id="cmd-output" class="container my-2"></div>
`;
}

function buildCLICommandModalCmd(node){
	let cmfSel = document.getElementById("cmf-cmd-node-select");
	let cmfCmd = document.getElementById("cmf-cmd-node-cmd");

	if(cmfSel.value === "custom"){
		cmfCmd.value = "";
		cmfCmd.readOnly = false;
	} else {
		cmfCmd.value = cmfSel.value;
		cmfCmd.readOnly = true;
	}
}

function executeNodeCLICmd(node){
	let cmfSel = document.getElementById("cmf-cmd-node-select");
	let cmfCmd = document.getElementById("cmf-cmd-node-cmd");

	if(cmfSel.checkValidity()){
		cmfSel.classList.remove("is-invalid");
		cmfSel.classList.add("is-valid");
	} else {
		cmfSel.classList.remove("is-valid");
		cmfSel.classList.add("is-invalid");
		return null;
	}

	if(cmfCmd.checkValidity()){
		cmfCmd.classList.remove("is-invalid");
		cmfCmd.classList.add("is-valid");
	} else {
		cmfCmd.classList.remove("is-valid");
		cmfCmd.classList.add("is-invalid");
		return null;
	}


	// toggle the buttons
	document.getElementById("cmd-exec-btn").style.display = "none";
	document.getElementById("cmd-exec-spinner").style.display = "inline-block";
	document.getElementById("cmd-exec-close").style.display = "none";


	sendCommand(node, `${cmfCmd.value}`);	
}


//
// Command Interface Hooks
//

function nodeCmdShortcut(node){
	cmdShortcut = node;
}
