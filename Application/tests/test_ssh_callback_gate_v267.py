import threading
import unittest
from ssh_callback_gate import SSHCallbackGate

class GateV267Tests(unittest.TestCase):
    def test_stale_resource_close_outside_lock(self):
        gate=SSHCallbackGate(); old=gate.begin(); gate.invalidate()
        testcase=self
        class Resource:
            def close(self):
                completed=[]
                t=threading.Thread(target=lambda: (gate.invalidate(), completed.append(True)))
                t.start(); t.join(timeout=1)
                if t.is_alive(): testcase.fail('deadlock: close held the gate lock')
                testcase.assertTrue(completed)
        self.assertFalse(gate.deliver(old,Resource(),lambda _: self.fail('stale delivered')))
    def test_rejected_resource_close_error_visible(self):
        gate=SSHCallbackGate(); old=gate.begin(); gate.invalidate()
        class Resource:
            def close(self): raise OSError('close failed')
        with self.assertRaisesRegex(OSError,'close failed'):
            gate.deliver(old,Resource(),lambda _:None)
    def test_delivery_then_cancel(self):
        gate=SSHCallbackGate(); generation=gate.begin(); received=[]
        self.assertTrue(gate.deliver(generation,object(),received.append))
        self.assertEqual(len(received),1)
        gate.invalidate()
        self.assertFalse(gate.deliver_error(generation,RuntimeError('late'),received.append))

if __name__=='__main__': unittest.main()
