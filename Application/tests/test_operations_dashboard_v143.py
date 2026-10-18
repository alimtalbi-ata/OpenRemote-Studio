import unittest
from operations_dashboard_view import filtered_rows, diagnostic_hint

class TestDashboardV143(unittest.TestCase):
    def setUp(self):
        self.report={'rows':[{'id':'a','protocol':'SSH','status':'attention'}, {'id':'b','protocol':'RDP','status':'observed'}, {'id':'c','protocol':'SSH','status':'not_tested'}]}
        self.names={'a':'Alpha','b':'Beta','c':'Gamma'}
    def test_attention(self):self.assertEqual([x['id'] for x in filtered_rows(self.report,self.names,status='attention')],['a'])
    def test_not_tested(self):self.assertEqual([x['id'] for x in filtered_rows(self.report,self.names,status='not_tested')],['c'])
    def test_combined(self):self.assertEqual([x['id'] for x in filtered_rows(self.report,self.names,'SSH','ga','not_tested')],['c'])
    def test_invalid(self):
        with self.assertRaises(ValueError):filtered_rows(self.report,self.names,status='secret')
    def test_attention_hint(self):self.assertIn('Échecs locaux',diagnostic_hint({'status':'attention'}))
    def test_observed_hint(self):self.assertIn('non vérifié',diagnostic_hint({'status':'observed'}))
    def test_unknown_hint(self):self.assertIn('inconnu',diagnostic_hint({'status':'anything'}))
    def test_invalid_hint(self):
        with self.assertRaises(ValueError):diagnostic_hint(None)
