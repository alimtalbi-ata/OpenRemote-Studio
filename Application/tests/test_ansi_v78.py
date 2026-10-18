import unittest
from ansi_screen import AnsiScreen

class ColorTests(unittest.TestCase):
    def test_256_cube(self):
        s=AnsiScreen();s.feed('\x1b[38;5;196mX')
        self.assertIn('color:#ff0000',s.render_html())
    def test_256_gray(self):
        s=AnsiScreen();s.feed('\x1b[48;5;232mX')
        self.assertIn('background-color:#080808',s.render_html())
    def test_truecolor(self):
        s=AnsiScreen();s.feed('\x1b[38;2;12;34;56mX')
        self.assertIn('color:#0c2238',s.render_html())
    def test_separate_attributes_persist(self):
        s=AnsiScreen();s.feed('\x1b[31m\x1b[1mX')
        h=s.render_html();self.assertIn('color:#aa0000',h);self.assertIn('font-weight:bold',h)
    def test_reset_fg_preserves_bg(self):
        s=AnsiScreen();s.feed('\x1b[31;44m\x1b[39mX')
        h=s.render_html();self.assertNotIn('color:#aa0000',h);self.assertIn('background-color:#0000aa',h)
    def test_invalid_rgb_rejected(self):
        s=AnsiScreen();s.feed('\x1b[38;2;999;0;0mX')
        self.assertNotIn('color:',s.render_html())
    def test_split_sequences(self):
        s=AnsiScreen();s.feed('\x1b[38;5;');s.feed('21mX')
        self.assertIn('color:#0000ff',s.render_html())
    def test_html_escaped(self):
        s=AnsiScreen();s.feed('\x1b[38;2;1;2;3m<script>')
        self.assertIn('&lt;script&gt;',s.render_html());self.assertNotIn('<script>',s.render_html())
