"""Source-level packaging checks; do not claim native Windows execution."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class PortableBuildContract(unittest.TestCase):
    def test_archive_inspected_after_packaging(self):
        script=(ROOT/'windows'/'build-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('ZipFile]::OpenRead($portable)',script)
        self.assertIn('Portable archive must contain exactly one application executable',script)
        self.assertIn('Portable archive missing Qt Windows platform plugin',script)
    def test_qt_navigation_accessible(self):
        script=(ROOT/'qt_app.py').read_text(encoding='utf-8')
        self.assertIn("setAccessibleName('Inventaire des connexions')",script)
        self.assertIn("setAccessibleName('Espace de travail et sessions')",script)
