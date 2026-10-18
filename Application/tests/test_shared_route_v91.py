import unittest, threading
from ssh_route_client import RoutedSshClient
from test_route_unified_v90 import Fake, Client

class Tests(unittest.TestCase):
    def setUp(self):Client.instances=[]
    def test_events_direct(self):
        events=[]
        c=RoutedSshClient({'host':'target'},paramiko_module=Fake,on_stage=lambda *a:events.append(a)).connect()
        self.assertEqual(events,[('target_connect','starting'),('target_connect','ok')]);c.close()
    def test_cancelled(self):
        flag=threading.Event();flag.set()
        c=RoutedSshClient({'host':'target'},paramiko_module=Fake,cancelled=flag)
        with self.assertRaises(InterruptedError):c.connect()
        self.assertEqual(c.clients,[])
    def test_keepalive_rejected(self):
        for x in (-1,1,301,True):
            with self.assertRaises(ValueError):RoutedSshClient({'host':'target'},paramiko_module=Fake,keepalive=x)
    def test_active_transport(self):
        c=RoutedSshClient({'host':'target'},paramiko_module=Fake).connect()
        self.assertTrue(c.transports_active());c.close();self.assertFalse(c.transports_active())
    def test_target_client(self):
        c=RoutedSshClient({'host':'target'},paramiko_module=Fake).connect()
        self.assertIs(c.target_client,Client.instances[-1]);c.close()
        with self.assertRaises(RuntimeError):_ = c.target_client
