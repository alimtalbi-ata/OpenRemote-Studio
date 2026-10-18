import unittest
from threading import Event
from ssh_end_to_end_probe import probe

HOPS=[{'host':'jump.example','port':22,'user':'ops'}]
class FakeClient:
    def __init__(self,endpoint,route,on_stage,keepalive,**kw):
        self.on_stage=on_stage;self.cancelled=kw.get('cancelled');self.closed=False
    def connect(self):
        self.on_stage('bastion_connect','starting')
        self.on_stage('bastion_connect','ok')
    def close(self):self.closed=True

class V96Tests(unittest.TestCase):
    def test_cancel_before_connection(self):
        event=Event();event.set()
        result=probe(HOPS,'target.example',consent=True,cancelled=event,factory=FakeClient)
        self.assertEqual(result['status'],'cancelled')
    def test_progress_events(self):
        progress=[]
        result=probe(HOPS,'target.example',consent=True,factory=FakeClient,on_event=progress.append)
        self.assertEqual(result['status'],'authenticated')
        self.assertEqual(len(progress),2)
        self.assertEqual(progress[0]['step'],'Bastion principal')
    def test_cancel_after_connection(self):
        event=Event()
        class CancelClient(FakeClient):
            def connect(self):event.set()
        result=probe(HOPS,'target.example',consent=True,cancelled=event,factory=CancelClient)
        self.assertEqual(result['status'],'cancelled')
    def test_interrupted(self):
        class Interrupt(FakeClient):
            def connect(self):raise InterruptedError('secret')
        result=probe(HOPS,'target.example',consent=True,factory=Interrupt)
        self.assertEqual(result['status'],'cancelled')
        self.assertNotIn('secret',result['message'])
    def test_failure_redaction(self):
        class Failure(FakeClient):
            def connect(self):raise RuntimeError('password=secret')
        result=probe(HOPS,'target.example',consent=True,factory=Failure)
        self.assertEqual(result['status'],'failed')
        self.assertNotIn('secret',str(result))
    def test_no_consent(self):
        with self.assertRaises(PermissionError):probe(HOPS,'target.example',factory=FakeClient)
    def test_progress_defensive_copy(self):
        seen=[]
        result=probe(HOPS,'target.example',consent=True,factory=FakeClient,on_event=lambda e:(seen.append(e),e.update(step='tampered')))
        self.assertEqual(result['events'][0]['step'],'Bastion principal')
