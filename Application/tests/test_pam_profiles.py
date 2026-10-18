import tempfile,unittest
from pathlib import Path
from pam_profiles import PamProfileStore,validate_profile
class PamProfileTests(unittest.TestCase):
 def test_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'pam.json'
   s=PamProfileStore(path);s.set_profile({'name':'Prod','provider':'cyberark','endpoint':'https://pam.example/'})
   self.assertEqual(PamProfileStore(path).items[0]['endpoint'],'https://pam.example')
 def test_no_password_url(self):
  for endpoint in ('https://user:pass@pam.example','http://pam.example','https://pam.example/?token=x',
                   'https://pam.example/#fragment','https://pam.example/ bad'):
   with self.subTest(endpoint=endpoint),self.assertRaises(ValueError):
    validate_profile({'name':'Prod','provider':'delinea','endpoint':endpoint})
 def test_unknown_provider(self):
  with self.assertRaises(ValueError):
   validate_profile({'name':'Prod','provider':'unknown','endpoint':'https://pam.example'})
 def test_update_without_duplicates(self):
  with tempfile.TemporaryDirectory() as d:
   s=PamProfileStore(Path(d)/'pam.json')
   s.set_profile({'name':'Prod','provider':'cyberark','endpoint':'https://one.example'})
   s.set_profile({'name':'Prod','provider':'beyondtrust','endpoint':'https://two.example'})
   self.assertEqual(len(s.items),1)
   self.assertEqual(s.items[0]['provider'],'beyondtrust')
 def test_remove(self):
  with tempfile.TemporaryDirectory() as d:
   s=PamProfileStore(Path(d)/'pam.json')
   s.set_profile({'name':'Prod','provider':'generic','endpoint':'https://pam.example'})
   s.remove_profile('Prod')
   self.assertEqual(PamProfileStore(Path(d)/'pam.json').items,[])
