import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class HomeWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'home_workspace.py').read_text(encoding='utf8')
        cls.main=(ROOT/'qt_app.py').read_text(encoding='utf8')
    def test_factory(self): self.assertIn('def create_home_header(handlers)',self.source)
    def test_integration(self): self.assertIn('h.addWidget(create_home_header(',self.main)
    def test_accessible(self): self.assertIn('button.setAccessibleName(caption)',self.source)
    def test_no_auto_launch(self): self.assertNotIn('subprocess',self.source)
    def test_no_network(self): self.assertNotIn('socket',self.source)
    def test_actions(self):
        for name in ('add','connect','check_access','show_session_overview','show_local_readiness'):
            self.assertIn("'"+name+"'",self.source)
    def test_handler_validation(self): self.assertIn('not callable(handlers[name])',self.source)
