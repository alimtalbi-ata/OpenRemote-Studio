import unittest
from ssh_end_to_end_probe import probe
H=[{'host':'jump1.example.org','port':22,'user':'ops'}, {'host':'jump2.example.org','port':2222,'user':'admin'}]
class Fake:
    instances=[]
    def __init__(self,target,route,on_stage,keepalive):
        self.target=target;self.route=route;self.on_stage=on_stage;self.keepalive=keepalive
        self.closed=False;Fake.instances.append(self)
    def connect(self):
        self.on_stage('bastion_connect','starting');self.on_stage('bastion_connect','ok')
        self.on_stage('bastion_2_connect','ok');self.on_stage('target_connect','ok')
    def close(self):self.closed=True
class TestEndToEnd(unittest.TestCase):
    def setUp(self):Fake.instances=[]
    def test_requires_consent(self):
        with self.assertRaises(PermissionError):probe(H,'target.example.org',factory=Fake)
        self.assertEqual(Fake.instances,[])
    def test_success(self):
        r=probe(H,'target.example.org',factory=Fake,consent=True)
        self.assertEqual(r['status'],'authenticated');self.assertEqual(len(r['events']),4)
        self.assertTrue(Fake.instances[0].closed)
    def test_route(self):
        probe(H,'target.example.org',2222,'root',Fake,True)
        f=Fake.instances[0];self.assertEqual(f.target['port'],2222)
        self.assertEqual(f.route['jump_host'],'jump1.example.org')
        self.assertEqual(f.keepalive,0)
    def test_invalid_host(self):
        with self.assertRaises(ValueError):probe(H,'bad host',factory=Fake,consent=True)
    def test_invalid_user(self):
        with self.assertRaises(ValueError):probe(H,'target.example.org',user='a\nsecret',factory=Fake,consent=True)
    def test_invalid_hops(self):
        with self.assertRaises(ValueError):probe(H+H,'target.example.org',factory=Fake,consent=True)
    def test_failure_redacted(self):
        class Bad(Fake):
            def connect(self):
                self.on_stage('bastion_connect','failed')
                raise RuntimeError('PASSWORD=verysecret')
        r=probe(H,'target.example.org',factory=Bad,consent=True)
        self.assertEqual(r['status'],'failed');self.assertNotIn('verysecret',str(r));self.assertTrue(Fake.instances[0].closed)
    def test_unknown_stage_redacted(self):
        class Weird(Fake):
            def connect(self):self.on_stage('secret-stage-PASSWORD','secret')
        r=probe(H,'target.example.org',factory=Weird,consent=True)
        self.assertEqual(r['events'][0],{'step':'Étape SSH','state':'failed'})
