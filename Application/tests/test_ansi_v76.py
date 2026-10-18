import unittest
from ansi_screen import AnsiScreen

class TestUnicodeTerminal(unittest.TestCase):
    def test_wide_character_occupies_two_cells(self):
        s=AnsiScreen(5,20);s.feed('界X')
        self.assertEqual(s.col,3)
        self.assertEqual(s.render(),'界X')
    def test_wide_character_wraps_before_last_column(self):
        s=AnsiScreen(5,20);s.feed('a'*19+'界')
        self.assertEqual(s.row,1)
        self.assertEqual(s.col,2)
        self.assertTrue(s.render().endswith('界'))
    def test_combining_character_does_not_advance_cursor(self):
        s=AnsiScreen(5,20);s.feed('e\u0301x')
        self.assertEqual(s.col,2)
        self.assertEqual(s.render(),'e\u0301x')
    def test_resize_retains_content(self):
        s=AnsiScreen(5,20);s.feed('abc');s.resize(8,30)
        self.assertEqual(s.render(),'abc')
    def test_resize_clamps_bounds(self):
        s=AnsiScreen();s.resize(999,999)
        self.assertEqual((s.rows,s.cols),(200,500))
