window.addEventListener("load", function(){
	setInterval(updateStatusDashboard, 10000);
});

updateStatusDashboard();

function updateStatusDashboard(){
	var xmlhttp = new XMLHttpRequest();
	var url = "api/asl-statmon.php";
	xmlhttp.onreadystatechange = function () {
		if( this.readyState == 4 && this.status == 200 ){
//		document.getElementById("statmon").innerHTML = this.responseText;
		nodeEntry(this.responseText);
		} else if( this.readyState == 4 && this.status != 200 ){
			console.log("Failed to get dashboard update")
		}

	}
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
};

function nodeEntry(nodeinfo){
	dashArea = document.getElementById("asl-statmon-dashboard-area");
	node = JSON.parse(nodeinfo);

	var nodeTxLine = ""	
	if(node.RXKEYED === true && node.TXKEYED === true && node.TXEKEYED === false){	
		nodeTxLine = "<div class=\"alert alert-danger mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Local Signal</div>";
	} else if( node.RXKEYED === false && node.TXKEYED === false && node.TXEKEYED === true ){
		nodeTxLine = "<div class=\"alert alert-danger mx-3 py-0 nodetxline nodetxline-keyed\">Transmit - Network Signal</div>";
	} else {
		nodeTxLine = "<div class=\"alert alert-success mx-3 py-0 nodetxline nodetxline-unkeyed\">Transmit - Idle</div>";
	}

	dashArea.innerHTML = nodeLineHeader(node.ME, node.DESC) + nodeTxLine + nodeConnTable(node.Conns);

	// enable the tooltips
	const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
	console.log(...tooltipTriggerList);
	const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
};


function nodeLineHeader(nodeNumber, nodeDescription){
	var nodeLineHeaderStr = `
        <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center py-2 px-2 mt-1 mb-3 border-bottom shadow nodeline-header">
            <h1 class="h3">${nodeNumber} - ${nodeDescription}</h3>
            <div class="btn-toolbar mb-2 mb-md-0">
                <div class="btn-group me-2">
                    <a class="btn btn-sm btn-outline-secondary"
						data-bs-toggle="tooltip" data-bs-placement="left"
						data-bs-custom-class="nodeline-tooltip" 
						data-bs-title="View this node with the ASL Bubble Map"
						href="http://stats.allstarlink.org/stats/${nodeNumber}/networkMap" target="_blank">
                        <svg class="bi flex-shrink-0" width="24" height="24" role="img" aria-label="Network Map ${nodeNumber}">
                            <use xlink:href="#bubble-chart"/>
                        </svg>
                    </a>
                    <a class="btn btn-sm btn-outline-secondary"
					data-bs-toggle="tooltip" data-bs-placement="left"
					data-bs-custom-class="nodeline-tooltip" 
					data-bs-title="View this node with at the ASL Node Info site"
					href="http://stats.allstarlink.org/stats/${nodeNumber}/" target="_blank">
                        <svg class="bi flex-shrink-0" width="24" height="24" role="img" aria-label="Node Details ${nodeNumber}">
                            <use xlink:href="#details"/>
                        </svg>
                    </a>
                    <a class="btn btn-sm btn-outline-secondary"
						data-bs-toggle="tooltip" data-bs-placement="left"
						data-bs-custom-class="nodeline-tooltip" 
						data-bs-title="Manage this node"
						href="#">
                        <svg class="bi flex-shrink-0" width="24" height="24" role="img" aria-label="Manage Node ${nodeNumber}">
                            <use xlink:href="#settings"/>
                        </svg>
                    </a>
                </div>
            </div>
        </div>
`;
	return nodeLineHeaderStr;
};

function nodeConnTable(conns) {
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
					var seconds = Math.round(t % 60);
					t = Math.floor(t / 60);
					var minutes = Math.round(t % 60);
					t = Math.floor(t / 60);
					var hours = Math.round(t % 24);
					var days = Math.floor(t / 24);
					if( days > 0 ){
						var lastXmit = `${days} days ${hours}:${minutes}:${seconds}`;
					} else {
						var lastXmit = `${hours}:${minutes}:${seconds}`;
					}
				} else {
					var lastXmit = "Never";
				}
			}
		} 

		row = row.concat(`
			<tr>
				<th scope="row">${c}</td>
				<td>${conns[c].DESC}</td>
				<td>${conns[c].CTIME}</td>
				<td>${lastXmit}</td>
				<td>${conns[c].DIR}</td>
				<td>${conns[c].CSTATE}</td>
				<td>${conns[c].MODE}</td>
			</tr>`);

	} else {
		row = "<tr><td colspan=7>No Conenctions - Repeat Only</td></tr>";
	}

	return tTop + row + tBottom;
};
