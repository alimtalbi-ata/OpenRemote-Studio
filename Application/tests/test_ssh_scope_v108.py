"""V10.8: scoped SQLite queries and key handling regressions."""
import tempfile
import unittest
from pathlib import Path
from ssh_diagnostic_history import DiagnosticHistory
from ssh_route_scope import route_token

REPORT={'schema':'openremote.ssh-diagnostic.v1','status':'authenticated','steps':[{'step':'Bastion principal','state':'ok','duration_ms':120}]}

class ScopedHistoryTests(unittest.TestCase):
    def test_scoped_filter_with_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=DiagnosticHistory(Path(tmp)/'history.sqlite3')
            a=route_token('route-a',b'x'*32)
            b=route_token('route-b',b'x'*32)
            db.add(REPORT,route_id=a);db.add(REPORT,route_id=b);db.add(REPORT)
            self.assertEqual(len(db.filtered(route_id=a)),1)
            self.assertEqual(len(db.filtered(route_id=b)),1)
            self.assertEqual(len(db.filtered()),3)
            self.assertEqual(db.statistics(route_id=a)['count'],1)
    def test_scoped_status_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=DiagnosticHistory(Path(tmp)/'history.sqlite3')
            token=route_token('a',b'x'*32)
            db.add(REPORT,route_id=token)
            self.assertEqual(len(db.filtered(route_id=token,status='authenticated',since=0)),1)
            self.assertEqual(len(db.filtered(route_id=token,status='failed')),0)
    def test_distinct_keys_are_distinct_routes(self):
        self.assertNotEqual(route_token('same',b'a'*32),route_token('same',b'b'*32))
    def test_no_plaintext_descriptor_in_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.sqlite3';db=DiagnosticHistory(path)
            db.add(REPORT,route_id=route_token('secret-route-name',b'z'*32))
            self.assertNotIn(b'secret-route-name',path.read_bytes())
    def test_scope_rejects_short_secret(self):
        with self.assertRaises(ValueError):route_token('x',b'123')

if __name__=='__main__':unittest.main()
