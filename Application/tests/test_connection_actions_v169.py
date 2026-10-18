import unittest
from connection_actions import CONNECTION_ACTIONS, actions_for_selection

class ConnectionActionsTests(unittest.TestCase):
    def test_empty_selection(self): self.assertEqual(actions_for_selection(None), ())
    def test_blank_selection(self): self.assertEqual(actions_for_selection('  '), ())
    def test_invalid_selection(self): self.assertEqual(actions_for_selection(12), ())
    def test_valid_selection(self): self.assertEqual(actions_for_selection('abc'), CONNECTION_ACTIONS)
    def test_unique_handlers(self): self.assertEqual(len({m for _,m in CONNECTION_ACTIONS}),len(CONNECTION_ACTIONS))
    def test_required_actions(self): self.assertIn(('Vérifier accès','check_access'),CONNECTION_ACTIONS)
    def test_immutable_actions(self): self.assertIsInstance(CONNECTION_ACTIONS,tuple)
