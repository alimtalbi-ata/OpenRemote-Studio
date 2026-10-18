import unittest
from pathlib import Path
from session_presentation import session_process_details

class SessionDetailsTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(name='Server',protocol='SSH',pid=42,status='exited',started_at='2026-10-17',exit_code=1,command='SECRET_PASSWORD')
    def test_identity(self):
        result=session_process_details(self.row)
        self.assertIn('PID : 42',result)
        self.assertIn('Code de sortie : 1',result)
    def test_no_secret_command(self):
        self.assertNotIn('SECRET_PASSWORD',session_process_details(self.row))
    def test_newline_sanitized(self):
        self.row['name']='one\ntwo'
        self.assertIn('Connexion : one two',session_process_details(self.row))
    def test_missing_fields(self):
        self.assertIn('indisponible',session_process_details({}))
    def test_invalid_input(self):
        with self.assertRaises(ValueError):session_process_details(None)
    def test_ui_context_action(self):
        ui=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('Copier les détails du processus',ui)
        self.assertIn('session_process_details(row)',ui)
