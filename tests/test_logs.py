import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import runpy
import sys
import tarfile
import types
from unittest.mock import AsyncMock
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from asl_allmon.logs import LogService, LogError, DEFAULT_LOG_SETTINGS
from asl_allmon import allmon3_server
HOOK = runpy.run_path(str(ROOT/'src/helpers/connection-log'))
READER = runpy.run_path(str(ROOT/'src/helpers/log-reader'))

def test_configuration_backup_restores_switches_and_hook_gates(tmp_path):
    assert HOOK['SETTINGS'] == DEFAULT_LOG_SETTINGS
    relative = Path(DEFAULT_LOG_SETTINGS).relative_to('/etc/allmon3')
    config = tmp_path/'original/etc/allmon3'
    settings = config/relative
    settings.parent.mkdir(parents=True, mode=0o755)
    manifest = config/'logging-nodes.json'
    manifest.write_text('{"nodes":["1999","2000"]}')
    service = LogService(['1999','2000'], manifest, settings)
    service.set_enabled('1999', False)
    service.set_enabled('2000', True)
    archive = tmp_path/'config.tar'
    with tarfile.open(archive, 'w') as backup:
        backup.add(config, arcname='etc/allmon3')
    with tarfile.open(archive) as backup:
        backup.extractall(tmp_path/'restored', filter='data')
    restored_config = tmp_path/'restored/etc/allmon3'
    restored = LogService(['1999','2000'], restored_config/'logging-nodes.json', restored_config/relative)
    assert restored._settings() == {'1999':False, '2000':True}
    assert restored.settings.stat().st_mode & 0o777 == 0o644
    log = tmp_path/'connectlog'
    assert not HOOK['emit'](log,'CONNECT','1999','111',restored.settings)
    assert HOOK['emit'](log,'CONNECT','2000','222',restored.settings)
    restored.set_enabled('1999', True)
    assert HOOK['emit'](log,'CONNECT','1999','111',restored.settings)

@pytest.fixture
def service(tmp_path):
    manifest = tmp_path/'manifest.json'; manifest.write_text('{"nodes":["1999","2000","999"]}')
    return LogService(['1999','2000'], manifest, tmp_path/'nodes.json')

def test_scopes_and_independent_persistent_switches(service):
    assert service.nodes == ['1999','2000']  # never permit non-local manifest node
    service.set_enabled('1999', False)
    state = service.snapshot(['1999'])
    assert state == {'nodes': [{'node':'1999','enabled':False}], 'messages_allowed':False, 'refresh_seconds':5}
    assert service.snapshot(['1999','2000'])['messages_allowed']
    again = LogService(service.nodes, service.settings.parent/'manifest.json', service.settings)
    assert again.snapshot(['1999'])['nodes'][0]['enabled'] is False
    assert HOOK['enabled']('1999', service.settings) is False
    assert HOOK['enabled']('2000', service.settings) is True
    assert service.settings.stat().st_mode & 0o777 == 0o644

def test_concurrent_updates_and_invalid_values(service):
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda node:service.set_enabled(node, False), service.nodes))
    assert service._settings() == {'1999':False,'2000':False}
    before = service.settings.read_bytes()
    for node, value in [('999',True),('1999','false'),('1999',0),('../x',True)]:
        with pytest.raises(LogError): service.set_enabled(node,value)
    assert service.settings.read_bytes() == before
    service.settings.write_text('broken')
    with pytest.raises(LogError): service.set_enabled('1999',True)
    assert service.settings.read_text() == 'broken'
    assert HOOK['enabled']('1999', service.settings)  # never lose logs on corrupt gate

def test_hook_respects_each_node_without_deleting_history(service,tmp_path):
    log = tmp_path/'connectlog'
    emit = HOOK['emit']
    assert emit(log,'CONNECT','1999','111',service.settings)
    original = log.read_text()
    service.set_enabled('1999',False)
    assert not emit(log,'DISCONNECT','1999','111',service.settings)
    assert log.read_text() == original
    assert emit(log,'CONNECT','2000','222',service.settings)
    service.set_enabled('1999',True)
    assert emit(log,'DISCONNECT','1999','111',service.settings)
    lines=log.read_text().splitlines()
    assert len(lines)==3 and 'local=2000 remote=222' in lines[1]
    with pytest.raises(ValueError): emit(log,'CONNECT','1999','injected\nrecord',service.settings)
    assert len(log.read_text().splitlines())==3

