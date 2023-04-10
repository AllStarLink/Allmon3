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

// Generic AJAX functions
async function getAPIJSON(url){
	let response = await fetch(url);
	if(response.ok){
		return await response.json();
	} else {
		console.log(`getAPIJSON error status ${response.status} ${response.statusText}`);
		return false;
	}
}

async function postAPIForm(url, form){
	const formData = new URLSearchParams(form);
	let response = await fetch(url, { method: "post", body: formData });
	if(response.ok){
		return await response.json();
	} else {
		console.log(`postAPIForm error status ${response.stats} ${response.statusText}`);
		return false;
	}

}


// Check Logon Status
async function checkLogonStatus(){
	let sessionStatus = await getAPIJSON("api/session-check.php")
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


// Generate and Draw Menus
async function createSidebarMenu(){
	let customMenu = await getAPIJSON("api/uiconfig.php?e=custmenu");
	let navMenu = `<div class="vstack d-grid gap-2 col-9 mx-auto">`;

	if(!customMenu["ERROR"]){
		for(let dd of Object.keys(customMenu)){
			if(customMenu[dd]["type"] === "menu"){
				navMenu = navMenu.concat(`
					<div class="btn-group">
						<button class="btn btn-secondary dropdown-toggle" data-bs-toggle="dropdown">${dd}</button>
						<div class="dropdown-menu">`);
					for(let ml of Object.keys(customMenu[dd])){
						if( ml !== "type" ){
							if(customMenu[dd][ml].match(/^[0-9]+$/)){
								let nn = customMenu[dd][ml];
								navMenu = navMenu.concat(`<a class="dropdown-item" href="#${nn}">${ml}</a>`);
							} else {
								let href = customMenu[dd][ml];
								navMenu = navMenu.concat(`<a class="dropdown-item" href="${href}">${ml}</a>`);
							}
						}
					}
				navMenu = navMenu.concat(`
						</div>
					</div>`);
			} else if(customMenu[dd]["type"] === "single"){
				for(let ml of Object.keys(customMenu[dd])){
					if( ml !== "type" ){
						let href = customMenu[dd][ml];
						navMenu = navMenu.concat(`
							<div class="btn-group">
								<a href="${href}" class="btn btn-secondary" role="button">${ml}</a>
							</div>`);
					}
				}
			}
		}
	} else {
		let allNodes = await getAPIJSON("api/uiconfig.php?e=nodelist");
		for(const n of allNodes){
        navMenu = navMenu.concat(`
			<div class="btn-group">
				<a href="#" class="btn btn-secondary" role="button" onclick="changeNodeListSingle(${n})">${n}</a>
			</div>`);
		}
	}	
	
	navMenu = navMenu.concat(`</div>`); // closes vstack
	document.getElementById("asl-node-navigation").innerHTML = navMenu;
}
