const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined,headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();let installed=false;let calls=0;const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{window.loggedIn=true});
  const root=path.join(__dirname,'../web');
  const manifest={id:'announcements',label:'Announcements',script:'addons/announcements/audio.js',fragment:'addons/announcements/panel.html',stylesheet:'addons/announcements/audio.css'};
  await page.route('http://addons.test/**',route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/master/addons')return route.fulfill({json:{addons:installed?[manifest]:[]}});
   if(url.pathname==='/master/audio/state'){calls++;return route.fulfill({json:{SUCCESS:{nodes:[1998],timezone:'Europe/London',assets:[],sources:[],schedules:[],jobs:[]}}});}
   if(url.pathname.endsWith('.js')&&!['/addons.js','/audio.js'].some(x=>url.pathname.endsWith(x)))return route.fulfill({contentType:'application/javascript',body:''});
   const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);
   return fs.existsSync(file)&&fs.statSync(file).isFile()?route.fulfill({path:file}):route.fulfill({status:404});
  });
  await page.goto('http://addons.test/');await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#audio-manager').count(),0);assert.equal(calls,0);
  installed=true;await page.reload();await page.waitForFunction(()=>typeof audioState!=='undefined'&&audioState?.nodes.length);
  await page.evaluate(()=>{
   for(const node of [1998,2000]){const slot=document.createElement('div');slot.className='allmon3-node-addons';slot.dataset.node=String(node);document.querySelector("main").append(slot);}
   refreshAddonNodes();
  });
  assert.equal(await page.locator('[data-node="1998"] button').count(),1);
  assert.equal(await page.locator('[data-node="2000"] button').count(),0);
  await page.locator('[data-node="1998"] button').click();
  assert.equal(await page.locator('#audio-node').inputValue(),'1998');assert.equal(await page.locator('#audio-manager').evaluate(e=>e.open),true);
  assert.ok((await page.locator('.audio-timezone').allTextContents()).every(x=>x==='Europe/London'));
  await page.evaluate(()=>{loggedIn=false;document.dispatchEvent(new Event('allmon3:auth'));refreshAddonNodes()});
  assert.equal(await page.locator('.allmon3-node-addons button').count(),0);assert.equal(await page.locator('#audio-manager').isVisible(),false);
  assert.deepEqual(errors,[]);console.log('PASS: base-only no audio requests/UI; optional per-node embedding, timezone labels and logout cleanup; no RF backend.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
