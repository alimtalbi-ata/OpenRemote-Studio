import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class InspectorPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel=(ROOT/'inspector_panel.py').read_text(encoding='utf8')
        cls.qt=(ROOT/'qt_app.py').read_text(encoding='utf8')
    def test_dock_extracted(self): self.assertIn('def create_inspector_panel(',self.panel)
    def test_action_disabled_until_selection(self): self.assertIn('button.setEnabled(False)',self.panel)
    def test_plain_text_protects_html(self): self.assertIn('Qt.PlainText',self.panel)
    def test_handlers_validated(self): self.assertIn('not callable(handlers[method])',self.panel)
    def test_tooltips_and_accessibility(self):
        self.assertIn('button.setToolTip',self.panel)
        self.assertIn('button.setAccessibleName',self.panel)
    def test_main_window_uses_factory(self): self.assertIn('create_inspector_panel(self,handlers)',self.qt)
    def test_no_network_on_creation(self):
        self.assertNotIn('subprocess',self.panel)
        self.assertNotIn('socket',self.panel)
