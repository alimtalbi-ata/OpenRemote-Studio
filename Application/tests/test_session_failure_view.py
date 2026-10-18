import unittest
from pathlib import Path
from session_view import filter_sessions,session_counts
class FailureViewTests(unittest.TestCase):
 def setUp(self):
  self.rows=[dict(name='ok',protocol='SSH',pid=1,connection_id='a',status='running',exit_code=None),
   dict(name='done',protocol='RDP',pid=2,connection_id='b',status='exited',exit_code=0),
   dict(name='failed',protocol='SFTP',pid=3,connection_id='c',status='exited',exit_code=255)]
 def test_failure_filter(self):
  self.assertEqual([x['name'] for x in filter_sessions(self.rows,state='failed')],['failed'])
 def test_failure_count(self):
  self.assertEqual(session_counts(self.rows),{'total':3,'running':1,'exited':2,'failed':1,'unknown':0})
 def test_failure_search(self):
  self.assertEqual(len(filter_sessions(self.rows,'SFTP','failed')),1)
 def test_unknown_filter(self):
  with self.assertRaises(ValueError):filter_sessions(self.rows,state='unexpected')
 def test_ui_wired(self):
  source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn("('En erreur','failed')",source)
  self.assertIn('def clear_exited_overview(self):',source)
