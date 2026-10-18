import unittest
from dashboard import quick_access

class QuickAccessV214Tests(unittest.TestCase):
    def setUp(self):
        self.items=[dict(id=str(i),name='Server '+str(i),protocol='SSH',host='host'+str(i)) for i in range(1,5)]
    def test_favorites_before_recent(self):
        self.assertEqual([x['id'] for x in quick_access(self.items,{'favorites':['3'],'recent':['2','1']})],['3','2','1'])
    def test_duplicate_deduped(self):
        self.assertEqual([x['id'] for x in quick_access(self.items,{'favorites':['1'],'recent':['1','2']})],['1','2'])
    def test_deleted_ignored(self):
        self.assertEqual([x['id'] for x in quick_access(self.items,{'favorites':['gone'],'recent':['2']})],['2'])
    def test_limit(self):
        self.assertEqual(len(quick_access(self.items,{'favorites':['1','2'],'recent':['3']},limit=2)),2)
    def test_no_secrets(self):
        self.items[0]['password']='private'
        self.assertNotIn('password',quick_access(self.items,{'favorites':['1']})[0])
    def test_invalid_limit(self):
        for limit in (0,-1,101,True):
            if limit is True:continue
            with self.assertRaises(ValueError):quick_access(self.items,{},limit)
