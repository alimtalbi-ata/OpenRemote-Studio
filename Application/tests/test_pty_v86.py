"""Keepalive and cancellation regression tests. Author: Abdelhalim Talbi."""
import unittest
from pty_session import PtyShell

class TestPtyV86(unittest.TestCase):
    def make(self):return PtyShell({'protocol':'SSH','host':'example.org'})
    def test_default_keepalive(self):self.assertEqual(self.make()._keepalive_seconds,30)
    def test_disable_keepalive(self):
        p=self.make();p.configure_keepalive(0);self.assertEqual(p._keepalive_seconds,0)
    def test_min_keepalive(self):
        p=self.make();p.configure_keepalive(10);self.assertEqual(p._keepalive_seconds,10)
    def test_max_keepalive(self):
        p=self.make();p.configure_keepalive(300);self.assertEqual(p._keepalive_seconds,300)
    def test_invalid_keepalive(self):
        p=self.make()
        for value in (-1,1,9,301,True,30.0,'30',None):
            with self.subTest(value=value),self.assertRaises(ValueError):p.configure_keepalive(value)
    def test_no_send_after_stop(self):
        p=self.make();p.stop();self.assertFalse(p.send_raw('ls'));self.assertFalse(p.send_text('ls'));self.assertTrue(p.commands.empty())
    def test_no_resize_after_stop(self):
        p=self.make();p.stop();p.resize_pty(100,30);self.assertTrue(p.commands.empty())
