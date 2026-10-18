import unittest
from ssh_callback_gate import SSHCallbackGate

class Resource:
    def __init__(self, fail=False): self.closed=0; self.fail=fail
    def close(self):
        self.closed += 1
        if self.fail: raise OSError('close failed')

class GateV264Tests(unittest.TestCase):
    def test_latest_result_delivered(self):
        gate=SSHCallbackGate(); token=gate.begin(); got=[]; resource=Resource()
        self.assertTrue(gate.deliver(token,resource,got.append)); self.assertEqual(got,[resource])
    def test_stale_resource_closed(self):
        gate=SSHCallbackGate(); token=gate.begin(); gate.invalidate(); resource=Resource()
        self.assertFalse(gate.deliver(token,resource,lambda r:self.fail('stale delivery'))); self.assertEqual(resource.closed,1)
    def test_closed_gate_rejects_and_closes(self):
        gate=SSHCallbackGate(); token=gate.begin(); gate.close(); resource=Resource()
        self.assertFalse(gate.deliver(token,resource,lambda r:self.fail('closed delivery'))); self.assertEqual(resource.closed,1)
    def test_stale_error_suppressed(self):
        gate=SSHCallbackGate(); token=gate.begin(); gate.invalidate(); received=[]
        self.assertFalse(gate.deliver_error(token,OSError('old'),received.append)); self.assertFalse(received)
    def test_close_error_not_silenced(self):
        gate=SSHCallbackGate(); token=gate.begin(); gate.invalidate()
        with self.assertRaisesRegex(OSError,'close failed'): gate.deliver(token,Resource(fail=True),lambda _:None)

if __name__=='__main__': unittest.main()
