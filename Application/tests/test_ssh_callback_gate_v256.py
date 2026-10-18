import unittest
from ssh_callback_gate import SSHCallbackGate

class Resource:
    def __init__(self): self.closed = 0
    def close(self): self.closed += 1

class GateTests(unittest.TestCase):
    def test_deliver_current(self):
        g=SSHCallbackGate(); t=g.begin(); r=Resource(); seen=[]
        self.assertTrue(g.deliver(t,r,seen.append)); self.assertEqual(seen,[r]); self.assertEqual(r.closed,0)
    def test_cancel_after_callback_before_delivery(self):
        g=SSHCallbackGate(); t=g.begin(); r=Resource(); seen=[]
        g.invalidate(); self.assertFalse(g.deliver(t,r,seen.append)); self.assertEqual(r.closed,1); self.assertEqual(seen,[])
    def test_superseded_result(self):
        g=SSHCallbackGate(); old=g.begin(); g.begin(); r=Resource()
        self.assertFalse(g.deliver(old,r,lambda x: self.fail('stale delivered'))); self.assertEqual(r.closed,1)
    def test_error_suppressed_after_close(self):
        g=SSHCallbackGate(); t=g.begin(); g.close(); seen=[]
        self.assertFalse(g.deliver_error(t,'offline',seen.append)); self.assertEqual(seen,[])
    def test_closed_gate_rejects_begin(self):
        g=SSHCallbackGate(); g.close()
        with self.assertRaises(RuntimeError):g.begin()

if __name__=='__main__':unittest.main()