def test_reader_scope_bounds_missing_rotation_and_symlinks(tmp_path):
    read = READER['read_log']; p=tmp_path/'log'
    assert not read(p,'connections','1999',200)['exists']
    p.write_text('stamp event=CONNECT local=2000 remote=1999\nstamp event=CONNECT local=19990 remote=4\nstamp event=CONNECT local=1999 remote=2001\n')
    result=read(p,'connections','1999',200)
    assert len(result['lines'])==1 and 'remote=2001' in result['lines'][0]
    p.rename(tmp_path/'log.1');p.write_text('new file <script>not executed</script>\n')
    assert read(p,'messages','-',200)['lines']==['new file <script>not executed</script>']
    link=tmp_path/'link';link.symlink_to(p)
    with pytest.raises(OSError):read(link,'messages','-',200)
    p.write_text(('x'*200+'\n')*2000)
    result=read(p,'messages','-',1000)
    assert result['truncated'] and len(result['lines'])==1000
    assert sum(map(len,result['lines']))<READER['MAX_BYTES']

@pytest.mark.asyncio
async def test_http_permissions_mutation_validation_and_origin(service,monkeypatch):
    server=allmon3_server.ServerWS.__new__(allmon3_server.ServerWS)
    server.logs=service
    service.read=AsyncMock(return_value={'lines':['safe'],'exists':True,'truncated':False})
    server.server_security=types.SimpleNamespace(
        session_db={n:types.SimpleNamespace(user=n) for n in ['one','both','admin','other']},
        restricted_users={'one','both','other'},
        restrictdb={'one1999','both1999','both2000','other999'})
    async def session(request):return {'auth_sess':request.headers.get('X-Test-User')}
    monkeypatch.setattr(allmon3_server,'get_session',session)
    app=web.Application()
    app.add_routes([web.get('/logs/state',server._ServerWS__logs_state),
        web.get('/logs/{kind:connections|messages}',server._ServerWS__logs_read),
        web.post('/logs/nodes/{node:[0-9]+}',server._ServerWS__logs_toggle)])
    async with TestClient(TestServer(app)) as client:
        for path in ['/logs/state','/logs/messages','/logs/connections?node=1999']:
            assert (await client.get(path)).status==403
        assert (await client.post('/logs/nodes/1999',json={'enabled':False})).status==403
        one={'X-Test-User':'one'};both={'X-Test-User':'both'}
        r=await client.get('/logs/state',headers=one);assert (await r.json())['SUCCESS']['nodes']==[{'node':'1999','enabled':True}]
        assert r.headers['Cache-Control']=='no-store'
        for path in ['/logs/messages','/logs/connections?node=2000','/logs/connections?node=999']:
            assert (await client.get(path,headers=one)).status==403
        service.read.assert_not_called()
        assert (await client.get('/logs/connections?node=1999',headers=one)).status==200
        assert (await client.get('/logs/messages',headers=both)).status==200
        assert (await client.post('/logs/nodes/2000',headers=one,json={'enabled':False})).status==403
        assert not service.settings.exists()
        assert (await client.post('/logs/nodes/1999',headers={**one,'Origin':'https://evil.example'},json={'enabled':False})).status==403
        assert (await client.post('/logs/nodes/1999',headers=one,data={'enabled':'false'})).status==415
        for payload in [[],{'enabled':'false'},{'enabled':True,'node':'2000'},{'enabled':1}]:
            assert (await client.post('/logs/nodes/1999',headers=one,json=payload)).status==400
        assert not service.settings.exists()
        assert (await client.post('/logs/nodes/1999',headers=one,json={'enabled':False})).status==200
        assert service._settings()=={'1999':False}
        assert (await client.get('/logs/state',headers={'X-Test-User':'other'})).status==403
        assert (await client.post('/logs/nodes/1999',headers=one,json={'enabled':True})).status==200


def test_server_initialization_never_labels_remote_node_local(monkeypatch):
    captured = []
    monkeypatch.setattr(allmon3_server.logs, 'LogService', lambda nodes: captured.extend(nodes))
    monkeypatch.setattr(allmon3_server.socket, 'gethostname', lambda: 'testhost')
    monkeypatch.setattr(allmon3_server.socket, 'getfqdn', lambda: 'testhost.example')
    monkeypatch.setattr(allmon3_server.socket, 'getaddrinfo', lambda *a: [])
    configs = types.SimpleNamespace(
        all_nodes=[1999,2000,2001], colo_nodes={2000:1999},
        nodes={1999:types.SimpleNamespace(host='127.0.0.1'),
               2001:types.SimpleNamespace(host='remote.example')})
    # Arbitrary options from a different feature must not override locality.
    allmon3_server.ServerWS(types.SimpleNamespace(audio_local_nodes={2001}), configs, None)
    assert captured == [1999,2000]


@pytest.mark.asyncio
async def test_reader_rejects_bad_requests_before_starting_process(service):
    for kind,node,limit in [('connections','999',200),('messages','-',0),
                            ('messages','-',1001),('../../etc/passwd','-',10)]:
        with pytest.raises(LogError):
            await service.read(kind,node,limit)
