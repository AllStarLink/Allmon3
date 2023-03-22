/*
 * Copyright(C) 2023 AllStarLink
 * Allmon3 and all components are Licensed under the AGPLv3
 * see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
 *
 * This excludes the use of the Bootstrap libraries which are licensed
 * separately.
 *
 */

// Returns the value of the specified HTTP GET parameter
function findGetParameter(parameterName) {
	var result = null,
	tmp = [];
	location.search
		.substr(1)
		.split("&")
		.forEach(function (item) {
		  tmp = item.split("=");
		  if (tmp[0] === parameterName) result = decodeURIComponent(tmp[1]);
		});
	return result;
}

// Convert elapsed seconds to HH:MM:SS
function toHMS(totalSeconds) {
  const totalMinutes = Math.floor(totalSeconds / 60);
  const zeroPad = (num) => String(num).padStart(2,'0');
  const seconds = totalSeconds % 60;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${zeroPad(hours)}:${zeroPad(minutes)}:${zeroPad(seconds)}`;
}

// Generic AJAX function
function XHRRequest(label, method, url, action){
	let xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function () {
		if( this.readyState == 4 && this.status == 200 ){
			action(this.responseText);
		} else if( this.readyState == 4 && this.status != 200 ){
			console.log("Failed to execute " + label)
		}

	}
	xmlhttp.open(method, url, true);
	xmlhttp.send();
}


// Check Logon Status
function checkLogonStatus(){
	XHRRequest("checkLogonStatus", "GET", "api/session-check.php", logonButtonToggle);	
}

// Draw the logon/logout buttons
function logonButtonToggle(res){
	let sessionStatus = JSON.parse(res);
	let loginRegion = document.getElementById("login-out-region");
	if(sessionStatus["SUCCESS"]){
		loginRegion.innerHTML = `
			<div class="d-grid gap-2 col-6 mx-auto">
				<button type="button" class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#logoutModal">
					Logout
				</button>
			</div>
		`;
		loggedIn = true;
	} 
	else if(sessionStatus["SECURITY"]){
		loginRegion.innerHTML = `
			<div class="d-grid gap-2 col-6 mx-auto">
				<button type="button" class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#loginModal">
					Login
				</button>	
			</div>
		`;
		loggedIn = false;
	} else {
		loginRegion.innerHTML = "ERROR";
		loggedIn = false;
	}
}
