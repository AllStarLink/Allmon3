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
var node = 0
var nodeVoterPollInterval = 1000;

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
	drawVoterPanelFamework();
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

function drawVoterPanelFamework(){
	let votermonArea = document.getElementById("asl-votermon-area");
	let votermonAreaHeader = `
<div id="node-header-${node}" class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center p
y-1 px-2 mt-1 mb-1 border-bottom nodeline-header rounded">
	<span id="asl-votermon-${node}-header-desc" class="align-middle">${node}</span>
</div>`;
	let votermonAreaData = `<div id="asl-votermon-${node}-data" class="px-3">`
	votermonArea.innerHTML = votermonAreaHeader + votermonAreaData;
}
