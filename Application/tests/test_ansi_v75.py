import unittest
from ansi_screen import AnsiScreen
class TestAnsiV75(unittest.TestCase):
 def test_alternate_screen_restore(self):
  s=AnsiScreen(5,20);s.feed('main\x1b[?1049halt');self.assertEqual(s.render(),'alt');s.feed('\x1b[?1049l');self.assertEqual(s.render(),'main')
 def test_alternate_screen_idempotent(self):
  s=AnsiScreen(5,20);s.feed('a\x1b[?1049h\x1b[?1049hx\x1b[?1049l');self.assertEqual(s.render(),'a')
 def test_sgr_reset(self):
  s=AnsiScreen();s.feed('\x1b[31mred');self.assertEqual(s.sgr,(('fg',('ansi',1)),));s.feed('\x1b[0m');self.assertEqual(s.sgr,())
 def test_split_alternate(self):
  s=AnsiScreen();s.feed('a\x1b[?104');s.feed('9hX');self.assertEqual(s.render(),'X')
