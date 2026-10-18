"""PTY UTF-8 stream decoding and shutdown contract. Author: Abdelhalim Talbi."""
import unittest
from unittest.mock import Mock
from pty_session import PtyShell

class TestPtyV81(unittest.TestCase):
    def make(self):return PtyShell({'protocol':'SSH','host':'example.org'})
    def test_utf8_split_multibyte(self):
        p=self.make();self.assertEqual(p._decoder.decode(b'\xe2',False),'');self.assertEqual(p._decoder.decode(b'\x82\xac',False),'€')
    def test_utf8_incomplete_flush(self):
        p=self.make();self.assertEqual(p._decoder.decode(b'\xe2',False),'');self.assertEqual(p._decoder.decode(b'',True),'�')
    def test_stop_without_connection(self):
        p=self.make();p.stop();self.assertTrue(p.shutdown.is_set())
    def test_stop_closes_channel_and_client(self):
        p=self.make();p.channel=Mock();p.client=Mock();p.stop();p.channel.close.assert_called_once();p.client.close.assert_called_once()
    def test_stop_idempotent(self):
        p=self.make();p.stop();p.stop();self.assertTrue(p.shutdown.is_set())
    def test_stop_channel_oserror(self):
        p=self.make();p.channel=Mock();p.channel.close.side_effect=OSError('closed');p.stop();self.assertTrue(p.shutdown.is_set())
    def test_stop_client_oserror(self):
        p=self.make();p.client=Mock();p.client.close.side_effect=OSError('closed');p.stop();self.assertTrue(p.shutdown.is_set())
