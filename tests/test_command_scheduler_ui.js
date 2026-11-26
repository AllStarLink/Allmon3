/* Browser-only backend simulation. No radio or Asterisk connection. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const WEATHER='rpt cmd 59521 cmd /usr/lib/allmon3-weather/say-weather-59521';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const root=path.join(__dirname,'../web');
  const state={nodes:[59521,529991],assets:[],sources:[],schedules:[],jobs:[],timezone:'America/Los_Angeles',playback_enabled:false,command_enabled:false,can_manage_playback:true};
  const mutations=[],errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.addInitScript(()=>{window.loggedIn=true});
  await page.route('http://allmon-test/**', async route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/master/addons')return route.fulfill({json:{addons:[{id:'announcements',label:'Announcements',script:'addons/announcements/audio.js',fragment:'addons/announcements/panel.html',stylesheet:'addons/announcements/audio.css'}]}});
   if(url.pathname.startsWith('/master/audio/')){
    const action=url.pathname.split('/').pop();
    if(action==='state')return route.fulfill({json:{SUCCESS:state}});
    if(route.request().method()==='DELETE'){
     assert.equal(url.pathname, '/master/audio/schedule/'+state.schedules[0].id);
     state.schedules.shift();return route.fulfill({json:{SUCCESS:'Removed'}});
    }
    const body=route.request().postDataJSON();mutations.push({action,body});
    if(action==='command-enable')state.command_enabled=body.enabled;
    else if(action==='enable')state.playback_enabled=body.enabled;
    else if(action==='schedule')state.schedules.push({...body,id:String(state.schedules.length+1).repeat(32),enabled:1,next_at:1900000000});
    else throw new Error('Unexpected action: '+action);
    return route.fulfill({json:{SUCCESS:{id:'1'.repeat(32)}}});
   }
   if(url.pathname.endsWith('.js')&&!['audio.js','addons.js'].includes(path.basename(url.pathname)))return route.fulfill({contentType:'application/javascript',body:''});
   const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);
   return fs.existsSync(file)&&fs.statSync(file).isFile()?route.fulfill({path:file}):route.fulfill({status:404,body:''});
  });
  await page.goto('http://allmon-test/');
  await page.waitForFunction(()=>typeof audioAuthChanged==='function');
  await page.evaluate(()=>audioAuthChanged());
  await page.locator('#audio-title h2').click();
  assert.equal(await page.locator('#command-master-enabled').isChecked(),false);
  assert.equal(await page.locator('#audio-master-enabled').isChecked(),false);
  const audioBox=await page.locator('#audio-master-label').boundingBox();
  const commandBox=await page.locator('#command-master-label').boundingBox();
  assert.ok(commandBox.x>audioBox.x+audioBox.width && Math.abs(commandBox.y-audioBox.y)<3, 'toggles side by side on desktop');
  await page.locator('#command-master-enabled').check();
  await page.waitForFunction(()=>audioState.command_enabled===true && !commandMasterBusy);
  assert.equal(await page.locator('#audio-manager').evaluate(e=>e.open),true,'toggle does not collapse panel');
  assert.equal(await page.locator('#audio-master-enabled').isChecked(),false,'command toggle independent');
  assert.equal(await page.locator('#audio-queue').isEnabled(),false);
  await page.locator('#audio-schedule-kind').selectOption('command');
  await page.locator('#command-name').fill('Say weather');
  await page.locator('#command-text').fill(WEATHER);
  for(const recurrence of ['once','daily','weekly']){
   await page.locator('#audio-recurrence').selectOption(recurrence);
   if(recurrence==='once')await page.locator('#audio-run-at').fill('2030-06-01T14:15');
   if(recurrence==='daily')await page.locator('#audio-daily-time').fill('09:30');
   if(recurrence==='weekly'){
    await page.locator('#audio-weekday').selectOption('2');
    await page.locator('#audio-weekly-time').fill('17:45');
   }
   await page.locator('button[onclick="scheduleAudio()"]').click();
   await page.waitForFunction(n=>audioState.schedules.length===n,['once','daily','weekly'].indexOf(recurrence)+1);
   await page.waitForFunction(()=>!audioRefreshing);
   const payload=mutations.filter(x=>x.action==='schedule').at(-1).body;
   assert.equal(payload.recurrence,recurrence);assert.equal(payload.command,WEATHER);
   assert.equal(payload.node,59521);assert.equal(payload.kind,'command');assert.deepEqual(payload.items,[]);
   assert.equal(payload.name,'Say weather');
   if(recurrence==='once')assert.equal(payload.run_at,'2030-06-01T14:15');
   if(recurrence==='daily')assert.equal(payload.local_time,'09:30');
   if(recurrence==='weekly'){assert.equal(payload.local_time,'17:45');assert.equal(payload.weekday,2);}
  }
  assert.equal(await page.locator('#audio-stack-validation').isVisible(),false,'empty audio stack allowed for command');
  assert.match(await page.locator('#audio-schedules').innerText(),/Command: rpt cmd 59521 cmd/);
  state.jobs=[{id:'b'.repeat(32),node:59521,name:'Say weather',kind:'command',command:WEATHER,items:[],position:1,status:'dispatched'}];
  await page.evaluate(()=>refreshAudioState());
  assert.match(await page.locator('#audio-jobs').innerText(),/dispatched.*Command: rpt cmd/);
  assert.equal(await page.locator('#audio-pause').isEnabled(),false);
  assert.equal(await page.locator('#audio-stop').isEnabled(),false);
  await page.locator('#command-master-enabled').uncheck();
  await page.waitForFunction(()=>!audioState.command_enabled && !commandMasterBusy);
  await page.locator('#audio-master-enabled').check();
  await page.waitForFunction(()=>audioState.playback_enabled && !audioMasterBusy);
  assert.equal(await page.locator('#command-master-enabled').isChecked(),false);
  await page.locator('#audio-schedules button').first().click();
  await page.waitForFunction(()=>audioState.schedules.length===2);
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.locator('#command-master-enabled').isVisible(),true);
   assert.equal(await page.evaluate(()=>[document.querySelector('#audio-manager'),...document.querySelectorAll('#audio-manager *')].every(e=>{const r=e.getBoundingClientRect();return !r.width || (r.x>=0 && r.right<=innerWidth)})),true,'scheduler fits viewport');
   await page.screenshot({path:path.join(__dirname,'../../command-scheduler-'+width+'.png'),fullPage:true});
  }
  await page.evaluate(()=>{loggedIn=false;return audioAuthChanged()});
  assert.equal(await page.locator('#command-name').inputValue(),'');
  assert.equal(await page.locator('#command-text').inputValue(),'');
  assert.equal(await page.locator('#audio-schedule-kind').inputValue(),'audio');
  assert.equal(await page.locator('#command-master-enabled').isEnabled(),false);
  assert.deepEqual(errors,[]);
  console.log('PASS command scheduler UI: exact weather command, Once/Daily/Weekly, independent adjacent toggles, no audio required, history/deletion, mobile layout and logout cleanup. Mock backend only.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
