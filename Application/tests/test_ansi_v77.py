import unittest
from ansi_screen import AnsiScreen

class TestAnsiColors(unittest.TestCase):
    def test_foreground(self):
        s=AnsiScreen();s.feed('\x1b[31mred');self.assertIn('color:#aa0000',s.render_html())
    def test_background_and_bold(self):
        s=AnsiScreen();s.feed('\x1b[1;44mX');self.assertIn('background-color:#0000aa',s.render_html());self.assertIn('font-weight:bold',s.render_html())
    def test_escape_html(self):
        s=AnsiScreen();s.feed('<script>alert(1)</script>');self.assertNotIn('<script>',s.render_html());self.assertIn('&lt;script&gt;',s.render_html())
    def test_reset(self):
        s=AnsiScreen();s.feed('\x1b[31mA\x1b[0mB');self.assertEqual(s.render(),'AB');self.assertIn('</span>B',s.render_html())
    def test_resize_preserves_color(self):
        s=AnsiScreen();s.feed('\x1b[32mG');s.resize(40,120);self.assertIn('color:#00aa00',s.render_html())
    def test_clear_removes_color(self):
        s=AnsiScreen();s.feed('\x1b[31mA\x1b[2J');self.assertNotIn('color:#aa0000',s.render_html())
