import unittest
from responsive_toolbar import collapsed_actions, SECONDARY_ACTIONS

class ResponsiveToolbarTests(unittest.TestCase):
    def test_small_screen(self): self.assertEqual(collapsed_actions(900), SECONDARY_ACTIONS)
    def test_small_boundary(self): self.assertEqual(collapsed_actions(1049), SECONDARY_ACTIONS)
    def test_medium(self): self.assertEqual(collapsed_actions(1100), ('diagnostic', 'help'))
    def test_medium_boundary(self): self.assertEqual(collapsed_actions(1249), ('diagnostic', 'help'))
    def test_large(self): self.assertEqual(collapsed_actions(1250), ())
    def test_boolean_rejected(self):
        with self.assertRaises(TypeError): collapsed_actions(True)
    def test_non_numeric_rejected(self):
        with self.assertRaises(TypeError): collapsed_actions('small')

if __name__=='__main__': unittest.main()
