import unittest
from ansi_screen import AnsiScreen

class ScreenV82Tests(unittest.TestCase):
    def test_alt_resize_restore(self):
        s=AnsiScreen(5,20);s.feed('base');s.feed('\x1b[?1049h');s.resize(7,25);s.feed('alt');s.feed('\x1b[?1049l')
        self.assertEqual((len(s.grid),len(s.grid[0])),(7,25));self.assertTrue(s.render().startswith('base'))
    def test_insert_lines_region_preserves_footer(self):
        s=AnsiScreen(6,20)
        for i in range(6):s.feed(f'\x1b[{i+1};1H{i}')
        s.feed('\x1b[2;4r\x1b[2;1H\x1b[L')
        self.assertEqual(s.grid[5][0],'5');self.assertEqual(s.grid[4][0],'4');self.assertEqual(s.grid[1][0],' ')
    def test_delete_lines_region_preserves_footer(self):
        s=AnsiScreen(6,20)
        for i in range(6):s.feed(f'\x1b[{i+1};1H{i}')
        s.feed('\x1b[2;4r\x1b[2;1H\x1b[M')
        self.assertEqual(s.grid[5][0],'5');self.assertEqual(s.grid[1][0],'2');self.assertEqual(s.grid[3][0],' ')
    def test_clear_screen_keeps_cursor(self):
        s=AnsiScreen(5,20);s.feed('\x1b[3;7Hhello\x1b[2J')
        self.assertEqual((s.row,s.col),(2,11));self.assertEqual(s.render(),'')
    def test_clear_before_cursor(self):
        s=AnsiScreen(5,20);s.feed('abc\x1b[2;1Hxyz\x1b[1J')
        self.assertEqual(s.grid[0][0],' ');self.assertEqual(s.grid[1][1],' ')
    def test_region_ignores_insert_outside(self):
        s=AnsiScreen(6,20);s.feed('\x1b[6;1Hfooter\x1b[2;4r\x1b[6;1H\x1b[5L')
        self.assertEqual(s.grid[5][0],'f')
