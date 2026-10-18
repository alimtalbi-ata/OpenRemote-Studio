import unittest
from pathlib import Path
from local_readiness_filter import visible_local_clients

class LocalReadinessFilterTests(unittest.TestCase):
    def setUp(self):
        self.report = {'rows': [
            {'protocol':'SSH','client':'ssh.exe','status':'prêt','ready':True},
            {'protocol':'VNC','client':'viewer','status':'absent','ready':False},
            {'protocol':'RDP','client':'mstsc','status':'inconnu','ready':None},
        ]}
    def test_all_clients(self):
        rows, shown, total = visible_local_clients(self.report)
        self.assertEqual((shown,total),(3,3))
        self.assertEqual(len(rows),3)
    def test_issues_only(self):
        rows, shown, total = visible_local_clients(self.report, True)
        self.assertEqual((shown,total),(2,3))
        self.assertEqual([r[0] for r in rows],['VNC','RDP'])
    def test_does_not_mutate(self):
        original = repr(self.report)
        visible_local_clients(self.report,True)
        self.assertEqual(repr(self.report),original)
    def test_invalid_report(self):
        with self.assertRaises(ValueError): visible_local_clients({'rows':None})
    def test_malformed_rows_rejected(self):
        with self.assertRaises(ValueError): visible_local_clients({'rows':[None]})
    def test_ui_wired(self):
        ui=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('issues_only.toggled.connect',ui)
        self.assertIn('visible_local_clients(report, issues_only.isChecked())',ui)
