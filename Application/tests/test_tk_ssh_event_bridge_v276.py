"""Thread ownership and generation semantics for the real Tk integration boundary."""
import threading
import unittest
from tk_ssh_event_bridge import TkSSHEventBridge

class Resource:
    def __init__(self): self.closed = 0
    def close(self): self.closed += 1

class TkSSHEventBridgeTests(unittest.TestCase):
    def test_worker_thread_success_delivered_only_on_ui_drain(self):
        owner = threading.get_ident(); seen=[]
        bridge=TkSSHEventBridge(lambda x:seen.append((x,threading.get_ident())),lambda e:None)
        gen=bridge.begin(); t=threading.Thread(target=lambda:bridge.post_success(gen,'ready'))
        t.start();t.join();self.assertEqual(seen,[])
        self.assertEqual(bridge.drain(),1);self.assertEqual(seen,[('ready',owner)])
    def test_cancel_discards_and_closes_stale_resource(self):
        r=Resource();seen=[];b=TkSSHEventBridge(seen.append,lambda e:None)
        g=b.begin();b.post_success(g,r);b.invalidate();b.drain()
        self.assertEqual(seen,[]);self.assertEqual(r.closed,1)
    def test_close_discards_pending_and_prevents_new_generation(self):
        r=Resource();b=TkSSHEventBridge(lambda x:None,lambda e:None)
        g=b.begin();b.post_success(g,r);b.close()
        self.assertEqual(r.closed,1)
        with self.assertRaises(RuntimeError):b.begin()
    def test_errors_only_delivered_for_current_generation(self):
        seen=[];b=TkSSHEventBridge(lambda x:None,seen.append)
        g=b.begin();b.post_error(g,ValueError('old'));g=b.begin();b.post_error(g,ValueError('new'));b.drain()
        self.assertEqual(len(seen),1);self.assertEqual(str(seen[0]),'new')
    def test_wrong_thread_cannot_drain_or_invalidate(self):
        b=TkSSHEventBridge(lambda x:None,lambda e:None);errors=[]
        def worker():
            for f in (b.drain,b.invalidate):
                try:f()
                except RuntimeError as e:errors.append(str(e))
        t=threading.Thread(target=worker);t.start();t.join()
        self.assertEqual(len(errors),2)
    def test_bounded_drain(self):
        seen=[];b=TkSSHEventBridge(seen.append,lambda e:None);g=b.begin()
        for n in range(4):b.post_success(g,n)
        self.assertEqual(b.drain(2),2);self.assertEqual(seen,[0,1]);self.assertEqual(b.drain(),2)
