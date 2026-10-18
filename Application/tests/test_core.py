import tempfile,unittest
from pathlib import Path
from core import Store,validate
class TestCore(unittest.TestCase):
 def test_validate(self):
  self.assertEqual(validate({'name':'a','host':'server.example','protocol':'ssh'})['protocol'],'SSH')
  for host in ('-oProxyCommand=bad','bad host',''):
   with self.assertRaises(ValueError):validate({'name':'x','host':host,'protocol':'SSH'})
 def test_store(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'connections.json');s.upsert({'name':'server','host':'example.com','protocol':'SSH'})
   self.assertEqual(len(Store(s.path).items),1)
   s.remove(s.items[0]['id']);self.assertEqual(Store(s.path).items,[])
if __name__=='__main__':unittest.main()
