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
// Global Variables
//
var voterNodes = [];
var votermons = {};

// Hook page show
window.addEventListener('pageshow', pageLoad);

// Hook on the documnet complete load
function pageLoad(){
     // was this called with #node[,node,node]
     if( location.hash !== "" ){
         const nodeHash = location.hash.replace("#","");
         for (const n of nodeHash.split(",")) {
             voterNodes.push(parseInt(n));
         }
         startup();
     } else {
         alert("At least one node ID must be passed as voter.html#NODE or voter.html#NODE1,NODE2");
     }
     window.onhashchange = changedLocationHash;
}

// Things to do when the page loads
function startup(){
    uiConfigs();
    setInterval(checkLogonStatus, 900000);

    // Pre-create all panels in URL order before async API calls so display
    // order always matches the hash regardless of response timing
    for (const n of voterNodes) {
        drawVoterPanelFamework(n, "Loading...");
    }

    for (const n of voterNodes) {
        getAPIJSON(`master/node/${n}/voter`)
            .then((result) => {
                if(result){
                    document.getElementById(`asl-votermon-${n}-header-desc`).innerHTML = `${n} - ${result["votertitle"]}`;
                    getVotes(n, result["voterport"]);
                } else {
                    document.getElementById(`asl-votermon-${n}-header-desc`).innerHTML = `${n} - ERROR`;
                    displayError(n, "Could not retrieve voter configuration from API");
                }
            });
    }
}

// Get the configs
function uiConfigs(){
    customizeUI();
    createSidebarMenu();
    checkLogonStatus();
}

// Update Customizations
async function customizeUI(){
    let customElements = await getAPIJSON("master/ui/custom/html");
    document.getElementById("navbar-midbar").innerHTML = customElements.HEADER_TITLE;
    document.title = customElements.HEADER_TITLE;
    if( customElements.HEADER_LOGO !== "" ){
        document.getElementById("header-banner-img").src = `img/${customElements.HEADER_LOGO}`;
        document.getElementById("header-banner-img").alt = customElements.HEADER_TITLE;
    }

    let currp = window.location.href.split("/").at(-1);
    let newp = customElements.HOME_BUTTON_URL;
    if( currp === newp ){
        document.getElementById("nav-home-button").setAttribute("onclick","window.location.reload()");
    }
    document.getElementById("nav-home-button").href=newp;
}

//
// Monitor and Address Hash/Navagation elements
//
function changedLocationHash(){
    document.getElementById("asl-votermon-area").innerHTML = "";
    window.location.reload(true);
}



//
// Voter displays
//
function drawVoterPanelFamework(node, title){
    let votermonArea = document.getElementById("asl-votermon-area");
    let nodeContainer = document.createElement("div");
    nodeContainer.id = `asl-votermon-node-${node}`;
    nodeContainer.innerHTML = `
<div id="node-header-${node}" class="row d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center py-1 px-2 mt-1 mb-1 border-bottom nodeline-header rounded">
    <div id="asl-votermon-${node}-header-desc" class="col align-middle">${node} - ${title}</div>
	<div class="col-md-auto align-middle">&nbsp</div>
    <div class="col col-lg-2 btn-toolbar mb-2 mb-md-0">
        <div class="btn-group me-2">
            <button class="btn btn-sm btn-outline-secondary node-bi" onclick="openCmdModalCLI(${node})"
                data-bs-toggle="tooltip" data-bs-title="Execute system commands for this node" data-bs-placement="bottom">
                <svg class="node-bi flex-shrink-0" width="16" height="16" role="img" aria-label="Manage Node ${node}">
                    <use xlink:href="#settings"/>
                </svg>
            </button>
        </div>
    </div>
</div>
<div id="asl-votermon-${node}-data" class="px-2"></div>`;
    votermonArea.appendChild(nodeContainer);
    tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
}

function getVotes(node, voterport){
    const wsproto = window.location.protocol.replace("http", "ws");
    const wshost = window.location.host;
    const wsuri = window.location.pathname.replace("voter.html", `/ws/${voterport}`)
    const wsurl = `${wsproto}//${wshost}${wsuri}`;
    votermons[node] = new WebSocket(wsurl);
    votermons[node].addEventListener("message", (event) => displayResults(node, event));
    votermons[node].onclose = (event) => {
        document.getElementById(`asl-votermon-${node}-data`).innerHTML = `
            <div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
                The websocket could not be contacted or unexpectedly closed. Check the server config.
            </div>
        `;

    }
    votermons[node].onerror = (event) => {
        document.getElementById(`asl-votermon-${node}-data`).innerHTML = `
            <div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
                The websocket had an error. Check the server config.
            </div>
        `;

    }

}

function displayResults(node, voterEvent){
    if(voterEvent.returnValue){
        document.getElementById(`asl-votermon-${node}-data`).innerHTML = voterEvent.data;
    } else {
        document.getElementById(`asl-votermon-${node}-data`).innerHTML = `
            <div class="p-3 my-2 text-warning-emphasis bg-warning-subtle border border-warning-subtle rounded-3">
                No voter data available from system
            </div>
        `;
    }
}

function displayError(node, errormsg){
    const voterDataArea = document.getElementById(`asl-votermon-node-${node}`);
    if(voterDataArea){
        voterDataArea.innerHTML = `
            <div class="p-3 my-2 text-danger-emphasis bg-danger-subtle border border-danger-subtle rounded-3">
                <p>The API returned an error:</p>
                <pre>${errormsg}</pre>
            </div>
        `;
    } else {
        document.getElementById("asl-votermon-area").innerHTML += `
            <div class="p-3 my-2 text-danger-emphasis bg-danger-subtle border border-danger-subtle rounded-3">
                <p>Node ${node}: The API returned an error:</p>
                <pre>${errormsg}</pre>
            </div>
        `;
    }
}
