//
// Global Variables
//
var updateStatusDashboardIntervalID = 0;	// ID for the setInterval() of the dashboard
var monNodes = [ ];			// node(s) to monitor in Array

// Things to do when the page loads
window.addEventListener("load", function(){
	uiConfigs();
	updateStatusDashboardIntervalID = setInterval(updateStatusDashboard, 1000);
});

// Generic AJAX function
function XHRRequest(label, url, action){
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function () {
		if( this.readyState == 4 && this.status == 200 ){
			action(this.responseText);
		} else if( this.readyState == 4 && this.status != 200 ){
			console.log("Failed to execute " + label)
		}

	}
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}	

// Get the configs
function uiConfigs(){
	XHRRequest("drawMenu", "api/uiconfig.php?e=nodelist", drawMenu);
};

// Update menu
function drawMenu(menulist){
	monNodes = JSON.parse(menulist);
	li = "";
	for(const n of monNodes){
		li = li.concat(`<li class="nav-item">
						<a href="#" onclick="changeNodeListSingle(${n})" class="nav-link">
							<svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img"><use xlink:href="#node"/></svg>
                           	${n} 
						</a>
                    </li>`);
	}
	document.getElementById("asl-node-navigation").innerHTML = li;
}

// Update the dashboard
function updateStatusDashboard(){
	var dashArea = document.getElementById("asl-statmon-dashboard-area");
	var monNodeDivs = "";
	for(const n of monNodes){
		var daExists = document.getElementById(`asl-statmon-dashboard-${n}`);
		if(!daExists){
			const newDiv = document.createElement("div");
			newDiv.id = `asl-statmon-dashboard-${n}`;
			dashArea.appendChild(newDiv);
		}
	}
	for(const n of monNodes){
		var xmlhttp = new XMLHttpRequest();
		var url = `api/asl-statmon.php?node=${n}`;
		xmlhttp.onreadystatechange = function () {
			if( this.readyState == 4 && this.status == 200 ){
				nodeEntry(n, this.responseText);
			} else if( this.readyState == 4 && this.status != 200 ){
				console.log("Failed to get dashboard update")
			}
	
		}
		xmlhttp.open("GET", url, true);
		xmlhttp.send();
	}
};

// Each node
function nodeEntry(nodeid, nodeinfo){
	var dashArea = document.getElementById(`asl-statmon-dashboard-${nodeid}`);
	const node = JSON.parse(nodeinfo);

	if(node.ERROR){
		window.alert(`SERVER ERROR: NODE=${nodeid}\n\n${node.ERROR}\n\nYou must fix the error and reload this page`);
		window.clearInterval(updateStatusDashboardIntervalID);
		return false;
	}

	var nodeTxLine = "";
	if(node.RXKEYED === true && node.TXKEYED === true){	
		nodeTxLine = "<div class=\"alert alert-danger mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Local Source</div>";
	} else if( node.CONNKEYED === true && node.TXKEYED === true && node.RXKEYED === false ){
		nodeTxLine = "<div class=\"alert alert-danger mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Network Source</div>";
	} else if( node.TXKEYED === true && node.RXKEYED === false && node.CONNKEYED === false ){
		 nodeTxLine = "<div class=\"alert alert-danger mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Telemetry/Playback</div>";
	} else {
		nodeTxLine = "<div class=\"alert alert-success mx-3 py-0 nodetxline nodetxline-unkeyed\">Transmit - Idle</div>";
	}

	dashArea.innerHTML = nodeLineHeader(node.ME, node.DESC) + nodeTxLine + 
		nodeConnTable(node.CONNS, node.CONNKEYED, node.CONNKEYEDNODE);

	// enable the tooltips
	// const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
	//const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

};


// Draw/update the header row for a node
function nodeLineHeader(nodeNumber, nodeDescription){
	var nodeLineHeaderStr = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center py-1 px-2 mt-1 mb-3 border-bottom shadow nodeline-header">
            <span class="align-middle">${nodeNumber} - ${nodeDescription}</span>
            <div class="btn-toolbar mb-2 mb-md-0">
                <div class="btn-group me-2">
                    <a id="btn-bubble-${nodeNumber}" onmouseover="dispToolTip(this)" class="btn btn-sm btn-outline-secondary"
						href="http://stats.allstarlink.org/stats/${nodeNumber}/networkMap" target="_blank">
                        <svg class="bi flex-shrink-0" width="16" height="16" role="img" aria-label="Network Map ${nodeNumber}">
                            <use xlink:href="#bubble-chart"/>
                        </svg>
                    </a>
                    <a class="btn btn-sm btn-outline-secondary"
					href="http://stats.allstarlink.org/stats/${nodeNumber}/" target="_blank">
                        <svg class="bi flex-shrink-0" width="16" height="16" role="img" aria-label="Node Details ${nodeNumber}">
                            <use xlink:href="#details"/>
                        </svg>
                    </a>
                    <a class="btn btn-sm btn-outline-secondary"
						href="#">
                        <svg class="bi flex-shrink-0" width="16" height="16" role="img" aria-label="Manage Node ${nodeNumber}">
                            <use xlink:href="#settings"/>
                        </svg>
                    </a>
                </div>
            </div>
        </div>
`;
	return nodeLineHeaderStr;
};

// Draw/update the node tables
function nodeConnTable(conns, keyed, keyednode) {
	var tTop = `
<table class="table table-responsive table-bordered table-hover">
<thead class="table-dark">
	<tr>
		<th scope="col">Node</th>
		<th scope="col">Description</th>
		<th scope="col">Connected Time</th>
		<th scope="col">Last Received</th>
		<th scope="col">Direction</th>
		<th scope="col">Connect State</th>
		<th scope="col">Mode</th>
	</tr>
</thead>
<tbody class="table-group-divider">
`;

	var tBottom = `</tbody></table>`;
	var row = "";
	if(Object.keys(conns).length > 0){
		for(var c in conns){
			if(c['SSK'] == -1){
				var lastXmit = "Never";
			} else {
				t = conns[c]['SSK'];
				if( t > -1 ){
					const date = new Date(null);
					date.setSeconds(t);
					var lastXmit = date.toISOString().slice(11,19);
				} else {
					var lastXmit = "Never";
				}
			}

			var rowclass = "node-conn-nokey";
			if( keyed === true && c == keyednode ){
				rowclass = "node-conn-keyed";
			}

			row = row.concat(`
			<tr class="${rowclass}">
				<th scope="row">${c}</td>
				<td>${conns[c].DESC}</td>
				<td>${conns[c].CTIME}</td>
				<td>${lastXmit}</td>
				<td>${conns[c].DIR}</td>
				<td>${conns[c].CSTATE}</td>
				<td>${conns[c].MODE}</td>
			</tr>`);
		}
	} else {
		row = "<tr><td colspan=7>No Conenctions - Repeat Only</td></tr>";
	}

	return tTop + row + tBottom;
};

//
// Change the list of nodes to the provided []
//
function changeNodeList(newNodeList){
	window.clearInterval(updateStatusDashboardIntervalID);
	document.getElementById("asl-statmon-dashboard-area").innerHTML = "";
	monNodes = newNodeList;
	updateStatusDashboardIntervalID = setInterval(updateStatusDashboard, 1000);
}

//
// Wapper for changeNodeList to take a single integer
function changeNodeListSingle(newNode){
	changeNodeList([newNode]);
}
