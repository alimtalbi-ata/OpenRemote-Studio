import tempfile
import unittest
from pathlib import Path
from ssh_route_scope import route_token,validate_token
from ssh_diagnostic_history import DiagnosticHistory

REPORT={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[{'step':'Bastion principal','state':'ok','duration_ms':100}]}
class ScopeTests(unittest.TestCase):
    def test_stable(self):self.assertEqual(route_token('route-A',b'x'*32),route_token('route-A',b'x'*32))
    def test_different_routes(self):self.assertNotEqual(route_token('A',b'x'*32),route_token('B',b'x'*32))
    def test_different_secrets(self):self.assertNotEqual(route_token('A',b'x'*32),route_token('A',b'y'*32))
    def test_short_key(self):
        with self.assertRaises(ValueError):route_token('A',b'bad')
    def test_invalid_descriptor(self):
        with self.assertRaises(ValueError):route_token('\n',b'x'*32)
    def test_invalid_token(self):
        with self.assertRaises(ValueError):validate_token('bad')
    def test_scoped_history(self):
        with tempfile.TemporaryDirectory() as d:
            h=DiagnosticHistory(Path(d)/'h.db');a=route_token('A',b'x'*32);b=route_token('B',b'x'*32)
            h.add(REPORT,route_id=a);h.add(REPORT,route_id=b);h.add(REPORT)
            self.assertEqual(len(h.filtered(route_id=a)),1)
            self.assertEqual(len(h.filtered(route_id=b)),1)
            self.assertEqual(len(h.filtered()),3)
            self.assertEqual(h.statistics(route_id=a)['count'],1)
    def test_scoped_clear(self):
        with tempfile.TemporaryDirectory() as d:
            h=DiagnosticHistory(Path(d)/'h.db');h.add(REPORT,route_id=route_token('A',b'x'*32));h.clear()
            self.assertEqual(h.statistics()['count'],0)
    def test_no_identity_in_db(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'h.db';h=DiagnosticHistory(p);h.add(REPORT,route_id=route_token('sensitive-route-name',b'x'*32))
            self.assertNotIn(b'sensitive-route-name',p.read_bytes())
if __name__=='__main__':unittest.main()
