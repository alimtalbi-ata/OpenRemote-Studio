import unittest
from dashboard import summarize,command_search
class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.items=[dict(id='1',name='srv-prod',protocol='SSH',host='10.0.0.1',group='prod',tags='linux'),dict(id='2',name='vcenter',protocol='WEB',host='example.org',group='infra',tags='vmware')]
    def test_summary(self):
        d=summarize(self.items,{'favorites':['1','absent'],'recent':['2','absent','1']})
        self.assertEqual(d['total'],2);self.assertEqual(d['favorites'],1);self.assertEqual(d['recent'],['2','1']);self.assertEqual(d['protocols']['SSH'],1)
    def test_search_connection(self):
        self.assertTrue(any(x['action']=='1' for x in command_search('srv-prod',self.items)))
    def test_search_tool(self):
        self.assertTrue(any(x['kind']=='tool' for x in command_search('ping',self.items)))
    def test_limit(self):
        self.assertEqual(len(command_search('',self.items,3)),3)
if __name__=='__main__':unittest.main()
