import unittest
from ansi_screen import AnsiScreen
from terminal_keys import Qt,encode_key

class TestTerminalV80(unittest.TestCase):
    def test_application_cursor_toggle(self):
        s=AnsiScreen(6,20);s.feed('\x1b[?1h');self.assertTrue(s.application_cursor)
        self.assertEqual(encode_key(Qt.Key_Up,application_cursor=s.application_cursor),'\x1bOA')
        s.feed('\x1b[?1l');self.assertFalse(s.application_cursor)
    def test_region_scroll_preserves_outer_rows(self):
        s=AnsiScreen(6,20)
        for i in range(6):s.feed(f'\x1b[{i+1};1H{i}')
        s.feed('\x1b[2;5r\x1b[5;1H\n')
        self.assertEqual(s.grid[0][0],'0');self.assertEqual(s.grid[5][0],'5')
        self.assertEqual(s.grid[1][0],'2');self.assertEqual(s.grid[4][0],' ')
    def test_reverse_index(self):
        s=AnsiScreen(6,20);s.feed('\x1b[2;5r\x1b[2;1HA\x1bM')
        self.assertEqual(s.grid[1][0],' ');self.assertEqual(s.grid[2][0],'A')
    def test_scroll_down(self):
        s=AnsiScreen(6,20);s.feed('\x1b[1;1HA\x1b[2;5r\x1b[2T')
        self.assertEqual(s.grid[0][0],'A')
    def test_origin_mode(self):
        s=AnsiScreen(6,20);s.feed('\x1b[2;5r\x1b[?6h\x1b[1;1HX')
        self.assertEqual(s.grid[1][0],'X')
        s.feed('\x1b[?6l');self.assertEqual(s.row,0)
    def test_region_reset_on_resize(self):
        s=AnsiScreen(6,20);s.feed('\x1b[2;5r');s.resize(8,30)
        self.assertEqual((s.scroll_top,s.scroll_bottom),(0,7))
    def test_index_escape(self):
        s=AnsiScreen(6,20);s.feed('A\x1bE');self.assertEqual((s.row,s.col),(1,0))
    def test_legacy_key_unaffected(self):
        self.assertEqual(encode_key(Qt.Key_Left),'\x1b[D')
