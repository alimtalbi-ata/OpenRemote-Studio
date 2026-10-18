import unittest
from remote_tools import safe_remote_path, Tunnel
class TestRemote(unittest.TestCase):
 def test_paths(self):
  self.assertEqual(safe_remote_path('/srv','file.txt'),'/srv/file.txt')
  for name in ('../bad','a/b','..',''):
   with self.assertRaises(ValueError):safe_remote_path('/srv',name)
 def test_tunnel_bind_restriction(self):
  with self.assertRaises(ValueError):Tunnel(None,'0.0.0.0',8080,'localhost',80)
if __name__=='__main__':unittest.main()
