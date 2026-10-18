import unittest
from local_diagnostic_summary import summarize_local_clients
from windows_client_health import inspect_clients

class LocalDiagnosticSummaryTests(unittest.TestCase):
    def report(self, available):
        return inspect_clients(which=lambda name: 'C:/bin/'+name if name in available else None, platform='nt')
    def test_all_ready(self):
        headline, advice = summarize_local_clients(self.report({'ssh','sftp','mstsc','vncviewer'}))
        self.assertEqual(headline, 'Clients locaux disponibles : 4/4')
        self.assertIn('pas été vérifiée', advice)
    def test_missing_clients(self):
        headline, advice = summarize_local_clients(self.report({'ssh'}))
        self.assertEqual(headline, 'Clients locaux disponibles : 1/4')
        self.assertIn('SFTP', advice)
    def test_unsupported_platform(self):
        report = inspect_clients(which=lambda name: '/usr/bin/'+name, platform='posix')
        self.assertIn('RDP', summarize_local_clients(report)[1])
    def test_empty_inventory(self):
        self.assertIn('Aucun', summarize_local_clients({'scope':'local_only','network_tested':False,'rows':[]})[1])
    def test_reject_remote_scope(self):
        with self.assertRaises(ValueError): summarize_local_clients({'scope':'remote','network_tested':False,'rows':[]})
    def test_reject_network_probe(self):
        with self.assertRaises(ValueError): summarize_local_clients({'scope':'local_only','network_tested':True,'rows':[]})
    def test_reject_unknown_protocol(self):
        with self.assertRaises(ValueError): summarize_local_clients({'scope':'local_only','network_tested':False,'rows':[{'protocol':'TELNET'}]})
    def test_qt_wiring(self):
        from pathlib import Path
        code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('localReadinessSummary',code)
        self.assertIn('summarize_local_clients(report)',code)
