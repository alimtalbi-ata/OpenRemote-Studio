"""Ensure both Windows PyInstaller specs resolve the actual Qt entrypoint.

Runs without PyInstaller or Windows. Author: Abdelhalim Talbi.
"""
from pathlib import Path
import unittest


class WindowsSpecEntrypointTests(unittest.TestCase):
    def test_specs_use_application_root(self):
        application=Path(__file__).resolve().parents[1]
        self.assertTrue((application/'qt_app.py').is_file())
        for filename in ('OpenRemoteStudio.spec','OpenRemoteStudio-onefile.spec'):
            with self.subTest(filename=filename):
                spec=(application/'windows'/filename).read_text(encoding='utf-8')
                self.assertIn('root = Path(SPECPATH).resolve().parent.parent',spec)
                self.assertIn("str(root / 'qt_app.py')",spec)
                self.assertIn('pathex=[str(root)]',spec)
                self.assertNotIn("root = Path(SPECPATH).resolve().parent\n",spec)


if __name__=='__main__':
    unittest.main()
