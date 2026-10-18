import unittest
from tab_navigation import next_tab,tab_at_position,closable_tab

class TabNavigationTests(unittest.TestCase):
    def test_forward_wrap(self):self.assertEqual(next_tab(3,4),0)
    def test_backward_wrap(self):self.assertEqual(next_tab(0,4,True),3)
    def test_empty(self):self.assertEqual(next_tab(0,0),-1)
    def test_position(self):self.assertEqual(tab_at_position(2,3),1)
    def test_invalid_position(self):self.assertEqual(tab_at_position(9,3),-1)
    def test_home_protection(self):self.assertFalse(closable_tab(0))
    def test_other_tab(self):self.assertTrue(closable_tab(2))
