"""Regression tests for non-modal, reusable transfer history workspace."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "qt_app.py").read_text(encoding="utf-8")


class TransferWorkspaceTabTests(unittest.TestCase):
    def test_transfer_history_uses_reusable_workspace_tab(self):
        section = SOURCE.split("    def show_transfer_history(self):", 1)[1].split("    def closeEvent(", 1)[0]
        self.assertIn("self.tabs.indexOf(self.transfer_history_tab) >= 0", section)
        self.assertIn("self.tabs.addTab(pane,'Transferts')", section)
        self.assertIn("self.tabs.setCurrentWidget(pane)", section)
        self.assertNotIn("dialog.exec()", section)

    def test_reopening_closed_tab_checks_for_none_before_qt_index(self):
        section = SOURCE.split('    def show_transfer_history(self):', 1)[1].split('    def closeEvent(', 1)[0]
        self.assertIn("getattr(self, 'transfer_history_tab', None) is not None", section)

    def test_revisiting_tab_refreshes_persisted_history(self):
        section = SOURCE.split('    def show_transfer_history(self):', 1)[1].split('    def closeEvent(', 1)[0]
        self.assertIn('self.transfer_history_refresh()', section)
        self.assertIn('self.transfer_history_refresh=populate', section)

    def test_closing_transfer_tab_clears_stale_references(self):
        section = SOURCE.split('    def close_tab(self,index):', 1)[1].split('    def show_integrations(', 1)[0]
        self.assertIn("widget is getattr(self,'transfer_history_tab',None)", section)
        self.assertIn('self.transfer_history_tab=None', section)
        self.assertIn('self.transfer_history_refresh=None', section)

    def test_primary_navigation_tracks_transfer_tab(self):
        section = SOURCE.split("    def _sync_primary_navigation(self, *_):", 1)[1].split("    def show_home(", 1)[0]
        self.assertIn("current.objectName() == 'transferHistoryTab'", section)
        self.assertIn("'show_transfer_history'", section)

    def test_corrupt_journal_clears_stale_rows_without_leaking_paths(self):
        section = SOURCE.split('    def show_transfer_history(self):', 1)[1].split('    def closeEvent(', 1)[0]
        self.assertIn('cells=[transfer_row_cells(row) for row in rows]', section)
        self.assertIn("warning.setText('Historique indisponible", section)
        self.assertIn('except Exception:', section)
        self.assertNotIn("'Erreur du journal : '+str(exc)", section)

    def test_transfer_history_is_read_only(self):
        section = SOURCE.split("    def show_transfer_history(self):", 1)[1].split("    def closeEvent(", 1)[0]
        self.assertIn("QAbstractItemView.NoEditTriggers", section)
        self.assertIn("self.transfer_journal.search(", section)


if __name__ == "__main__":
    unittest.main()
