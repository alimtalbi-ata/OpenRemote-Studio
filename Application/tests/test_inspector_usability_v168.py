import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class InspectorUsabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
    def test_actions_tracked(self):self.assertIn('self.inspector_actions=create_inspector_panel(self,handlers)',self.source)
    def test_actions_disabled_without_selection(self):self.assertIn('button.setEnabled(selected is not None)',self.source)
    def test_empty_selection_hint(self):self.assertIn('Sélectionnez une connexion dans la liste',self.source)
    def test_dock_can_be_hidden(self):self.assertIn('dock.toggleViewAction()',self.source)
    def test_dock_can_be_restored_from_view_menu(self):self.assertIn("addMenu('Affichage')",self.source)
    def test_no_automatic_connection(self):self.assertNotIn('self.connect()\n        self.update_inspector()',self.source)
