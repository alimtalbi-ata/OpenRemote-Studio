import unittest
from pathlib import Path
from connection_action_state import primary_action_state

class PrimaryActionStateTests(unittest.TestCase):
    def test_empty_selection(self):
        self.assertEqual(primary_action_state(None),{'connect':False,'check_access':False,'sftp':False})
    def test_group_header(self):
        self.assertFalse(any(primary_action_state({'name':'Group'}).values()))
    def test_ssh(self):
        self.assertTrue(all(primary_action_state({'id':'a','protocol':'SSH'}).values()))
    def test_sftp(self):
        self.assertTrue(primary_action_state({'id':'a','protocol':'SFTP'})['sftp'])
    def test_rdp(self):
        state=primary_action_state({'id':'a','protocol':'RDP'})
        self.assertTrue(state['connect']);self.assertTrue(state['check_access']);self.assertFalse(state['sftp'])
    def test_vnc(self):
        self.assertFalse(primary_action_state({'id':'a','protocol':'VNC'})['sftp'])
    def test_invalid_id(self):
        self.assertFalse(any(primary_action_state({'id':'  ','protocol':'SSH'}).values()))
    def test_ui_wiring(self):
        code=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn('self._update_primary_action_buttons(selected)',code)
        self.assertIn('self.primary_action_buttons[key]=button',code)

if __name__=='__main__':unittest.main()
