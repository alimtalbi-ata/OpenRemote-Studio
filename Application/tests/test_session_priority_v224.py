import unittest
from session_view import prioritized_sessions,filter_sessions

class SessionPriorityTests(unittest.TestCase):
 def setUp(self):
  self.rows=[{'status':'exited','exit_code':0,'pid':1}, {'status':'unknown','pid':2}, {'status':'running','pid':3}, {'status':'exited','exit_code':2,'pid':4}, {'status':'running','pid':5}]
 def test_priority(self):self.assertEqual([r['pid'] for r in prioritized_sessions(self.rows)],[3,5,2,4,1])
 def test_stable_within_class(self):self.assertEqual([r['pid'] for r in prioritized_sessions(self.rows)[:2]],[3,5])
 def test_immutable(self):
  old=list(self.rows);prioritized_sessions(self.rows);self.assertEqual(self.rows,old)
 def test_empty(self):self.assertEqual(prioritized_sessions([]),[])
 def test_unknown_status_last(self):self.assertEqual(prioritized_sessions([{'status':'other'},{'status':'running'}])[0]['status'],'running')
 def test_filter_compatible(self):self.assertEqual([r['pid'] for r in prioritized_sessions(filter_sessions(self.rows,state='running'))],[3,5])
 def test_failed_before_success(self):self.assertEqual([r['pid'] for r in prioritized_sessions(self.rows) if r['status']=='exited'],[4,1])
