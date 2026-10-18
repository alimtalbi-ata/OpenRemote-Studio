"""Source contract tests for SFTP completion and tab lifecycle (not GUI runtime tests)."""
import pathlib
import unittest

SOURCE = (pathlib.Path(__file__).resolve().parents[1] / 'qt_app.py').read_text(encoding='utf-8')

class SftpQtLifecycleContract(unittest.TestCase):
    def test_journal_error_initialized_before_completion(self):
        block = SOURCE.split('def finish(result):', 1)[1].split('def error(message):', 1)[0]
        self.assertIn('journal_error=None', block)
        self.assertIn('queue.complete(current,journal_error is None)', block)
        self.assertIn('if journal_error is None and not pane._sftp_closing:on_success(result)', block)
    def test_tab_close_cancels_pending_sftp(self):
        self.assertIn('pane._cancel_sftp_transfers=cancel_transfers', SOURCE)
        block = SOURCE.split('def close_tab(self,index):', 1)[1].split('def show_integrations', 1)[0]
        self.assertIn("getattr(widget,'_cancel_sftp_transfers',None)",block)
        self.assertLess(block.index('cancel_sftp()'),block.index('self.tabs.removeTab(index)'))
