import unittest
from pathlib import Path
from session_reconnect_choices import reconnectable_processes

class ReconnectV206(unittest.TestCase):
    def test_duplicate_identity_excluded(self):
        rows=[dict(connection_id='a',pid=42,status='exited'),dict(connection_id='a',pid='042',status='exited')]
        self.assertEqual(reconnectable_processes(rows,'a'),[])
    def test_other_valid_process_preserved(self):
        rows=[dict(connection_id='a',pid=42,status='exited'),dict(connection_id='a',pid='042',status='exited'),dict(connection_id='a',pid=43,status='exited')]
        self.assertEqual(reconnectable_processes(rows,'a'),[rows[2]])
    def test_other_connection_not_interfering(self):
        rows=[dict(connection_id='a',pid=42,status='exited'),dict(connection_id='b',pid=42,status='running')]
        self.assertEqual(reconnectable_processes(rows,'a'),[rows[0]])
    def test_inno_version_matches(self):
        self.assertIn('#include "version.generated.iss"',Path('windows/OpenRemoteStudio.iss').read_text())
    def test_dialog_rechecks_selection(self):
        source=Path('qt_app.py').read_text()
        self.assertIn("current.get('id') != c['id']",source)
    def test_dialog_choices_unique(self):
        source=Path('qt_app.py').read_text()
        self.assertIn('enumerate(candidates)',source)
