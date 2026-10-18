import tempfile,unittest
from pathlib import Path
from routes import RouteStore
class RouteCleanupTests(unittest.TestCase):
 def test_remove_route(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'routes.json'
   r=RouteStore(path)
   r.set_route('a',{'mode':'ssh_jump','jump_host':'bastion.example'})
   r.set_route('b',{'mode':'direct'})
   r.remove_route('a')
   reload=RouteStore(path)
   self.assertEqual(reload.for_connection('a'),{})
   self.assertEqual(reload.for_connection('b')['mode'],'direct')
 def test_remove_unknown_is_safe(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=RouteStore(Path(tmp)/'routes.json')
   r.remove_route('not-found')
   self.assertEqual(r.items,[])
