import unittest
from pathlib import Path
from session_reconnect_choices import reconnectable_processes

class TestReconnectChoices(unittest.TestCase):
    def test_two_exited_sessions(self):
        rows=[dict(connection_id='a',pid=11,status='exited'),dict(connection_id='a',pid=12,status='exited')]
        self.assertEqual(reconnectable_processes(rows,'a'),rows)
    def test_running_sibling_blocks_all(self):
        rows=[dict(connection_id='a',pid=11,status='exited'),dict(connection_id='a',pid=12,status='running')]
        self.assertEqual(reconnectable_processes(rows,'a'),[])
    def test_duplicate_normalized_pid_rejected(self):
        rows=[dict(connection_id='a',pid=11,status='exited'),dict(connection_id='a',pid='011',status='exited')]
        self.assertEqual(reconnectable_processes(rows,'a'),[])
    def test_other_connection_ignored(self):
        rows=[dict(connection_id='b',pid=2,status='exited'),dict(connection_id='a',pid=3,status='exited')]
        self.assertEqual(reconnectable_processes(rows,'a'),rows[1:])
    def test_invalid_rows_ignored(self):
        self.assertEqual(reconnectable_processes([None,dict(connection_id='a',pid=0,status='exited')],'a'),[])
    def test_gui_requires_explicit_choice_and_revalidation(self):
        source=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        section=source.split('    def reconnect_selected(self):',1)[1].split('    def connect(self):',1)[0]
        self.assertIn('QInputDialog.getItem',section)
        self.assertIn("reconnect_candidate(c['id'],pid)",section)
        self.assertNotIn("reconnect_candidate(c['id'])",section)
