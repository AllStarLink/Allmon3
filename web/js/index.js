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
// Global Variables
//
var monNodes = [ ];			// node(s) to monitor in Array
var nodeWebPollIntervals = new Map();
var nodePollErrors = new Map();
var nodeDescOverrides = new Map();
var loggedIn = false;
var tooltipTriggerList;
var tooltipList;

const max_poll_errors = 10;

// Hook on the documnet complete load
document.onreadystatechange = () => {
	if(document.readyState === "complete") {
		// was this called with #node[,node,node]
		if( location.hash !== "" ){
			nodeHash = location.hash.replace("#","");
			monNodes = nodeHash.split(",");
			startup();
		} else {
			getAPIJSON("master/node/listall")
				.then((result) => {
					monNodes = result;
					startup();
				});
		}
	}
};

// Things to do when the page loads
function startup(){
	uiConfigs();
	updateDashboardAreaStructure();
//	setInterval(checkLogonStatus, 900000);

	// Load the overrides
	getAPIJSON('master/ui/custom/overrides')
		.then((result) => {
			nodeDescOverrides = result;
		});

	// setup the initial polling intervals
	for(const n of monNodes){
		getAPIJSON(`master/node/${n}/config`)
			.then((result) => {
			const port = result["statport"];
			const wsproto = window.location.protocol.replace("http", "ws");
		    const wshost = window.location.host;
		    const wsuri = window.location.pathname.replace("index.html", "").concat(`ws/${port}`)
		    const wsurl = `${wsproto}//${wshost}${wsuri}`;
		    nodeWS = new WebSocket(wsurl);
			nodeStatus(n, nodeWS);	
		});
	}
}

// Get the configs
function uiConfigs(){
	customizeUI();
	createSidebarMenu();
//	checkLogonStatus();
}

// Update Customizations
async function customizeUI(){
	let customElements = await getAPIJSON("master/ui/custom/html");
	document.getElementById("navbar-midbar").innerHTML = customElements.HEADER_TITLE;
	if( customElements.HEADER_LOGO !== "" ){
		document.getElementById("header-banner-img").src = `img/${customElements.HEADER_LOGO}`;
	}
	document.getElementById("nav-home-button").href = customElements.HOME_BUTTON_URL;
};

// Update the dashboard
function updateDashboardAreaStructure(){
	const dashArea = document.getElementById("asl-statmon-dashboard-area");
	let dashUpdates = false;
	for(const n of monNodes){
		let daExists = document.getElementById(`asl-statmon-dashboard-${n}`);
		if(!daExists){
			let newNodeDiv = document.createElement("div");
			newNodeDiv.id = `asl-statmon-dashboard-${n}`;

			let newNodeDivHeader = document.createElement("div");
			newNodeDivHeader.id = `asl-statmon-dashboard-${n}-header`;
			newNodeDivHeader.innerHTML = nodeLineHeader(n, "")
			newNodeDiv.appendChild(newNodeDivHeader);

			let newNodeDivTxStat = document.createElement("div");
			newNodeDivTxStat.id = `asl-statmon-dashboard-${n}-txstat`;
			newNodeDiv.appendChild(newNodeDivTxStat);

			let newNodeDivConntable = document.createElement("div");
			newNodeDivConntable.id = `asl-statmon-dashboard-${n}-conntable`;
			newNodeDiv.appendChild(newNodeDivConntable);

			dashArea.appendChild(newNodeDiv);
			dashUpdates = true;
		}
	}

	if(dashUpdates){
		tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
		tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
	}
}

function nodeStatus(node, nodeWS){
    nodeWS.addEventListener("message", nodeEntryHandler);
    nodeWS.onclose = (event) => { nodeEntrySetError(node); }
    nodeWS.onerror = (event) => { nodeEntrySetError(node); }
}

