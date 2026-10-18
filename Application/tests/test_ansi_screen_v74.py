import unittest
from ansi_screen import AnsiScreen
class TestAnsiScreen(unittest.TestCase):
 def test_plain(self):
  s=AnsiScreen(5,20);s.feed('hello');self.assertEqual(s.render(),'hello')
 def test_carriage(self):
  s=AnsiScreen(5,20);s.feed('hello\rbye');self.assertEqual(s.render(),'byelo')
 def test_clear(self):
  s=AnsiScreen(5,20);s.feed('hello\x1b[2J');self.assertEqual(s.render(),'')
 def test_split_escape(self):
  s=AnsiScreen(5,20);s.feed('abc\x1b[');s.feed('2K');self.assertEqual(s.render(),'')
 def test_cursor(self):
  s=AnsiScreen(5,20);s.feed('abc\x1b[1D!');self.assertEqual(s.render(),'ab!')
 def test_resize(self):
  s=AnsiScreen(5,20);s.feed('hello');s.resize(6,25);self.assertEqual(s.render(),'hello')
 def test_osc(self):
  s=AnsiScreen(5,20);s.feed('a\x1b]0;secret\x07b');self.assertEqual(s.render(),'ab')
 def test_bounded(self):
  s=AnsiScreen(5,20);s.feed('x'*200);self.assertLessEqual(len(s.render().splitlines()),5)
