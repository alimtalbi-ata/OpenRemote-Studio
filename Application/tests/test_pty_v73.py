import unittest
import sys,types
try:
    from PySide6.QtCore import QThread
except ImportError:
    qt=types.ModuleType('PySide6');core=types.ModuleType('PySide6.QtCore')
    class QThread:
        def __init__(self,*args,**kwargs):pass
    class Signal:
        def __init__(self,*args):pass
    core.QThread=QThread;core.Signal=Signal
    sys.modules.setdefault('PySide6',qt);sys.modules.setdefault('PySide6.QtCore',core)
from pty_session import validate_pty_target,PtyShell
class TestPty(unittest.TestCase):
    def test_direct(self):self.assertEqual(validate_pty_target({'protocol':'SSH','host':'example.org','port':'22','user':'ops'},{}),('example.org',22,'ops'))
    def test_default_port(self):self.assertEqual(validate_pty_target({'protocol':'SFTP','host':'host'},{}),('host',22,''))
    def test_route_rejected(self):
        with self.assertRaises(ValueError):validate_pty_target({'protocol':'SSH','host':'host'},{'mode':'ssh_jump','jump_host':''})
    def test_protocol_rejected(self):
        with self.assertRaises(ValueError):validate_pty_target({'protocol':'RDP','host':'host'},None)
    def test_bad_port(self):
        with self.assertRaises(ValueError):validate_pty_target({'protocol':'SSH','host':'host','port':'70000'},None)
    def test_queue(self):
        w=PtyShell({'protocol':'SSH','host':'host'});self.assertTrue(w.send_text('pwd'));self.assertEqual(w.commands.get_nowait(),('send','pwd\n'))
    def test_reject_nul(self):
        w=PtyShell({'protocol':'SSH','host':'host'});self.assertFalse(w.send_text('a\x00b'))
    def test_resize_bounds(self):
        w=PtyShell({'protocol':'SSH','host':'host'});w.resize_pty(1,1);self.assertTrue(w.commands.empty());w.resize_pty(120,40);self.assertEqual(w.commands.get_nowait(),('resize',120,40))
