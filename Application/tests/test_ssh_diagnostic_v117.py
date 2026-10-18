import unittest
from ssh_diagnostic_view import compact_stage_rows

class CompactStages(unittest.TestCase):
 def test_empty(self):self.assertEqual(compact_stage_rows([]),[])
 def test_one_row_for_start_and_success(self):
  rows=compact_stage_rows([{'step':'Bastion principal','state':'starting'},{'step':'Bastion principal','state':'ok','duration_ms':42}])
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['duration_ms'],42)
 def test_order(self):
  rows=compact_stage_rows([{'step':'Bastion principal','state':'starting'},{'step':'Serveur cible','state':'ok'}])
  self.assertEqual([r['step'] for r in rows],['Bastion principal','Serveur cible'])
 def test_failure(self):
  rows=compact_stage_rows([{'step':'Serveur cible','state':'starting'},{'step':'Serveur cible','state':'failed'}])
  self.assertEqual(rows[0]['state'],'failed')
 def test_late_start_does_not_override_failure(self):
  rows=compact_stage_rows([{'step':'Serveur cible','state':'failed'},{'step':'Serveur cible','state':'starting'}])
  self.assertEqual(rows[0]['state'],'failed')
 def test_cancelled(self):self.assertEqual(compact_stage_rows([],status='cancelled')[0]['state'],'cancelled')
 def test_reject_secret_label(self):
  with self.assertRaises(ValueError):compact_stage_rows([{'step':'password','state':'ok'}])
 def test_reject_bad_duration(self):
  with self.assertRaises(ValueError):compact_stage_rows([{'step':'Serveur cible','state':'ok','duration_ms':-2}])
