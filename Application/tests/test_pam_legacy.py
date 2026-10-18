import json,tempfile,unittest
from pathlib import Path
from routes import RouteStore
class LegacyPamTests(unittest.TestCase):
 def test_legacy_invalid_loads_without_data_loss(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'routes.json'
   p.write_text(json.dumps([{'id':'old','route':{'mode':'direct','vault_ref':'legacy-name'}},
                            {'id':'good','route':{'mode':'direct','vault_ref':'cyberark:Safe/A'}}]))
   store=RouteStore(p)
   self.assertIn('old',store.invalid_routes)
   self.assertEqual(store.raw_for_edit('old')['vault_ref'],'legacy-name')
   with self.assertRaises(ValueError):store.for_connection('old')
   self.assertEqual(store.for_connection('good')['vault_ref'],'cyberark:Safe/A')
   self.assertIn('legacy-name',p.read_text())
 def test_fix_preserves_other_routes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'routes.json'
   p.write_text(json.dumps([{'id':'old','route':{'mode':'direct','vault_ref':'bad ref'}},
                            {'id':'good','route':{'mode':'direct','vault_ref':'generic:ID'}}]))
   store=RouteStore(p)
   store.set_route('old',{'mode':'direct','vault_ref':'delinea:Safe/Account'})
   self.assertNotIn('old',store.invalid_routes)
   self.assertEqual(len(RouteStore(p).items),2)
 def test_reject_invalid_new_ref(self):
  with tempfile.TemporaryDirectory() as d:
   store=RouteStore(Path(d)/'routes.json')
   with self.assertRaises(ValueError):store.set_route('x',{'mode':'direct','vault_ref':'password=abc'})
 def test_remove_quarantined(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'routes.json'
   p.write_text(json.dumps([{'id':'old','route':{'mode':'direct','vault_ref':'legacy'}}]))
   store=RouteStore(p);store.remove_route('old')
   self.assertFalse(store.invalid_routes)
   self.assertEqual(RouteStore(p).items,[])
