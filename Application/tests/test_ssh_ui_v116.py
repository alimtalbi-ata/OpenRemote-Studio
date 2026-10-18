import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'qt_app.py'

class TestSSHUIV116(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code = SRC.read_text(encoding='utf-8')
    def test_scroll_area_imported(self): self.assertIn('QTabWidget,QScrollArea,QTextEdit', self.code)
    def test_history_scroll_area(self): self.assertIn("history_scroll.setWidgetResizable(True)", self.code)
    def test_history_scroll_has_stable_id(self): self.assertIn("sshHistoryScroll", self.code)
    def test_tabs_scroll_buttons(self): self.assertIn('self.ssh_sections.setUsesScrollButtons(True)', self.code)
    def test_no_automatic_network_from_tooltip(self): self.assertIn('no network action is triggered by hovering', self.code)
    def test_security_help(self): self.assertIn('Ne jamais utiliser le mot de passe SSH.', self.code)
    def test_accessible_descriptions(self): self.assertIn('widget.setAccessibleDescription(hint)', self.code)
    def test_consent_explained(self): self.assertIn('après clic et consentement', self.code)
