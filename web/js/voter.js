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
var nodePollErrors = 0;

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

async function getVotes(){
	let errormsg = "";
	let response = await fetch(`api/asl-votermon.php?node=${node}`);
	if(response.ok){
		const result = await response.json();
        if(result["ERROR"]){
            errormsg = result["ERROR"];
            nodePollErrors = nodePollErrors + 1;
        } else {
            nodePollErrors = 0;
            displayResults(result);
        }
    } else {
        console.log(response);
		errormsg = response;
        nodePollErrors =  nodePollErrors + 1;
    }

    if( nodePollErrors < max_poll_errors ){
		setTimeout(getVotes, nodeVoterPollInterval );
    } else {
    	displayError(errormsg);
    }
}

function displayResults(voters){
	const voterDataArea = document.getElementById(`asl-votermon-${node}-data`);
	let voterData = "";
	if(Object.keys(voters).length > 0){
		for(let v in voters){

			// RSSI
			let rssi = voters[v]["RSSI"];
			let rssiPct = 0;
			if( rssi == 255 ){
				rssiPct = 100;
			} else {
				// display the bar as a relative size between 10% and 100% - 90/255 ~ .35
				rssiPct = rssi * .35 + 10;
			}

			// Bar Color
			let barColor = null;
			if( voters[v]["VOTED"] === null ){
				barColor = "info";
			} else if( voters[v]["VOTED"] === v  ) {
				barColor = "success";
			} else {
				barColor = "primary";
			}

			// Draw Data
			voterData = voterData.concat(`
				<div class="row d-flex align-items-center">
	                <div class="col-2 text-end">
	                    <b>${v}</b>
	                </div>
	                <div class="col-8">
	                    <div class="progress" role="progressbar" aria-valuenow="${rssiPct}" aria-valuemin="0" aria-valuemax="100">
	                          <div class="progress-bar progress-bar-striped bg-${barColor}" style="width: ${rssiPct}%">${rssi}</div>
	                    </div>
	                </div>
	            </div>
			`);
		}
		voterDataArea.innerHTML = voterData.concat(`
			<div class="row d-flex align-items-center">
				<div class="col-2 text-end">
					<div class="spinner-grow spinner-grow-sm" style="animation-duration: .5s" role="status">
						<span class="visually-hidden">Loading...</span>	
					</div>
				</div>
			</div>`);
	} else {
		voterData.innerHTML = `
			<div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
				No voter data available from system
			</div>
		`;
	}
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
