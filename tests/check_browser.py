"""Isolated log-panel interactions; no host or radio connection."""
from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright, expect
R=Path(__file__).resolve().parents[1]
html=(R/'web/index.html').read_text()
start=html.index('        <details id="logs-manager"')
panel=html[start:html.index('        </details>',start)+len('        </details>')]
with sync_playwright() as p:
 executable=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
 b=p.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True)
 ctx=b.new_context();page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 state={'1999':True,'2000':True};reads=[];posts=[]
 def api(route):
  req=route.request;url=req.url
  if url.endswith('/state'):data={'nodes':[{'node':n,'enabled':v} for n,v in state.items()],'messages_allowed':True}
  elif '/nodes/' in url:
   node=url.rsplit('/',1)[-1];state[node]=req.post_data_json['enabled'];posts.append(node);data={'node':node,'enabled':state[node]}
  else:
   reads.append(url);data={'lines':['<img src=x onerror="window.INJECTED=true">','local=1999 CONNECT'], 'exists':True,'truncated':False}
  route.fulfill(json={'SUCCESS':data})
 ctx.route('http://test.invalid/master/logs/**',api)
 ctx.route('http://test.invalid/',lambda route:route.fulfill(body='<html><head></head><body><button id="logs-navigation"></button><div id="sidebarMenu"></div>'+ panel+'<script>var loggedIn=true;</script></body></html>',content_type='text/html'))
 page.goto('http://test.invalid/');page.add_style_tag(content='.d-none {display:none}');page.add_script_tag(path=str(R/'web/js/logs.js'))
 page.evaluate('logsAuthChanged()');expect(page.locator('#logs-enable-1999')).to_be_checked()
 page.evaluate('openLogsPanel()');expect(page.locator('#logs-output')).to_contain_text('<img')
 assert page.locator('#logs-output img').count()==0 and not page.evaluate('Boolean(window.INJECTED)')
 page.locator('#logs-enable-1999').uncheck();expect(page.locator('label[for="logs-enable-1999"]')).to_contain_text('Recording off')
 assert state=={'1999':False,'2000':True}
 page.locator('#logs-enable-1999').check();expect(page.locator('label[for="logs-enable-1999"]')).to_contain_text('Recording on')
 page.locator('#logs-search').fill('CONNECT');expect(page.locator('#logs-output')).to_have_text('local=1999 CONNECT')
 page.locator('#logs-kind').select_option('messages');expect(page.locator('#logs-node')).to_be_disabled()
 with page.expect_download() as d:page.locator('#logs-download').click()
 assert d.value.suggested_filename=='messages.txt'
 page.evaluate('loggedIn=false; logsAuthChanged()');expect(page.locator('#logs-output')).to_have_text('');expect(page.locator('#logs-manager')).not_to_be_visible()
 page.evaluate('loggedIn=true; logsAuthChanged()');expect(page.locator('#logs-enable-1999')).to_be_attached()
 assert not errors,errors
 print(json.dumps({'passed':['node switches independent and reversible','untrusted text escaped','search and download','shared-log scope','logout clears content; relogin restores controls'],'errors':errors}))
 b.close()
