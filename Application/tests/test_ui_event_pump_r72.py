"""R72: a broken UI callback must not block subsequent UI events.

Headless event-pump test; does not assert real Windows GUI behavior.
Author: Abdelhalim Talbi.
"""
import queue
import unittest
from unittest.mock import Mock
from app import App


class UIEventPumpTests(unittest.TestCase):
    def test_callback_failure_does_not_drop_following_event(self):
        app = App.__new__(App)
        app._closing = False
        app.ui_events = queue.Queue()
        app.events = queue.Queue()
        app.sessions = []
        app.root = Mock()
        messages = []
        app.note = messages.append
        calls = []

        def broken():
            raise RuntimeError('synthetic callback failure')

        app.ui_events.put(({'closed': False}, broken, ()))
        app.ui_events.put(({'closed': False}, lambda: calls.append('second'), ()))
        app.poll()
        self.assertEqual(calls, ['second'])
        self.assertEqual(len(messages), 1)
        self.assertIn('synthetic callback failure', messages[0])
        app.root.after.assert_called_once()


if __name__ == '__main__':
    unittest.main()
