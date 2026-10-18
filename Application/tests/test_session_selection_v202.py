import unittest
from pathlib import Path
from session_selection import session_identity, selected_session, preserved_session_identity

class SessionSelectionV202Tests(unittest.TestCase):
    def test_zero_pid_rejected(self):
        self.assertIsNone(session_identity({'connection_id':'a','pid':0}))
    def test_unicode_pid_rejected(self):
        self.assertIsNone(session_identity({'connection_id':'a','pid':'١٢'}))
    def test_connection_id_whitespace_rejected(self):
        self.assertIsNone(session_identity({'connection_id':' a ','pid':12}))
    def test_ascii_pid_supported(self):
        self.assertEqual(session_identity({'connection_id':'a','pid':12}),('a','12'))
    def test_invalid_selection_not_preserved(self):
        self.assertIsNone(preserved_session_identity([{'connection_id':'a','pid':0}],('a','0')))
    def test_refresh_computes_preservation_once(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        segment=source.split('    def refresh_session_overview(self,*_):',1)[1].split('    def show_session_diagnostics(self):',1)[0]
        self.assertEqual(segment.count('preserved_session_identity(visible, previous)'),1)
        self.assertIn('preserved=preserved_session_identity(visible, previous)',segment)

if __name__=='__main__': unittest.main()
