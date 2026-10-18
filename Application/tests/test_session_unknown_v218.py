import unittest
from pathlib import Path
from session_view import filter_sessions, session_counts

class UnknownSessionsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'name':'prod','protocol':'SSH','pid':12,'connection_id':'a','status':'running','exit_code':None},
            {'name':'edge','protocol':'RDP','pid':13,'connection_id':'b','status':'unknown','exit_code':None},
            {'name':'backup','protocol':'SFTP','pid':14,'connection_id':'c','status':'exited','exit_code':1},
        ]
    def test_unknown_counted_separately(self):
        self.assertEqual(session_counts(self.rows),{'total':3,'running':1,'exited':1,'failed':1,'unknown':1})
    def test_unknown_filter(self):
        self.assertEqual([r['name'] for r in filter_sessions(self.rows,state='unknown')],['edge'])
    def test_unknown_search(self):
        self.assertEqual(len(filter_sessions(self.rows,'RDP','unknown')),1)
    def test_unknown_not_failed(self):
        self.assertEqual([r['name'] for r in filter_sessions(self.rows,state='failed')],['backup'])
    def test_unknown_not_running(self):
        self.assertEqual(len(filter_sessions(self.rows,state='running')),1)
    def test_ui_exposes_unknown_filter(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn("addItem('État inconnu','unknown')",source)
    def test_ui_exposes_unknown_count(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn("counts['unknown']",source)
