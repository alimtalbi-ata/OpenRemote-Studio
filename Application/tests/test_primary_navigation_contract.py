"""Keep visible primary navigation and registered shortcuts synchronized."""
import unittest
from workspace_navigation import primary_views
from workspace_shortcuts import workspace_shortcuts, validate_shortcuts


class PrimaryNavigationContractTests(unittest.TestCase):
    def test_each_primary_shortcut_targets_the_same_handler(self):
        registered = dict(workspace_shortcuts())
        for label, handler, shortcut in primary_views():
            with self.subTest(view=label):
                self.assertEqual(registered.get(shortcut), handler)

    def test_all_primary_handlers_are_distinct(self):
        handlers = [handler for _, handler, _ in primary_views()]
        self.assertEqual(len(handlers), len(set(handlers)))

    def test_shortcuts_are_valid(self):
        self.assertTrue(validate_shortcuts())

    def test_duplicate_shortcut_is_rejected(self):
        self.assertFalse(validate_shortcuts((("Ctrl+1", "show_home"), ("ctrl+1", "show_session_overview"))))


if __name__ == "__main__":
    unittest.main()
