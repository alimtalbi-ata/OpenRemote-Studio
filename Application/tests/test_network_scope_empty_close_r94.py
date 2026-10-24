"""R94 empty-scope shutdown must complete without a scheduled cleanup thread.

No network; protects SSH fail-closed cleanup on busy Windows runners.
Author: Abdelhalim Talbi.
"""
import threading
import unittest
from network_resource_scope import NetworkResourceScope


class EmptyScopeR94Tests(unittest.TestCase):
    def test_empty_scope_close_is_immediately_drained(self):
        scope = NetworkResourceScope()
        self.assertFalse(scope.wait_closed(0))
        self.assertTrue(scope.close())
        self.assertTrue(scope.cancelled)
        self.assertTrue(scope.closed)
        self.assertTrue(scope.wait_closed(0))
        self.assertFalse(scope.close())

    def test_concurrent_empty_close_is_idempotent(self):
        scope = NetworkResourceScope()
        start = threading.Event()
        results = []
        def closer():
            start.wait()
            results.append(scope.close())
        threads = [threading.Thread(target=closer) for _ in range(8)]
        for t in threads: t.start()
        start.set()
        for t in threads: t.join(timeout=3)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 7)
        self.assertTrue(scope.wait_closed(0))


if __name__ == '__main__':
    unittest.main()
