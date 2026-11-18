/*
 * Copyright(C) @@COPYDATE@@ AllStarLink
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

	let cmdout = await postAPIForm("master/cmd", cmdForm);
	let res = "";
	if( cmdout["SUCCESS"] ){
		let out = cmdout['SUCCESS'];
		try {
			out = atob(cmdout["SUCCESS"]);
		} catch(e) {}
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
async function openCmdModalLink(node, defCmd){
	const modal = new bootstrap.Modal(document.getElementById("commandModal"), {});
		document.getElementById("commandModalTitleBox").innerHTML = `Execute Command on ${node}`;
	if(loggedIn){
		document.getElementById("command-modal-body").innerHTML = getLinkCommandModalForm(node, defCmd);
	} else {
		document.getElementById("command-modal-body").innerHTML = `<div class="alert alert-danger role="alert">Must Logon First</div>`;
	}
	modal.show();
	if(loggedIn){
		const favoritesSelect = document.getElementById("cmf-link-favorite");
		try {
			const favorites = await getAPIJSON(`master/node/${node}/favorites`);
			// The user may have closed this modal or opened it for another node.
			if (document.getElementById("cmf-link-favorite") !== favoritesSelect) return;
			if (Array.isArray(favorites)) {
				renderLinkFavorites(favoritesSelect, favorites);
			} else {
				favoritesSelect.replaceChildren(new Option("Favorites unavailable", ""));
			}
		} catch (e) {
			if (document.getElementById("cmf-link-favorite") === favoritesSelect) {
				favoritesSelect.replaceChildren(new Option("Favorites unavailable", ""));
			}
		}
	}
}

function renderLinkFavorites(select, favorites, selectedNode = "") {
	select._favoriteLabels = new Map(favorites.map(item => [item.node, item.label]));
	select.replaceChildren(new Option(
		favorites.length ? "Choose a favorite" : "No favorites saved", ""));
	for (const favorite of favorites) {
		// Option assigns text, so names from other users never become HTML.
		select.add(new Option(`${favorite.label} (${favorite.node})`, favorite.node));
	}
	select.disabled = favorites.length === 0;
	select.value = selectedNode;
	document.getElementById("cmf-favorite-delete").disabled = !selectedNode;
	document.getElementById("cmf-favorite-save").textContent = selectedNode ? "Save changes" : "Add favorite";
}

function selectLinkFavorite() {
	const select = document.getElementById("cmf-link-favorite");
	const selected = select.value;
	document.getElementById("cmf-favorite-delete").disabled = !selected;
	document.getElementById("cmf-favorite-save").textContent = selected ? "Save changes" : "Add favorite";
	if (!selected) document.getElementById("cmf-favorite-name").value = "";
	if (selected) {
		const nodeInput = document.getElementById("cmf-link-node-num");
		nodeInput.value = selected;
		nodeInput.classList.remove("is-invalid");
		document.getElementById("cmf-favorite-name").value = select._favoriteLabels.get(selected) || "";
	}
}

function newLinkFavorite() {
	document.getElementById("cmf-link-favorite").value = "";
	document.getElementById("cmf-favorite-name").value = "";
	document.getElementById("cmf-favorite-delete").disabled = true;
	document.getElementById("cmf-favorite-save").textContent = "Add favorite";
	setFavoriteFeedback("Adding a new favorite. Enter its node number and name.");
}

function setFavoriteFeedback(message, isError = false) {
	const feedback = document.getElementById("cmf-favorite-feedback");
	feedback.textContent = message;
	feedback.className = isError ? "small mt-2 text-danger" : "small mt-2 text-success";
}

async function changeLinkFavorite(source, action) {
	const select = document.getElementById("cmf-link-favorite");
	const nodeInput = document.getElementById("cmf-link-node-num");
	const nameInput = document.getElementById("cmf-favorite-name");
	const selected = select.value;
	const node = action === "delete" ? selected : nodeInput.value.trim();
	const label = nameInput.value.trim();
	if (!/^[0-9]{1,10}$/.test(node) || (action === "save" && (!label || label.length > 80))) {
		setFavoriteFeedback("Enter a numeric node ID and a name of 1 to 80 characters.", true);
		return;
	}
	const saveButton = document.getElementById("cmf-favorite-save");
	const deleteButton = document.getElementById("cmf-favorite-delete");
	saveButton.disabled = deleteButton.disabled = true;
	try {
		const response = await fetch(`master/node/${source}/favorites`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ action, node, label, original_node: selected || null }),
		});
		const result = await response.json();
		if (!response.ok || !Array.isArray(result.SUCCESS)) {
			throw new Error(result.ERROR || result.SECURITY || "Unable to save favorites");
		}
		if (document.getElementById("cmf-link-favorite") !== select) return;
		const editing = action === "save" && !!selected;
		renderLinkFavorites(select, result.SUCCESS, editing ? node : "");
		if (!editing) nameInput.value = "";
		setFavoriteFeedback(action === "delete" ? "Favorite deleted." :
			editing ? "Favorite updated. Choose New favorite to add another." :
			"Favorite added. Enter another node number and name to add more.");
	} catch (e) {
		if (document.getElementById("cmf-link-favorite") === select) {
			setFavoriteFeedback(e.message || "Unable to save favorites", true);
			deleteButton.disabled = !selected;
		}
	} finally {
		if (document.getElementById("cmf-link-favorite") === select) saveButton.disabled = false;
	}
}

async function openCmdModalCLI(node){
	const modal = new bootstrap.Modal(document.getElementById("commandModal"), {});
	document.getElementById("commandModalTitleBox").innerHTML = `Execute Command on ${node}`;
	if(loggedIn){
		document.getElementById("command-modal-body").innerHTML = await getCLICommandModalForm(node);
	} else {
		document.getElementById("command-modal-body").innerHTML = `<div class="alert alert-danger role="alert">Must Logon First</div
>`;
	}
	modal.show();
}


//
// Link Command Modal Interface
//
function getLinkCommandModalForm(node, defCmd){
	let opt1 = "";
	let opt2 = "";
	let opt3 = "";
	let opt6 = "";
	let opt8 = "";

	if( defCmd == 1 ){
		opt1 = "selected";
	}
	rForm = `
<div id="cmd-link-cmd" class="container">
	<form id="command-modal-form" class="needs-validation" novalidate>
		<div class="row justify-content-start d-flex align-items-center mb-2">
			<div class="col-12"><i>Hint: clicking on a node line first will pre-populate node numbers as appropriate.</i></div>
        </div>
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
	`;

	if(typeof defCmd === 'undefined'){
		rForm = rForm.concat(`<option selected disabled value="">Choose a command</option>`);
	}

	rForm = rForm.concat(`
					<option ${opt3} value="3">Connect</option>
					<option ${opt1} value="1">Disconnect</option>
					<option ${opt2} value="2">Monitor</option>
					<option ${opt8} value="8">Local Monitor</option>
					<option ${opt6} value="6">Disconnect All</option>
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
				<label for="cmf-link-favorite" class="form-label mt-2">Favorites</label>
				<select id="cmf-link-favorite" class="form-select" aria-label="Favorite node"
						onchange="selectLinkFavorite()" disabled>
					<option value="">Loading favorites...</option>
				</select>
			</div>
			<div class="col">
				<select id="cmf-link-node-perm" name="cmf-link-node-perm" class="form-select"
					arial-label="permanent link" required>
					<option value="no" selected>No</option>
					<option value="yes" >Yes</option>
				</select>
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
		<div class="row g-2 mt-3 align-items-end">
			<div class="col-sm-5">
				<label for="cmf-favorite-name" class="form-label">Favorite name</label>
				<input id="cmf-favorite-name" class="form-control" type="text" maxlength="80"
						placeholder="Name this node">
			</div>
			<div class="col-sm-7 d-flex flex-wrap gap-2">
				<button id="cmf-favorite-save" type="button" class="btn btn-outline-primary"
						onclick="changeLinkFavorite(${node}, 'save')">Add favorite</button>
				<button type="button" class="btn btn-primary" onclick="newLinkFavorite()">New favorite</button>
				<button id="cmf-favorite-delete" type="button" class="btn btn-outline-danger"
						onclick="changeLinkFavorite(${node}, 'delete')" disabled>Delete</button>
			</div>
		</div>
		<div class="small mt-2">Select a favorite to edit it, or choose New favorite to add another.</div>
		<div id="cmf-favorite-feedback" class="small mt-2" role="status" aria-live="polite"></div>
	</form>
</div>
<div id="cmd-output" class="container my-2"></div>
	`);
	return rForm;
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
async function getCLICommandModalForm(node){

	let cmdopts = "";
	let ppath = window.location.pathname;
	let ppage = ppath.split("/").pop();
	isVoter = false;
	if( ppage === "voter.html" ){
		isVoter = true;
	}

	if( cmdShortcut.length == 0 ){
		cmdShortcut = "NODE";
	}

	const commands = await getAPIJSON("master/ui/custom/commands");
	for(let c in commands){
		if(isVoter && c.match(/^voter/)){
			let cmdstr = c.replace("'", "").replace("'","").replace("@",node).replace("%", cmdShortcut);
			cmdopts = cmdopts.concat(`<option value="${cmdstr}">`, commands[c], "</option>\n");
		} else if ( !isVoter && !c.match(/^voter/)) {
			let cmdstr = c.replace("'", "").replace("'","").replace("@",node).replace("%", cmdShortcut);
			cmdopts = cmdopts.concat(`<option value="${cmdstr}">`, commands[c], "</option>\n");
		}
	}

	const nodeCommands = await getAPIJSON(`master/ui/custom/nodecommands/${node}`);
	for(let c in nodeCommands){
		if(isVoter && c.match(/^voter/)){
			let cmdstr = c.replace("'", "").replace("'","").replace("@",node).replace("%", cmdShortcut);
			cmdopts = cmdopts.concat(`<option value="${cmdstr}">`, nodeCommands[c], "</option>\n");
		} else if ( !isVoter && !c.match(/^voter/)) {
			let cmdstr = c.replace("'", "").replace("'","").replace("@",node).replace("%", cmdShortcut);
			cmdopts = cmdopts.concat(`<option value="${cmdstr}">`, nodeCommands[c], "</option>\n");
		}
    }

	const modal = `
<div id="cmd-exec-cmd" class="container">
	<form id="command-modal-form" class="needs-validation" novalidate>
		<div class="row justify-content-start d-flex align-items-center mb-2">
        	<div class="col-2"></div>
            <div class="col-8"><i>Hint: clicking on a node line first will pre-populate node numbers as appropriate.</i></div>
            <div class="col-2"></div>
        </div>
		<div class="row justify-content-start d-flex align-items-center mb-2">
			<div class="col-4 fw-bolder text-end">
				<label for="cmf-cmd-node-select">Command Template</label>
			</div>
			<div class="col-8">
                <select id="cmf-cmd-node-select" name="cmf-cmd-node-select"
						class="form-select" aria-label="system command" onchange="buildCLICommandModalCmd()" required>
                    <option selected disabled value="">Choose a command</option>
					${cmdopts}
					<option value="custom">Custom command</option>
				</select>
			</div>
		</div>
		<div class="row justify-content-start d-flex align-items-center mb-2">
			<div class="col-4 fw-bolder text-end">
				<label for="cmf-cmd-node-cmd">Command</label>
			</div>
			<div class="col-8">
				<input id="cmf-cmd-node-cmd" type="text" class="form-control" required>
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
	return modal;
}

function buildCLICommandModalCmd(node){
	let cmfSel = document.getElementById("cmf-cmd-node-select");
	let cmfCmd = document.getElementById("cmf-cmd-node-cmd");

	if(cmfSel.value === "custom"){
		cmfCmd.value = "";
	} else {
		cmfCmd.value = cmfSel.value;
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

function nodeUnlinkShortcut(node, target){
	cmdShortcut = target;
	openCmdModalLink(node, 1);
}