// Each node
function nodeEntryHandler(WSResult){
	const nodeinfoHash = JSON.parse(WSResult.data);
	for( n in nodeinfoHash ){
		nodeEntry(n, nodeinfoHash[n]);
	}
}
function nodeEntry(nodeid, nodeinfo){
	const node = nodeinfo;
	const divTxStat = document.getElementById(`asl-statmon-dashboard-${nodeid}-txstat`);
	const divConntable = document.getElementById(`asl-statmon-dashboard-${nodeid}-conntable`);
	const headerDescSpan = document.getElementById(`asl-statmon-dashboard-${nodeid}-header-desc`);

	// update the description line
	if(nodeDescOverrides[nodeid]){
		node["DESC"] = nodeDescOverrides[nodeid];
	}
	headerDescSpan.innerHTML = `${nodeid} - ${node.DESC}`;

	// update the tx line
	if(node.RXKEYED === true && node.TXKEYED === true ){	
		divTxStat.innerHTML = "<div class=\"alert alert-warning am3-alert-keyed mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Local Source</div>";
	} else if( node.RXKEYED === true && node.TXEKEYED === false && node.TXEKEYED === false ){
		divTxStat.innerHTML = "<div class=\"alert alert-warning am3-alert-keyed mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Local Source</div>";
	} else if( node.CONNKEYED === true && node.TXKEYED === true && node.RXKEYED === false ){
		divTxStat.innerHTML = "<div class=\"alert alert-warning am3-alert-keyed mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Network Source</div>";
	} else if( node.TXKEYED === true && node.RXKEYED === false && node.CONNKEYED === false ){
		divTxStat.innerHTML = "<div class=\"alert alert-warning am3-alert-keyed mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Telemetry/Playback</div>";
	} else if( node.TXKEYED === false && node.RXKEYED === false && node.TXEKEYED === false && node.CONNKEYED === true ){
		divTxStat.innerHTML = `<div class="alert alert-warning am3-alert-keyed mx-3 py-0 nodetxline nodetxline-keyed">Transmit - Playback from Remote Node %{node.CONNKEYEDNODE}</div>`;
	} else {
		divTxStat.innerHTML = "<div class=\"alert alert-success am3-alert-idle mx-3 py-0 nodetxline nodetxline-unkeyed\">Transmit - Idle</div>";
	}

	// update the connection table	
	divConntable.innerHTML = nodeConnTable(node.CONNS, node.CONNKEYED, node.CONNKEYEDNODE);
}

function nodeEntrySetError(nodeid){
	const divHeader = document.getElementById(`asl-statmon-dashboard-${nodeid}-header`);
	const divTxStat = document.getElementById(`asl-statmon-dashboard-${nodeid}-txstat`);
	const divConntable = document.getElementById(`asl-statmon-dashboard-${nodeid}-conntable`);

	divHeader.innerHTML = nodeLineHeader(nodeid, "Unavailable Node")
	divTxStat.innerHTML = `<div class="alert alert-danger am3-alert-error mx-3 py-0"><b>Node Response Error - Node disabled<b> <button class="btn btn-danger" style="--bs-btn-padding-y: .25rem; --bs-btn-padding-x: .5rem; --bs-btn-font-size: .5rem;" onclick="reAddNode(${nodeid})">Reload Node</button></div>`;
	divConntable.innerHTML = "";

	const i = monNodes.indexOf(nodeid);
	if( i > -1 ){
		monNodes.splice(i, 1);
	}
}

