import unittest
from connection_health import summarize_connection

class TestHealth(unittest.TestCase):
    def test_empty(self):
        r=summarize_connection([], 'x')
        self.assertIsNone(r['coverage'])
        self.assertEqual(r['attempts'],0)
    def test_failures(self):
        r=summarize_connection([dict(connection_id='x',attempts=4,observed=3,failed=1,unobserved=1)],'x')
        self.assertEqual(r['coverage'],75.0)
        self.assertEqual(r['failures'],1)
    def test_unknown(self):
        r=summarize_connection([dict(connection_id='x',attempts=1,observed=0,failed=0,unobserved=1)],'x')
        self.assertIn('non observées',r['status'])
    def test_no_failure_not_remote_success(self):
        r=summarize_connection([dict(connection_id='x',attempts=2,observed=2,failed=0,unobserved=0)],'x')
        self.assertIn('ne garantit pas',r['advice'])
    def test_ignore_other_connection(self):
        r=summarize_connection([dict(connection_id='y',attempts=5,observed=5,failed=5,unobserved=0)],'x')
        self.assertEqual(r['attempts'],0)
