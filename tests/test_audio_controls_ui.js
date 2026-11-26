const {chromium}=require('playwright');const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,headless:true,args:['--no-sandbox']});
 try {
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});const page=await ctx.newPage();
 const root=path.join(__dirname,'../web');
 const state={nodes:[1998,1999],assets:[],sources:[],schedules:[],jobs:[{id:'a'.repeat(32),name:'Test news',node:1998,status:'playing',position:0,items:['source:arn']}]};
 const mutations=[],errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.addInitScript(()=>{window.loggedIn=true});
 await page.route('http://allmon-test/**',async route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/master/addons')return route.fulfill({json:{addons:[{id:'announcements',label:'Announcements',script:'addons/announcements/audio.js',fragment:'addons/announcements/panel.html',stylesheet:'addons/announcements/audio.css'}]}});
  if(url.pathname.startsWith('/master/audio/')){
   const action=url.pathname.split('/').pop();
   if(action==='state')return route.fulfill({json:{SUCCESS:state}});
   assert.ok(['pause','resume','stop'].includes(action));const body=route.request().postDataJSON();
   assert.deepEqual(body,{node:1998,id:'a'.repeat(32)});mutations.push(action);
   state.jobs[0].status={pause:'paused',resume:'playing',stop:'cancelled'}[action];
   return route.fulfill({json:{SUCCESS:{id:body.id}}});
  }
  if(url.pathname.endsWith('.js')&&!url.pathname.endsWith('/audio.js')&&!url.pathname.endsWith('/addons.js'))return route.fulfill({contentType:'application/javascript',body:''});
  const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);
  return fs.existsSync(file)&&fs.statSync(file).isFile()?route.fulfill({path:file}):route.fulfill({status:404,body:''});
 });
 await page.goto('http://allmon-test/');await page.waitForFunction(()=>typeof audioAuthChanged==='function');await page.evaluate(()=>audioAuthChanged());
 assert.equal(await page.locator('#audio-manager').evaluate(e=>e.open),false);
 await page.locator('#audio-title h2').click();
 assert.equal(await page.locator('#audio-pause').isEnabled(),true);
 for (const width of [1440,390]) {
  await page.setViewportSize({width,height:1000});
  const top=await page.locator('#audio-playback-panel').boundingBox();
  const build=await page.locator('#audio-build-title').boundingBox();
  for(const selector of ['#audio-stack-name','#audio-pause','#audio-stop','button[onclick="queueAudio()"]']) {
   const box=await page.locator(selector).boundingBox();assert.ok(box.y+box.height<build.y,selector+' before builder');
   assert.ok(box.x>=top.x&&box.x+box.width<=top.x+top.width+1,selector+' within panel');
  }
  const duplicates=await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.filter((id,i)=>ids.indexOf(id)!==i)});assert.deepEqual(duplicates,[]);
  await page.screenshot({path:path.join(require('os').tmpdir(),'allmon3-layout-'+width+'.png'),fullPage:true});
 }
 await page.setViewportSize({width:1440,height:1000});
 await page.locator('#audio-pause').click();await page.waitForFunction(()=>document.querySelector('#audio-pause').textContent==='Resume');
 assert.match(await page.locator('#audio-playback-status').innerText(),/paused/);
 await page.locator('#audio-pause').click();await page.waitForFunction(()=>document.querySelector('#audio-pause').textContent==='Pause');
 await page.locator('#audio-node').selectOption('1999');assert.equal(await page.locator('#audio-stop').isEnabled(),false);
 await page.locator('#audio-node').selectOption('1998');assert.equal(await page.locator('#audio-stop').isEnabled(),true);
 await page.locator('#audio-stop').click();await page.waitForFunction(()=>document.querySelector('#audio-stop').disabled);
 assert.deepEqual(mutations,['pause','resume','stop']);assert.deepEqual(errors,[]);
 await page.setViewportSize({width:390,height:844});await page.locator('#audio-pause').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(require('os').tmpdir(),'allmon3-controls-mobile.png'),fullPage:true});
 console.log('PASS browser controls with simulated backend: correct node/job payload, Pause becomes Resume, Stop, inactive-node disable, mobile placement, no JS errors. No real RF backend connected.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
