import threading
import unittest
from ssh_callback_gate import SSHCallbackGate

class GateV265Tests(unittest.TestCase):
    def test_stale_cleanup_runs_outside_lock(self):
        gate = SSHCallbackGate()
        old = gate.begin()
        gate.invalidate()
        results = []
        class Resource:
            def close(self):
                t = threading.Thread(target=lambda: results.append(gate.begin()))
                t.start()
                t.join(timeout=1)
                self.thread_alive = t.is_alive()
        resource = Resource()
        self.assertFalse(gate.deliver(old, resource, lambda _: None))
        self.assertFalse(resource.thread_alive, 'stale cleanup must not hold gate lock')
        self.assertEqual(len(results), 1)

    def test_current_result_delivered(self):
        gate=SSHCallbackGate(); generation=gate.begin(); got=[]
        self.assertTrue(gate.deliver(generation, 'ok', got.append))
        self.assertEqual(got, ['ok'])

    def test_closed_result_cleanup(self):
        gate=SSHCallbackGate(); generation=gate.begin(); gate.close()
        class Resource:
            closed=False
            def close(self): self.closed=True
        r=Resource(); self.assertFalse(gate.deliver(generation,r,lambda _:None))
        self.assertTrue(r.closed)
