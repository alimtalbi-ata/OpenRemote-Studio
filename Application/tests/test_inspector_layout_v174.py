import unittest
from pathlib import Path
from inspector_action_layout import inspector_action_groups

ROOT=Path(__file__).resolve().parents[1]

class InspectorLayoutTests(unittest.TestCase):
    def test_two_sections(self):
        self.assertEqual([x[0] for x in inspector_action_groups()], ['Session','Informations'])
    def test_unique_handlers(self):
        handlers=[action[1] for _,items in inspector_action_groups() for action in items]
        self.assertEqual(len(handlers),len(set(handlers)))
    def test_expected_actions(self):
        self.assertEqual({a[1] for _,items in inspector_action_groups() for a in items}, {'connect','check_access','show_connection_card','show_connection_timeline'})
    def test_nonempty_tooltips(self):
        self.assertTrue(all(a[2] for _,items in inspector_action_groups() for a in items))
    def test_qt_integration(self):
        source=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('from inspector_action_layout import inspector_action_groups',source)
        self.assertIn('create_inspector_panel(self,handlers)',source)
        self.assertIn('button.setAccessibleName',(ROOT/'inspector_panel.py').read_text(encoding='utf-8'))
    def test_no_side_effect_import(self):
        source=(ROOT/'inspector_action_layout.py').read_text(encoding='utf-8')
        self.assertNotIn('subprocess',source)
        self.assertNotIn('socket',source)
