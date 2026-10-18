import unittest
from session_lifecycle import SessionLifecycle, State, InvalidTransition

class TestLifecycle(unittest.TestCase):
    def test_normal(self):
        s=SessionLifecycle('a');s.transition(State.CONNECTING);s.transition(State.CONNECTED);s.transition(State.DISCONNECTING);self.assertEqual(s.transition(State.CLOSED),State.CLOSED)
    def test_invalid(self):
        s=SessionLifecycle('a');self.assertRaises(InvalidTransition,s.transition,State.CONNECTED)
    def test_cancel(self):
        s=SessionLifecycle('a');s.transition(State.CONNECTING);self.assertEqual(s.cancel(),State.CANCELLED)
    def test_timeout(self):
        s=SessionLifecycle('a',timeout_seconds=1);s.transition(State.CONNECTING);self.assertTrue(s.expire(s.started_at+2));self.assertEqual(s.state,State.FAILED)
    def test_no_timeout_connected(self):
        s=SessionLifecycle('a');s.transition(State.CONNECTING);s.transition(State.CONNECTED);self.assertFalse(s.expire(999999999))
    def test_closed_terminal(self):
        s=SessionLifecycle('a');s.transition(State.CLOSED);self.assertRaises(InvalidTransition,s.transition,State.CONNECTING)
    def test_retry_failed(self):
        s=SessionLifecycle('a');s.transition(State.CONNECTING);s.transition(State.FAILED);self.assertEqual(s.transition(State.CONNECTING),State.CONNECTING)
    def test_no_cancel_connected(self):
        s=SessionLifecycle('a');s.transition(State.CONNECTING);s.transition(State.CONNECTED);self.assertRaises(InvalidTransition,s.cancel)
