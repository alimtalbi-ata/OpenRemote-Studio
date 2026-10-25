"""Audit journal terminal-state regression tests. Author: Abdelhalim Talbi."""
import tempfile
import unittest
from pathlib import Path
from transfer_journal import TransferJournal

class TransferJournalStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.journal=TransferJournal(Path(self.tmp.name)/'transfers.sqlite')
        self.id=self.journal.add('conn-1','download','/remote/file','/local/file')
        self.journal.update(self.id,'running')
    def tearDown(self):
        self.journal.close()
        self.tmp.cleanup()
    def test_cancelled_state_is_terminal(self):
        self.journal.update(self.id,'cancelled')
        with self.assertRaisesRegex(ValueError,'terminé'):
            self.journal.update(self.id,'done',100)
        self.assertEqual(self.journal.recent()[0][5],'cancelled')
    def test_done_state_is_terminal(self):
        self.journal.update(self.id,'done',100)
        with self.assertRaisesRegex(ValueError,'terminé'):
            self.journal.update(self.id,'cancelled')
        self.assertEqual(self.journal.recent()[0][5],'done')
    def test_progress_cannot_regress(self):
        self.journal.update(self.id,'running',60)
        with self.assertRaisesRegex(ValueError,'progression régressive'):
            self.journal.update(self.id,'running',40)
        self.assertEqual(self.journal.recent()[0][6],60)
    def test_recovery_marks_unfinished_transfer_interrupted(self):
        self.journal.update(self.id,'running',30)
        self.journal.recover()
        self.assertEqual(self.journal.recent()[0][5],'interrupted')

if __name__=='__main__': unittest.main()
