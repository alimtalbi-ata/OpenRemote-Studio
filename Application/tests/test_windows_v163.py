import unittest
from pathlib import Path
from windows_ui_theme import MAIN_STYLESHEET
ROOT=Path(__file__).resolve().parents[1]
class WindowsV163Tests(unittest.TestCase):
 def test_theme_focus(self):self.assertIn('QPushButton:focus',MAIN_STYLESHEET)
 def test_theme_disabled(self):self.assertIn('QPushButton:disabled',MAIN_STYLESHEET)
 def test_cmd_entrypoint(self):self.assertIn('bootstrap-and-build.ps1',(ROOT/'windows/BUILD-WINDOWS.cmd').read_text())
 def test_bootstrap_winget(self):self.assertIn('winget install',(ROOT/'windows/bootstrap-and-build.ps1').read_text())
 def test_bootstrap_failure(self):self.assertIn('exit 1',(ROOT/'windows/bootstrap-and-build.ps1').read_text())
 def test_runtime_disclosure(self):self.assertIn('non intégrée',(ROOT/'windows/RUNTIME-DEPENDENCIES.md').read_text())
 def test_title_current(self):self.assertIn("'OpenRemote Studio V'+application_version()", (ROOT/'qt_app.py').read_text())
