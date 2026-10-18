import unittest
from ssh_session_state import Lifecycle,SessionState,classify_failure

class TestSSHSessionState(unittest.TestCase):
    def test_normal(self):
        life=Lifecycle()
        for s in ('connecting','connected','closed'):self.assertTrue(life.transition(s))
        self.assertEqual(life.state,SessionState.CLOSED)
    def test_stop_before_connect(self):
        life=Lifecycle();life.transition('stopping');life.transition('closed')
    def test_connect_failure(self):
        life=Lifecycle();life.transition('connecting');life.transition('failed');life.transition('closed')
    def test_no_reconnect_after_close(self):
        life=Lifecycle();life.transition('stopping');life.transition('closed')
        with self.assertRaises(ValueError):life.transition('connecting')
    def test_idempotent(self):
        life=Lifecycle();self.assertFalse(life.transition('new'))
    def test_auth_no_secret(self):
        class AuthenticationException(Exception):pass
        self.assertNotIn('SECRET',classify_failure(AuthenticationException('SECRET')))
    def test_network_error(self):
        self.assertIn('réseau',classify_failure(OSError('my-private-host')))
    def test_timeout(self):self.assertIn('Délai',classify_failure(TimeoutError()))
if __name__=='__main__':unittest.main()
