const {chromium}=require('playwright');const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:1000}});const root=path.join(__dirname,'../web');
 const requests=[];const state={nodes:[1998],assets:[],sources:[],schedules:[],jobs:[],playback_enabled:true,can_manage_playback:true};
 await page.addInitScript(()=>{window.loggedIn=true});
 await page.route('http://test/**',route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/master/audio/state')return route.fulfill({json:{SUCCESS:state}});
  if(url.pathname==='/master/audio/enable'){state.playback_enabled=route.request().postDataJSON().enabled;return route.fulfill({json:{SUCCESS:{id:state.playback_enabled}}})}
  if(url.pathname==='/master/audio/schedule'){requests.push(route.request().postDataJSON());return route.fulfill({json:{SUCCESS:{id:'test-only'}}})}
  if(url.pathname.endsWith('.js')&&!url.pathname.endsWith('/audio.js'))return route.fulfill({contentType:'application/javascript',body:''});
  const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);
  return fs.existsSync(file)&&fs.statSync(file).isFile()?route.fulfill({path:file}):route.fulfill({status:404,body:''});
 });
 await page.goto('http://test/');await page.evaluate(()=>audioAuthChanged());assert.equal(await page.locator('#audio-master-label').isVisible(),false);await page.locator('#audio-title h2').click();

 assert.equal(await page.locator('#audio-master-label').isVisible(),true);
 assert.equal(await page.locator('#audio-master-enabled').isChecked(),true);
 await page.locator('#audio-master-enabled').uncheck();
 await page.waitForFunction(()=>audioState.playback_enabled===false&&!audioMasterBusy);
 assert.equal(await page.locator('#audio-manager').evaluate(e=>e.open),true);
 assert.equal(await page.locator('#audio-queue').isDisabled(),true);
 assert.match(await page.locator('#audio-playback-status').innerText(),/disabled/);
 await page.locator('#audio-master-enabled').check();
 await page.waitForFunction(()=>audioState.playback_enabled===true&&!audioMasterBusy);
 assert.equal(await page.locator('#audio-queue').isDisabled(),false);
 assert.equal(await page.getByText('Name your stack, add audio below, then play it now or save a schedule.',{exact:true}).count(),0);
 await page.locator('#audio-recurrence').selectOption('daily');


 assert.equal(await page.locator('label[for="audio-stack-name"]').innerText(),'Stack name / Announcement Text');
 assert.equal(await page.getByText('Playback behavior',{exact:true}).count(),0);
 for(const width of [1440,390]) {
  await page.setViewportSize({width,height:1000});
  const name=await page.locator('#audio-stack-name').boundingBox();
  const build=await page.locator('#audio-build-title').boundingBox();
  assert.ok(name.y+name.height<build.y);
  assert.ok(await page.locator('label[for="audio-stack-name"]').isVisible());
  await page.screenshot({path:path.join(require('os').tmpdir(),'allmon3-layout-'+width+'.png'),fullPage:true});
 }
 await page.locator('#audio-recurrence').selectOption('once');
 const save=page.getByRole('button',{name:'Save schedule',exact:true});
 await save.click();assert.equal(await page.locator('#audio-stack-validation').isVisible(),true);
 assert.equal(await page.locator('#audio-add-item').getAttribute('aria-invalid'),'true');
 assert.equal(await page.locator('#audio-add-item').evaluate(e=>e===document.activeElement),true);
 assert.equal(requests.length,0);
 for(const kind of ['daily','weekly','once','daily']) {
  await page.locator('#audio-recurrence').selectOption(kind);
  for(const other of ['once','daily','weekly']) assert.equal(await page.locator('#audio-'+other+'-fields').isVisible(),kind===other);
  await save.click();assert.equal(requests.length,0);
 }

 await page.locator('#audio-add-item').selectOption('source:arn');await save.click();assert.equal(requests.length,0);
 await page.getByRole('button',{name:'Add to stack',exact:true}).click();
 assert.equal(await page.locator('#audio-stack-validation').isVisible(),false);
 assert.equal(await page.locator('#audio-add-item').getAttribute('aria-invalid'),null);
 await page.locator('#audio-stack-name').fill('Browser-only test');
 await page.locator('#audio-daily-time').fill('');await save.click();assert.equal(requests.length,0);
 await page.locator('#audio-daily-time').fill('22:30');
 const saved=page.waitForResponse(r=>r.url().endsWith('/master/audio/schedule')&&r.request().method()==='POST');
 await save.click();await saved;
 await page.waitForFunction(()=>!audioRefreshing);assert.equal(await page.locator('#audio-feedback').innerText(),'');
 assert.equal(requests.length,1);assert.deepEqual(requests[0].items,['source:arn']);assert.equal(requests[0].recurrence,'daily');assert.equal(requests[0].local_time,'22:30');assert.equal(requests[0].weekday,undefined);assert.equal(requests[0].run_at,undefined);
 await page.locator('#audio-stack').getByRole('button',{name:'Remove',exact:true}).click();await save.click();
 assert.equal(await page.locator('#audio-stack-validation').isVisible(),true);assert.equal(requests.length,1);
 console.log('PASS: empty once/daily/weekly stacks blocked without request; selecting without adding still blocked; warning focuses selector; Add clears warning; Daily fields/payload and blank-time validation work; removing last item restores guard. No live backend used.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
