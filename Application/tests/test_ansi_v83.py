import unittest
from ansi_screen import AnsiScreen

class TestV83(unittest.TestCase):
    def test_cursor_default_visible(self):
        self.assertTrue(AnsiScreen().cursor_visible)
    def test_cursor_hidden(self):
        s=AnsiScreen();s.feed('A\x1b[?25l')
        self.assertFalse(s.cursor_visible)
        self.assertNotIn('text-decoration:underline',s.render_html())
    def test_cursor_reenabled(self):
        s=AnsiScreen();s.feed('\x1b[?25l\x1b[?25h')
        self.assertIn('text-decoration:underline',s.render_html())
    def test_cursor_moves(self):
        s=AnsiScreen();s.feed('ABC\x1b[1;1H')
        self.assertTrue(s.line_html(0,True).startswith('<span style="text-decoration:underline'))
    def test_escape_html_in_line(self):
        s=AnsiScreen();s.feed('<script>')
        self.assertNotIn('<script>',s.render_html())
        self.assertIn('&lt;script&gt;',s.render_html())
    def test_invalid_line(self):
        s=AnsiScreen()
        with self.assertRaises(IndexError):s.line_html(-1)
    def test_no_cursor_in_plain_line(self):
        s=AnsiScreen();s.feed('ok')
        self.assertNotIn('text-decoration:underline',s.line_html(0))
