import ast,tempfile,unittest
from pathlib import Path
from routes import RouteStore
class PamIntegrationTests(unittest.TestCase):
 def test_valid_ref_persists(self):
  with tempfile.TemporaryDirectory() as d:
   store=RouteStore(Path(d)/'routes.json')
   store.set_route('abc',{'mode':'direct','vault_ref':'cyberark:Safe/Account01'})
   store2=RouteStore(Path(d)/'routes.json')
   self.assertEqual(store2.for_connection('abc')['vault_ref'],'cyberark:Safe/Account01')
 def test_invalid_ref_rejected_before_save(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'routes.json';store=RouteStore(path)
   with self.assertRaises(ValueError):
    store.set_route('abc',{'mode':'direct','vault_ref':'delinea:password=123'})
   self.assertFalse(path.exists())
 def test_ui_status_exists(self):
  source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  ast.parse(source)
  self.assertIn("('État PAM',self.show_pam_status)",source)
  self.assertIn('def show_pam_status(self):',source)
 def test_no_secret_broker_claim(self):
  source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
  self.assertIn('Ouverture de session PAM : NON DISPONIBLE',source)
