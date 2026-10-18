import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HomeFocusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home=(ROOT/'home_workspace.py').read_text(encoding='utf8')
        cls.gui=(ROOT/'qt_app.py').read_text(encoding='utf8')
    def test_no_duplicate_new_connection(self):
        self.assertNotIn("('＋ Nouvelle connexion', 'add'", self.home)
    def test_no_duplicate_connect(self):
        self.assertNotIn("('Ouvrir session', 'connect'", self.home)
    def test_no_duplicate_access_check(self):
        self.assertNotIn("('Vérifier accès', 'check_access'", self.home)
    def test_no_duplicate_local_diagnostic(self):
        self.assertNotIn("('Diagnostic local', 'show_local_readiness'", self.home)
    def test_session_shortcut_kept(self):
        self.assertIn("('Sessions actives', 'show_session_overview'",self.home)
    def test_incident_duplicate_removed(self):
        self.assertNotIn("incident_button=QPushButton('Analyser les échecs récents')",self.gui)
    def test_guidance_accessible(self):
        self.assertIn("guidance.setWordWrap(True)",self.home)
    def test_no_automatic_network(self):
        self.assertNotIn('subprocess',self.home)
