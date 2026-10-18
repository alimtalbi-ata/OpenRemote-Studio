import unittest
from pathlib import Path
from client_readiness_view import readiness_rows
ROOT=Path(__file__).resolve().parents[1]
class V164Tests(unittest.TestCase):
 def test_normalize(self):
  self.assertEqual(readiness_rows({'rows':[{'protocol':'SSH','client':'ssh','status':'ready'}]}),[('SSH','ssh','ready')])
 def test_reject(self):
  with self.assertRaises(ValueError): readiness_rows({'rows':'bad'})
 def test_strip_linebreaks(self):
  self.assertEqual(readiness_rows({'rows':[{'protocol':'SSH\n','client':'ssh','status':'ok'}]})[0][0],'SSH ')
 def test_no_remote_action(self):
  source=(ROOT/'qt_app.py').read_text()
  body=source.split('    def show_local_readiness(self):')[1].split('    def show_windows_clients(self):')[0]
  self.assertIn('inspect_clients()',body)
  self.assertNotIn('launch_connection(',body)
 def test_build_exit_code(self):
  self.assertIn("if (-not $?) { throw 'Windows build script failed' }",(ROOT/'windows/bootstrap-and-build.ps1').read_text())
 def test_release_checksum(self):
  self.assertIn("$_.Name -ne 'SHA256SUMS.txt'",(ROOT/'windows/build-windows.ps1').read_text())
