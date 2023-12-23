/*
 * Copyright(C) 2023-2024 AllStarLink
 * Allmon3 and all components are Licensed under the AGPLv3
 * see https://raw.githubusercontent.com/AllStarLink/Allmon3/develop/LICENSE
 *
 * This excludes the use of the Bootstrap libraries which are licensed
 * separately.
 *
 */

// Convert elapsed seconds to HH:MM:SS
function toHMS(totalSeconds) {
  const totalMinutes = Math.floor(totalSeconds / 60);
  const zeroPad = (num) => String(num).padStart(2,'0');
  const seconds = totalSeconds % 60;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${zeroPad(hours)}:${zeroPad(minutes)}:${zeroPad(seconds)}`;
}

function secondsToDhms(seconds) {
	seconds = Number(seconds);
	const zeroPad = (num) => String(num).padStart(2,'0');
	let d = Math.floor(seconds / (3600*24));
	let h = Math.floor(seconds % (3600*24) / 3600);
	let m = Math.floor(seconds % 3600 / 60);
	let s = Math.floor(seconds % 60);
	let dDisplay = d > 0 ? d + "d " : "";
	return dDisplay + zeroPad(h) + ":" + zeroPad(m) + ":" + zeroPad(s);
	
}

// Generic AJAX functions
async function getAPIJSON(url){
    let response = await fetch(url);
    if(response.ok){
        let resp =  await response.json();
        if(resp['SUCCESS']){
            return resp['SUCCESS'];
        } 
        if(resp['SECURITY']){
            return resp;
        }
    }
    console.log(`getAPIJSON error status ${response.status} ${response.statusText}`);
    return false;
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

//
// Authentication
// 

// Check Logon Status
async function checkLogonStatus(){
    let sessionStatus = await getAPIJSON("master/auth/check")
    let loginRegion = document.getElementById("login-out-region");
    if(sessionStatus === "Logged In"){
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


// Do Logins
var originalLoginBox = "";
async function doLogin(){
    let loginResponse = await postAPIForm("master/login", new FormData(document.getElementById("loginBox")));
    originalLoginBox = document.getElementById("loginModal").innerHTML;
    if( loginResponse["SUCCESS"] ){
        document.getElementById("login-modal-body").innerHTML = `
<div class="login-form-success">
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-square-fill" viewBox="0 0 16 16">
  <path d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2zm10.03 4.97a.75.75 0 0 1 .011 1.05l-3.992 4.99a.75.75 0
 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.75.75 0 0 1 1.08-.022z"/>
</svg>
Login Successful
</div>
`;
        document.getElementById("login-modal-footer").innerHTML = `
    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="clearLogin()">OK</button>
`;
        loggedIn = true;
    } else {
        document.getElementById("loginModalLabel").innerHTML = "Login Failed";
        document.getElementById("loginModalLabel").classList.add("login-form-failure-header");
    }
    checkLogonStatus();
}

// Clear Login
function clearLogin(){
    if( ! originalLoginBox === "" ){
        document.getElementById("loginModal").innerHTML = originalLoginBox;
        checkLogonStatus();
    }
}

// Do logouts
var originalLogoutBox = "";
async function doLogout(){
    let logoutResponse = await getAPIJSON("master/auth/logout")
    originalLogoutBox = document.getElementById("logoutModal").innerHTML;
    if( logoutResponse["SECURITY"] ){
        document.getElementById("logout-modal-body").innerHTML = `
<div class="login-form-success">
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-square-fill" viewBox="0 0 16 16">
  <path d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2zm10.03 4.97a.75.75 0 0 1 .011 1.05l-3.992 4.99a.75.75 0
 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.75.75 0 0 1 1.08-.022z"/>
</svg>
Logout Successful
</div>
`;
        document.getElementById("logout-modal-footer").innerHTML = `
    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="clearLogout()">OK</button>
`;
        loggedIn= false;
    } else {
        document.getElementById("logout-modal-body").innerHTML = logoutResponse;
    }
    checkLogonStatus();
}

function clearLogout(){
    if( ! originalLogoutBox === "" ){
        document.getElementById("logoutModal").innerHTML = originalLogoutBox;
        checkLogonStatus();
    }
}


//
// UI / Menuing
// 

// Generate and Draw Menus
async function createSidebarMenu(){
    let navMenu = `<div class="vstack d-grid gap-2 col-9 mx-auto">`;
    const pageName = "index.html";

    let customMenu = await getAPIJSON("master/ui/custom/menu");
    if(Object.keys(customMenu).length > 0){
        for(let majMenu of Object.keys(customMenu)){
            let majMenuObj = customMenu[majMenu];
            for(let majMenuLabel of Object.keys(majMenuObj)){
                let menuType = true;
                let menuObjArr = new Array(majMenuObj[majMenuLabel]);
                while(menuObjArr[0].length > 0){
                    let menuItem = menuObjArr[0].shift();
                    if( menuItem["type"] ){
                        if(menuItem["type"] === "menu"){
                            navMenu = navMenu.concat(`<div class="btn-group">
                                <button class="btn btn-secondary dropdown-toggle" data-bs-toggle="dropdown">${majMenuLabel}</button>
                                <div class="dropdown-menu">`);
                            menuType = true;
                        } else {
                            menuType = false;
                        }
                    } else {
                        if(menuType){
                            for( let ml of Object.keys(menuItem)){
                                const mo = menuItem[ml];
                                if(mo.match(/^[0-9]+$/)){
									let currp = window.location.href.split("/").at(-1);
									let newp = `${pageName}#${mo}`;
									let onClickSlot = "";
									if( currp === newp ){
										onClickSlot = "onclick=\"window.location.reload()\"";
									}
	                                navMenu = navMenu.concat(`<a class="dropdown-item" href="${newp}" ${onClickSlot}>${ml}</a>`);

                                } else {
									let currp = window.location.href.split("/").at(-1);
	                                let newp = menuItem[ml];
	                                let onClickSlot = "";
	                                if( currp === newp ){
	                                    onClickSlot = "onclick=\"window.location.reload()\"";
	                                }
									navMenu = navMenu.concat(`<a class="dropdown-item" href="${newp}" ${onClickSlot}">${ml}</a>`);
                                }
                            }
                        } else {
                            for( let ml of Object.keys(menuItem)){
								let currp = window.location.href.split("/").at(-1);
                                let newp = menuItem[ml];
                                let onClickSlot = "";
	                            if( currp === newp ){
                                    onClickSlot = "onclick=\"window.location.reload()\"";
                                }
								navMenu = navMenu.concat(`<div class="btn-group">
                                    <a href="${newp}" ${onClickSlot} class="btn btn-secondary" role="button">${ml}</a>
                                    </div>`);
                            }
                        }
                    }
                }
                if(menuType){
                    navMenu = navMenu.concat(`</div></div>`);
                } 
            }
        }
    } else {
        let allNodes = await getAPIJSON("master/node/listall")
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
