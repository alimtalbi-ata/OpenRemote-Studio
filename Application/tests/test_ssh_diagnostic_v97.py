import unittest
from ssh_diagnostic_view import stage_rows
from ssh_end_to_end_probe import probe
from ssh_route_client import RoutedSshClient
class Tests(unittest.TestCase):
 def test_ok(self):self.assertEqual(stage_rows([{'step':'Bastion principal','state':'ok'}])[0]['label'],'RÉUSSI')
 def test_target(self):self.assertEqual(stage_rows([{'step':'Serveur cible','state':'failed'}])[0]['state'],'failed')
 def test_cancelled(self):self.assertEqual(stage_rows([],status='cancelled')[-1]['label'],'ANNULÉ')
 def test_secret_rejected(self):
  with self.assertRaises(ValueError):stage_rows([{'step':'secret-password','state':'ok'}])
 def test_unknown_status(self):
  with self.assertRaises(ValueError):stage_rows([{'step':'Serveur cible','state':'secret'}])
 def test_many(self):
  with self.assertRaises(ValueError):stage_rows([{'step':'Serveur cible','state':'ok'}]*25)
 def test_timeout_validation(self):
  with self.assertRaises(ValueError):probe([], 'example.com',consent=True,connect_timeout=0)
 def test_route_timeout_validation(self):
  with self.assertRaises(ValueError):RoutedSshClient({'host':'example.com','port':22},connect_timeout=21,paramiko_module=object())
