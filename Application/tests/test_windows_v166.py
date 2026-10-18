import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class WindowsV166Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
    def test_window_version(self): self.assertIn("'OpenRemote Studio V'+application_version()",self.source)
    def test_quick_guide_method(self): self.assertIn('def show_quick_guide(self):',self.source)
    def test_quick_guide_reuses_tab(self): self.assertIn('indexOf(self.quick_guide_tab) >= 0',self.source)
    def test_quick_guide_f1(self): self.assertIn("('F1', 'show_quick_guide')",(Path(__file__).resolve().parents[1]/'workspace_shortcuts.py').read_text().replace('\"',"'"))
    def test_quick_guide_menu(self): self.assertIn("addMenu('Aide')",self.source)
    def test_quick_guide_no_network(self):
        segment=self.source.split('def show_quick_guide(self):')[1].split('def show_qa_summary(self):')[0]
        self.assertNotIn('subprocess',segment)
        self.assertNotIn('requests.',segment)
