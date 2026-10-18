import unittest
from session_view import filter_sessions,session_counts
ROWS=[{'name':'Serveur PROD','protocol':'SSH','pid':101,'connection_id':'a','status':'running'},
      {'name':'Bastion','protocol':'RDP','pid':202,'connection_id':'b','status':'exited'}]
class SessionViewTests(unittest.TestCase):
 def test_counts(self):self.assertEqual(session_counts(ROWS),{'total':2,'running':1,'exited':1,'failed':0,'unknown':0})
 def test_filter_status(self):self.assertEqual(len(filter_sessions(ROWS,state='running')),1)
 def test_filter_casefold(self):self.assertEqual(filter_sessions(ROWS,'prod')[0]['pid'],101)
 def test_filter_pid(self):self.assertEqual(filter_sessions(ROWS,'202')[0]['name'],'Bastion')
 def test_invalid_state(self):
  with self.assertRaises(ValueError):filter_sessions(ROWS,state='invalid')
 def test_does_not_modify_input(self):
  filter_sessions(ROWS,'none');self.assertEqual(len(ROWS),2)
