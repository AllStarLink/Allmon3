window.addEventListener("load", function(){
	setInterval(updateStatusDashboard, 1000);
});

function updateStatusDashboard(){
	var xmlhttp = new XMLHttpRequest();
	var url = "api/asl-statmon.php";
	xmlhttp.onreadystatechange = function () {
		if( this.readyState == 4 && this.status == 200 ){
			document.getElementById("statmon").innerHTML = this.responseText;
		} else if( this.readyState == 4 && this.status != 200 ){
			console.log("Failed to get dashboard update")
		}

	}
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}
