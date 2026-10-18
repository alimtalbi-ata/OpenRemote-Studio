import sys,types,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if 'PySide6' not in sys.modules:
    pass
try:
    from pty_session import validate_pty_target,PtyShell
except ImportError:
    from test_pty_v73 import validate_pty_target,PtyShell

class JumpTests(unittest.TestCase):
    def setUp(self):
        self.c={'protocol':'SSH','host':'target.example','port':22,'user':'admin'}
        self.r={'mode':'ssh_jump','jump_host':'jump.example','jump_user':'ops','jump_port':'2222'}
    def test_jump_valid(self):self.assertEqual(validate_pty_target(self.c,self.r),('target.example',22,'admin'))
    def test_route_normalized(self):self.assertEqual(PtyShell(self.c,self.r).route['jump_port'],'2222')
    def test_missing_jump(self):
        with self.assertRaises(ValueError):validate_pty_target(self.c,{'mode':'ssh_jump'})
    def test_rds_rejected(self):
        with self.assertRaises(ValueError):validate_pty_target(self.c,{'mode':'rd_gateway','gateway_host':'gw.example'})
    def test_bad_target(self):
        with self.assertRaises(ValueError):validate_pty_target({**self.c,'host':'bad host'},self.r)
    def test_bad_jump_port(self):
        with self.assertRaises(ValueError):validate_pty_target(self.c,{**self.r,'jump_port':'65536'})
    def test_no_secret(self):
        obj=PtyShell(self.c,self.r)
        self.assertNotIn('password',str(obj.route))
