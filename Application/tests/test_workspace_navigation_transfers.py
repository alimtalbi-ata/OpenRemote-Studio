"""Primary navigation exposes transfer history without side effects."""
import unittest
from workspace_navigation import primary_views, resolve_view


class TransferNavigationTests(unittest.TestCase):
    def test_transfers_has_stable_handler(self):
        self.assertEqual(resolve_view("Transferts"), "show_transfer_history")

    def test_primary_views_have_unique_labels_and_handlers(self):
        views = primary_views()
        self.assertEqual(len(views), len({v[0] for v in views}))
        self.assertEqual(len(views), len({v[1] for v in views}))

    def test_existing_shortcuts_unchanged(self):
        views = {label: (handler, shortcut) for label, handler, shortcut in primary_views()}
        self.assertEqual(views["Connexions"], ("show_home", "Ctrl+1"))
        self.assertEqual(views["Sessions"], ("show_session_overview", "Ctrl+2"))
        self.assertEqual(views["Diagnostics"], ("show_local_readiness", "Ctrl+3"))


if __name__ == "__main__":
    unittest.main()
