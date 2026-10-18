import unittest
from ansi_screen import AnsiScreen
from terminal_keys import encode_key
from terminal_keys import Qt

class TestTerminalV79(unittest.TestCase):
    def test_delete_cells(self):
        s=AnsiScreen(5,20);s.feed('ABCDE\x1b[1;2H\x1b[2P');self.assertTrue(s.render().startswith('ADE'))
    def test_insert_cells(self):
        s=AnsiScreen(5,20);s.feed('ABCD\x1b[1;2H\x1b[2@');self.assertTrue(s.render().startswith('A  BCD'))
    def test_erase_chars(self):
        s=AnsiScreen(5,20);s.feed('ABCD\x1b[1;2H\x1b[2X');self.assertTrue(s.render().startswith('A  D'))
    def test_vertical_absolute(self):
        s=AnsiScreen(5,20);s.feed('A\x1b[3dB');self.assertEqual(s.grid[2][1],'B')
    def test_insert_lines(self):
        s=AnsiScreen(5,20);s.feed('A\nB\x1b[1;1H\x1b[1L');self.assertEqual(s.grid[1][0],'A')
    def test_delete_lines(self):
        s=AnsiScreen(5,20);s.feed('A\nB\x1b[1;1H\x1b[1M');self.assertEqual(s.grid[0][1],'B')
    def test_keys(self):
        self.assertEqual(encode_key(Qt.Key_Up),'\x1b[A')
        self.assertEqual(encode_key(Qt.Key_C,Qt.ControlModifier),'\x03')
        self.assertEqual(encode_key(Qt.Key_F5),'\x1b[15~')
        self.assertEqual(encode_key(Qt.Key_A,Qt.NoModifier,'a'),'a')
    def test_unknown(self):self.assertIsNone(encode_key(Qt.Key_Shift))
