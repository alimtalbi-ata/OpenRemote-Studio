import unittest
from pathlib import Path
from session_diagnostics import format_session_diagnostic

class DiagnosticCopyTests(unittest.TestCase):
    def test_empty(self):
        report=dict(connections=0,failed_attempts=0,repeated_failures=0,items=[])
        self.assertIn('Aucun processus',format_session_diagnostic(report))
    def test_failure(self):
        report=dict(connections=1,failed_attempts=2,repeated_failures=1,items=[dict(name='Serveur',protocol='SSH',failures=2,repeated_failure=True,attempts=3,last_exit_code=255,hint='Vérifier le client')])
        text=format_session_diagnostic(report)
        self.assertIn('ÉCHECS RÉPÉTÉS',text)
        self.assertIn('Vérifier le client',text)
        self.assertNotIn('Aucun processus',text)
    def test_does_not_mutate_report(self):
        report=dict(connections=0,failed_attempts=0,repeated_failures=0,items=[])
        before=repr(report)
        format_session_diagnostic(report)
        self.assertEqual(repr(report),before)
    def test_ui_copy_button_wired(self):
        code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('copySessionDiagnostics',code)
        self.assertIn('QApplication.clipboard().setText(diagnostic_text)',code)
if __name__=='__main__':unittest.main()
