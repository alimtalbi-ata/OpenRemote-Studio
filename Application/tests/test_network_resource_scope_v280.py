import threading
import unittest
from network_resource_scope import NetworkResourceScope

class Resource:
    def __init__(self):
        self.count = 0
        self.event = threading.Event()
    def close(self):
        self.count += 1
        self.event.set()

class ScopeTests(unittest.TestCase):
    def test_close_then_register(self):
        scope=NetworkResourceScope();self.assertTrue(scope.close())
        r=Resource();self.assertFalse(scope.register(r));self.assertEqual(r.count,1)
    def test_registered_resource_closed(self):
        scope=NetworkResourceScope();r=Resource();self.assertTrue(scope.register(r))
        self.assertTrue(scope.close());self.assertTrue(r.event.wait(2));self.assertFalse(scope.close())
        self.assertEqual(r.count,1)
    def test_race_register_close(self):
        scope=NetworkResourceScope();resources=[Resource() for _ in range(50)]
        t=threading.Thread(target=lambda:[scope.register(r) for r in resources]);t.start()
        scope.close();t.join()
        self.assertTrue(all(r.event.wait(2) for r in resources))
        self.assertTrue(all(r.count==1 for r in resources))
