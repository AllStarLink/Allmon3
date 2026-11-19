import asyncio,json,tempfile,types,unittest
from pathlib import Path
from aiohttp import web
from test_audio_api import load_server

class ControlsAPITest(unittest.TestCase):
    def test_control_actions_enforce_auth_node_origin_and_job_identity(self):
        Server=load_server()
        with tempfile.TemporaryDirectory() as directory:
            nodes=types.SimpleNamespace(all_nodes=[1999,2000],colo_nodes={},nodes={
                n:types.SimpleNamespace(host='localhost',port=5038) for n in [1999,2000]})
            security=types.SimpleNamespace(session_db={'valid':types.SimpleNamespace(user='ham')},
                restricted_users={'ham'},restrictdb={'ham1999'})
            server=Server(None,nodes,security)
            calls=[]
            async def control(node,ident,action):calls.append((node,ident,action));return ident
            server.audio.control_job=control
            class Request:
                session={};headers={};host='radio.example';content_type='application/json'
                match_info={};node=1999
                async def json(self):return {'node':self.node,'id':'a'*32}
            request=Request();mutate=server._ServerWS__audio_mutation
            for action in ['pause','resume','stop']:
                request.match_info={'action':action};request.session={};request.headers={};request.node=1999
                with self.assertRaises(web.HTTPForbidden):asyncio.run(mutate(request))
                request.session={'auth_sess':'valid'};request.node=2000
                with self.assertRaises(web.HTTPForbidden):asyncio.run(mutate(request))
                request.node=1999;request.headers={'Origin':'https://evil.example'}
                with self.assertRaises(web.HTTPForbidden):asyncio.run(mutate(request))
                self.assertEqual(len(calls),['pause','resume','stop'].index(action))
                request.headers={'Origin':'https://radio.example'}
                result=asyncio.run(mutate(request));self.assertEqual(result.status,200)
                self.assertEqual(json.loads(result.text),{'SUCCESS':{'id':'a'*32}})
                self.assertEqual(calls[-1],(1999,'a'*32,action))

    def test_master_requires_all_local_node_permissions_and_origin(self):
        Server=load_server()
        with tempfile.TemporaryDirectory() as directory:
            nodes=types.SimpleNamespace(all_nodes=[1999,2000],colo_nodes={},nodes={
                n:types.SimpleNamespace(host='localhost',port=5038) for n in [1999,2000]})
            security=types.SimpleNamespace(session_db={'valid':types.SimpleNamespace(user='ham')},
                restricted_users={'ham'},restrictdb={'ham1999'})
            server=Server(None,nodes,security)
            calls=[]
            server.audio.set_playback_enabled=lambda value:calls.append(value) or value
            class Request:
                session={'auth_sess':'valid'};headers={'Origin':'https://radio.example'}
                host='radio.example';content_type='application/json';match_info={'action':'enable'}
                async def json(self):return {'node':1999,'enabled':False}
            request=Request();mutate=server._ServerWS__audio_mutation
            with self.assertRaises(web.HTTPForbidden):asyncio.run(mutate(request))
            self.assertEqual(calls,[])
            security.restrictdb.add('ham2000')
            request.headers={'Origin':'https://evil.example'}
            with self.assertRaises(web.HTTPForbidden):asyncio.run(mutate(request))
            self.assertEqual(calls,[])
            request.headers={'Origin':'https://radio.example'}
            result=asyncio.run(mutate(request))
            self.assertEqual(result.status,200);self.assertEqual(calls,[False])
