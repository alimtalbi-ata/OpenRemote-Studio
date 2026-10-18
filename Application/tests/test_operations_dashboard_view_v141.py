import unittest
from operations_dashboard_view import filtered_rows
class FilterTests(unittest.TestCase):
    def setUp(self):
        self.report={'rows':[{'id':'a','protocol':'SSH'},{'id':'b','protocol':'RDP'},{'id':'c','protocol':'SSH'}]}
        self.names={'a':'Serveur alpha','b':'Bureau distant','c':'Prod beta'}
    def test_all(self):self.assertEqual(len(filtered_rows(self.report,self.names)),3)
    def test_protocol(self):self.assertEqual(len(filtered_rows(self.report,self.names,'SSH')),2)
    def test_search(self):self.assertEqual(filtered_rows(self.report,self.names,query='ALPHA')[0]['id'],'a')
    def test_combined(self):self.assertEqual(filtered_rows(self.report,self.names,'RDP','bureau')[0]['id'],'b')
    def test_empty(self):self.assertEqual(filtered_rows(self.report,self.names,'VNC'),[])
    def test_invalid_protocol(self):
        with self.assertRaises(ValueError):filtered_rows(self.report,self.names,'BAD')
    def test_invalid_query(self):
        with self.assertRaises(ValueError):filtered_rows(self.report,self.names,query='x'*201)
    def test_invalid_report(self):
        with self.assertRaises(ValueError):filtered_rows([],self.names)
    def test_no_name_leak_in_backend(self):self.assertNotIn('Serveur alpha',str(self.report))
if __name__=='__main__':unittest.main()
