import json, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
from core import Store,validate
class TestCore(unittest.TestCase):
 def test_validate(self):
  self.assertEqual(validate({'name':'a','host':'server.example','protocol':'ssh'})['protocol'],'SSH')
  for host in ('-oProxyCommand=bad','bad host',''):
   with self.assertRaises(ValueError):validate({'name':'x','host':host,'protocol':'SSH'})
 def test_port_bounds_and_user_controls(self):
  for port in ('0','65536','abc'):
   with self.assertRaises(ValueError):
    validate({'name':'x','host':'server.example','protocol':'SSH','port':port})
  for user in ('alice' + chr(10) + 'admin', 'alice' + chr(13) + 'admin', 'alice' + chr(0) + 'admin'):
   with self.assertRaises(ValueError):
    validate({'name':'x','host':'server.example','protocol':'SSH','user':user})
 def test_web_url_rejects_embedded_credentials(self):
  for host in ('https://alice:secret@example.com','https://alice@example.com'):
   with self.assertRaises(ValueError):
    validate({'name':'portal','host':host,'protocol':'WEB'})
 def test_duplicate_ids_rejected_on_load(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'connections.json'
   item={'id':'same','name':'one','host':'one.example','protocol':'SSH'}
   path.write_text(json.dumps([item,{**item,'name':'two','host':'two.example'}]),encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'dupliqués'):
    Store(path)
 def test_upsert_rolls_back_memory_on_save_failure(self):
  with tempfile.TemporaryDirectory() as d:
   store=Store(Path(d)/'connections.json')
   store.upsert({'name':'original','host':'one.example','protocol':'SSH'})
   before=list(store.items)
   with patch.object(store,'save',side_effect=OSError('simulated disk failure')):
    with self.assertRaises(OSError):
     store.upsert({'name':'replacement','host':'two.example','protocol':'SSH'})
   self.assertEqual(store.items,before)
 def test_store(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'connections.json');s.upsert({'name':'server','host':'example.com','protocol':'SSH'})
   self.assertEqual(len(Store(s.path).items),1)
   s.remove(s.items[0]['id']);self.assertEqual(Store(s.path).items,[])
if __name__=='__main__':unittest.main()