// Draw/update the header row for a node
function nodeLineHeader(nodeNumber, nodeDescription){
	let nodeLineHeaderStr = `
        <div id="node-line-header-${nodeNumber}" class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center py-1 px-2 mt-1 mb-1 border-bottom nodeline-header rounded">
            <span id="asl-statmon-dashboard-${nodeNumber}-header-desc" class="align-middle">${nodeNumber} - ${nodeDescription}</span>
            <div class="btn-toolbar mb-2 mb-md-0">
                <div class="btn-group me-2">
                    <a id="btn-bubble-${nodeNumber}" class="btn btn-sm btn-outline-secondary node-bi"
						data-bs-toggle="tooltip" data-bs-title="View ASL Node Map for this node" data-bs-placement="bottom"
						href="http://stats.allstarlink.org/stats/${nodeNumber}/networkMap" target="_blank">
                        <svg class="node-bi flex-shrink-0" width="16" height="16" role="img" aria-label="Network Map ${nodeNumber}">
                            <use xlink:href="#bubble-chart"/>
                        </svg>
                    </a>
                    <a class="btn btn-sm btn-outline-secondary node-bi"
					data-bs-toggle="tooltip" data-bs-title="View ASL Stats for this node" data-bs-placement="bottom"
					href="http://stats.allstarlink.org/stats/${nodeNumber}/" target="_blank">
                        <svg class="node-bi flex-shrink-0" width="16" height="16" role="img" aria-label="Node Details ${nodeNumber}">
                            <use xlink:href="#details"/>
                        </svg>
                    </a>
                   <button class="btn btn-sm btn-outline-secondary node-bi" onclick="openCmdModalLink(${nodeNumber})"
						data-bs-toggle="tooltip" data-bs-title="Execute linking commands for this node" data-bs-placement="bottom">
                        <svg class="node-bi flex-shrink-0" width="16" height="16" role="img" aria-label="Manage Node ${nodeNumber}">
                            <use xlink:href="#link-45"/>
                        </svg>
                    </button>
                   <button class="btn btn-sm btn-outline-secondary node-bi" onclick="openCmdModalCLI(${nodeNumber})"
						data-bs-toggle="tooltip" data-bs-title="Execute system commands for this node" data-bs-placement="bottom">
                        <svg class="node-bi flex-shrink-0" width="16" height="16" role="img" aria-label="Manage Node ${nodeNumber}">
                            <use xlink:href="#settings"/>
                        </svg>
                   </button>
                </div>
            </div>
        </div>
`;
	return nodeLineHeaderStr;
}

// Draw/update the node tables
function nodeConnTable(conns, keyed, keyednode) {
	var tTop = `
<div class="px-3">
<table class="table table-sm table-responsive table-bordered table-hover">
<thead class="table-dark">
	<tr>
		<th scope="col">Node</th>
		<th scope="col">Description</th>
		<th scope="col">Last Recv</th>
		<th scope="col" class="d-none d-md-table-cell">Conn Time</th>
		<th scope="col" class="d-none d-md-table-cell">Direction</th>
		<th scope="col" class="d-none d-md-table-cell">Connect State</th>
		<th scope="col" class="d-none d-md-table-cell">Mode</th>
	</tr>
</thead>
<tbody class="table-group-divider">
`;

	var tBottom = `</tbody></table></div>`;
	var row = "";
	if(Object.keys(conns).length > 0){

		let nodesBySSU = [];
		for(let x in conns){
			nodesBySSU.push(x);
		}
		nodesBySSU.sort(function(a,b){
			let a_ssk = Number(conns[a]["SSK"]);
			let b_ssk = Number(conns[b]["SSK"]);

			// If both SSKs are -1, then sort by node # asc
			if( a_ssk == -1 && b_ssk == -1 ){
				let a_id = Number(a);
				let b_id = Number(b);

				if(Number.isNaN(a_id)){
					a_id = "99999999999";
				}

				if(Number.isNaN(b_id)){
					b_id = "99999999999";
				}

				if( a_id < b_id ){
					return -1;
				}
				if( a_id > b_id ){
					return 1;
				}
				return 0;
			}

			// If one SSK is -1, then SSK >0 always wins
			if( a_ssk == -1){
				return 1;
			}
			if( b_ssk == -1){
				return -1;
			}
	
			// Otherwise sort by conn time asc
			if( a_ssk < b_ssk ){
				return -1;
			}
			if( a_ssk > b_ssk ){
				return 1;
			}
			return 0;
		});

		for(const x of nodesBySSU){
			let c = conns[x];
			let lastXmit = "";
			if(c['SSK'] == -1){
				lastXmit = "Never";
			} else {
				let t = c['SSU'];
				if( t > -1 ){
					lastXmit = toHMS(t);
				} else {
					lastXmit = "Never";
				}
			}

			var rowclass = "node-conn-nokey";
			if( keyed === true && x == keyednode ){
				rowclass = "node-conn-keyed";
				lastXmit = "00:00:00";
			}

			row = row.concat(`
			<tr class="${rowclass}" onclick="nodeCmdShortcut(${x})">
				<th scope="row">${x}</td>
				<td>${c.DESC}</td>
				<td>${lastXmit}</td>
				<td class="d-none d-md-table-cell">${c.CTIME}</td>
				<td class="d-none d-md-table-cell">${c.DIR}</td>
				<td class="d-none d-md-table-cell">${c.CSTATE}</td>
				<td class="d-none d-md-table-cell">${c.MODE}</td>
			</tr>`);
		}
	} else {
		row = "<tr><td colspan=7>No Conenctions - Repeat Only</td></tr>";
	}

	return tTop + row + tBottom;
}

