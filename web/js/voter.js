/*
 * Copyright(C) 2023-2024 AllStarLink
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
var nodeVMonPort = 0;
var votermon = null;

// Hook page show
window.addEventListener('pageshow', pageLoad);

// Hook on the documnet complete load
function pageLoad(){
     // was this called with #node[,node,node]
     if( location.hash !== "" ){
         node = location.hash.replace("#","");
         startup();
     } else {
         alert("One node ID must be passed as voter.html#NODE");
     }
     window.onhashchange = changedLocationHash;
}

// Things to do when the page loads
function startup(){
    uiConfigs();
    setInterval(checkLogonStatus, 900000);
    getAPIJSON(`master/node/${node}/voter`)
        .then((result) => {
            if(result){
                nodeVMonPort = result["voterport"];
                drawVoterPanelFamework(result["votertitle"]);
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
function drawVoterPanelFamework(title){
    let votermonArea = document.getElementById("asl-votermon-area");
    let votermonAreaHeader = `
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
</div>`;
    let votermonAreaData = `<div id="asl-votermon-${node}-data" class="px-2">`
    votermonArea.innerHTML = votermonAreaHeader + votermonAreaData;
    tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
}

function getVotes(){
    const wsproto = window.location.protocol.replace("http", "ws");
    const wshost = window.location.host;
    const wsuri = window.location.pathname.replace("voter.html", `/ws/${nodeVMonPort}`)
    const wsurl = `${wsproto}//${wshost}${wsuri}`;
    votermon = new WebSocket(wsurl);
    votermon.addEventListener("message", displayResults);
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
