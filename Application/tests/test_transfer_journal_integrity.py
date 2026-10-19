"""SFTP journal state integrity regression tests.
Author: Abdelhalim Talbi.
"""
import tempfile
import unittest
from pathlib import Path
from transfer_journal import TransferJournal


class TransferJournalIntegrityTests(unittest.TestCase):
    def test_terminal_state_cannot_be_overwritten_by_late_callback(self):
        with tempfile.TemporaryDirectory() as d:
            journal = TransferJournal(Path(d) / "journal.db")
            item = journal.add("server", "download", "/remote", "local")
            journal.update(item, "running", 40)
            journal.update(item, "cancelled")
            with self.assertRaises(ValueError):
                journal.update(item, "done", 100)
            self.assertEqual(journal.search()[0][5], "cancelled")
            journal.close()

    def test_progress_cannot_go_backwards(self):
        with tempfile.TemporaryDirectory() as d:
            journal = TransferJournal(Path(d) / "journal.db")
            item = journal.add("server", "upload", "/remote", "local")
            journal.update(item, "running", 80)
            with self.assertRaises(ValueError):
                journal.update(item, "running", 25)
            self.assertEqual(journal.search()[0][6], 80)
            journal.close()

    def test_restart_keeps_terminal_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "journal.db"
            journal = TransferJournal(path)
            item = journal.add("server", "upload", "/remote", "local")
            journal.update(item, "done", 100)
            journal.close()
            reopened = TransferJournal(path)
            self.assertEqual(reopened.search()[0][5:7], ("done", 100))
            reopened.close()


if __name__ == "__main__":
    unittest.main()