//
// Monitor and Address Hash/Navagation elements
//
function changedLocationHash(){
	document.getElementById("asl-statmon-dashboard-area").innerHTML = "";

	let navbutton = document.getElementById("collapse-navbar-button");
	if( navbutton.classList.contains("collapsed") == false ){
		let menu = document.getElementById("sidebarMenu");
		menu.classList.remove("show");
		navbutton.classList.add("collapsed");
	}

	if( location.hash === "" || location.hash === "#" ){
		getAPIJSON("master/node/listall")
		.then((result) => {
			changeNodeList(result);
		});
	} else {
		nodeHash = location.hash.replace("#","");
		changeNodeList(nodeHash.split(","));
	}
}

function changeNodeList(nodeList){
	monNodes = nodeList;
	// redraw the dashboard page area
	updateDashboardAreaStructure();
	tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
	tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

    // setup the polling intervals
    for(const n of monNodes){
        pollNode(n);
    }
}

window.onhashchange = changedLocationHash;

//
// Handle logins
//

var originalLoginBox = "";

async function doLogin(){
	let loginResponse = await postAPIForm("api/session-handler.php", new FormData(document.getElementById("loginBox")));
	originalLoginBox = document.getElementById("loginModal").innerHTML;
	if( loginResponse["SUCCESS"] ){
		document.getElementById("login-modal-body").innerHTML = `
<div class="login-form-success">
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-square-fill" viewBox="0 0 16 16">
  <path d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2zm10.03 4.97a.75.75 0 0 1 .011 1.05l-3.992 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.75.75 0 0 1 1.08-.022z"/>
</svg>
Login Successful
</div>
`;
		document.getElementById("login-modal-footer").innerHTML = `
	<button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="clearLogin()">OK</button>
`;
		loggedIn = true;
	} else {
		document.getElementById("loginModalLabel").innerHTML = "Login Failed";
		document.getElementById("loginModalLabel").classList.add("login-form-failure-header");
	}	
	checkLogonStatus();
}

//
// Reset Login Box
//
function clearLogin(){
	if( ! originalLoginBox === "" ){
		document.getElementById("loginModal").innerHTML = originalLoginBox;	
		checkLogonStatus();
	}
}

//
// Handle Logout
//

var originalLogoutBox = "";

async function doLogout(){
    let logoutResponse = await postAPIForm("api/session-handler.php", new FormData(document.getElementById("logoutBox")));
	originalLogoutBox = document.getElementById("logoutModal").innerHTML;
	if( logoutResponse["SUCCESS"] ){
		document.getElementById("logout-modal-body").innerHTML = `
<div class="login-form-success">
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-square-fill" viewBox="0 0 16 16">
  <path d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2zm10.03 4.97a.75.75 0 0 1 .011 1.05l-3.992 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.75.75 0 0 1 1.08-.022z"/>
</svg>
Logout Successful
</div>
`;
		document.getElementById("logout-modal-footer").innerHTML = `
	<button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="clearLogout()">OK</button>
`;
		loggedIn= false;
	} else {
		document.getElementById("logout-modal-body").innerHTML = res;
	}
	checkLogonStatus();
}

function clearLogout(){
	if( ! originalLogoutBox === "" ){
		document.getElementById("logoutModal").innerHTML = originalLogoutBox;
		checkLogonStatus();
	}
}



