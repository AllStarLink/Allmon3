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
var node = 0;
var nodeTitle = "";
var nodeVoterPollInterval = 1000;
var nodePass = "";
var nodePollErrors = 0;
var votermon = null;

const max_poll_errors = 10;

// Hook on the documnet complete load
document.onreadystatechange = () => {
	if(document.readyState === "complete") {
		// was this called with #node[,node,node]
		if( location.hash !== "" ){
			node = location.hash.replace("#","");
			startup();
		} else {
			alert("One node ID must be passed as voter.html#NODE");
		}
	}
};

// Things to do when the page loads
function startup(){
	uiConfigs();
	getAPIJSON(`api/uiconfig.php?e=voter&n=${node}`).then((result) => {
    	if(result["SUCCESS"]){
			nodeVoterPollInterval = Number(result["SUCCESS"]["POLLTIME"]);
			nodePass = result["SUCCESS"]["PASS"];
			drawVoterPanelFamework(result["SUCCESS"]["TITLE"]);
			getVotes();
		} else {
			drawVoterPanelFamework("ERROR");
			displayError(result["ERROR"]);			
		}
	});
}

// Get the configs
function uiConfigs(){
	customizeUI();
	createSidebarMenu();
}

// Update Customizations
async function customizeUI(){
	let customElements = await getAPIJSON("api/uiconfig.php?e=customize");
	document.getElementById("navbar-midbar").innerHTML = customElements.HEADER_TITLE;
	if( customElements.HEADER_LOGO !== "" ){
		document.getElementById("header-banner-img").src = `img/${customElements.HEADER_LOGO}`;
	}
	document.getElementById("nav-home-button").href = customElements.HOME_BUTTON_URL;
};

//
// Monitor and Address Hash/Navagation elements
//
function changedLocationHash(){
	document.getElementById("asl-votermon-area").innerHTML = "";

	let navbutton = document.getElementById("collapse-navbar-button");
	if( navbutton.classList.contains("collapsed") == false ){
		let menu = document.getElementById("sidebarMenu");
		menu.classList.remove("show");
		navbutton.classList.add("collapsed");
	}

	if( location.hash === "" || location.hash === "#" ){
		alert("One node must be specified as voter.html#NODE")
	} else {
		node = location.hash.replace("#","");
	}
}

window.onhashchange = changedLocationHash;


//
// Voter displays
//
function drawVoterPanelFamework(title){
	let votermonArea = document.getElementById("asl-votermon-area");
	let votermonAreaHeader = `
<div id="node-header-${node}" class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center p
y-1 px-2 mt-1 mb-1 border-bottom nodeline-header rounded">
	<span id="asl-votermon-${node}-header-desc" class="align-middle">${node} - ${title}</span>
</div>`;
	let votermonAreaData = `<div id="asl-votermon-${node}-data" class="px-2">`
	votermonArea.innerHTML = votermonAreaHeader + votermonAreaData;
}

function getVotes(){
	const wsproto = window.location.protocol.replace("http", "ws");
	const wshost = window.location.host;
	const wsuri = window.location.pathname.replace("voter.html", `/ws/voter/${node}`)
	const wsurl = `${wsproto}//${wshost}${wsuri}`;
	votermon = new WebSocket(wsurl);
	votermon.addEventListener("message", displayResults);
	votermon.onopen = (event) => {
		getNextVoterData();
	}
	votermon.onclose = (event) => {
		document.getElementById(`asl-votermon-${node}-data`).innerHTML = `
            <div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
            	The websocket could not be contacted or unexpectedly closed. Check the server config.
            </div>
        `;

	}
	votermon.onerror = (event) => {
		document.getElementById(`asl-votermon-${node}-data`).innerHTML = `
            <div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
            	The websocket had an error. Check the server config.
            </div>
        `;

	}

}

function getNextVoterData(){
	votermon.send(nodePass);
}

function displayResults(voterEvent){
	if(voterEvent.returnValue){
		document.getElementById(`asl-votermon-${node}-data`).innerHTML = voterEvent.data;
	} else {
		document.getElementById(`asl-votermon-${node}-data`).innerHTML = `
			<div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
				No voter data available from system
			</div>
		`;
	}
	setTimeout(getNextVoterData, nodeVoterPollInterval);
}

function displayError(errormsg){
	const voterDataArea = document.getElementById(`asl-votermon-area`);
	voterDataArea.innerHTML = `
		<div class="p-3 my-2 text-danger-emphasis bg-danger-subtle border border-danger-subtle rounded-3">
			<p>The API returned an error:</p>
			<pre>${errormsg}</pre>
		</div>
	`;
}
