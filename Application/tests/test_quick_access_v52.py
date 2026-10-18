import unittest
from dashboard import quick_access
class QuickAccessTests(unittest.TestCase):
 def setUp(self):
  self.c=[{'id':'a','name':'Alpha','protocol':'SSH','host':'a'}, {'id':'b','name':'Beta','protocol':'RDP','host':'b'}]
 def test_favorites_first(self):
  self.assertEqual([x['id'] for x in quick_access(self.c,{'favorites':['b'],'recent':['a','b']})],['b','a'])
 def test_deduplicates(self):
  self.assertEqual(len(quick_access(self.c,{'favorites':['a'],'recent':['a']})),1)
 def test_stale_ids_ignored(self):
  self.assertEqual(quick_access(self.c,{'favorites':['missing'],'recent':[]}),[])
 def test_limit(self):
  self.assertEqual(len(quick_access(self.c,{'favorites':['a','b']},1)),1)
 def test_invalid_limit(self):
  with self.assertRaises(ValueError):quick_access(self.c,{},0)
