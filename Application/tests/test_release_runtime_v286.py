import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version_info import read_application_version

ROOT=Path(__file__).resolve().parents[2]
class RuntimePackagingTests(unittest.TestCase):
    def test_source_version(self):
        self.assertEqual(read_application_version(ROOT/'Application'), (ROOT/'VERSION.txt').read_text().strip())
    def test_missing_version_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):read_application_version(Path(d)/'Application')
    def test_specs_bundle_version(self):
        for name in ('OpenRemoteStudio.spec','OpenRemoteStudio-onefile.spec'):
            source=(ROOT/'Application/windows'/name).read_text()
            self.assertIn("root.parent / 'VERSION.txt'",source)
            self.assertIn("'.'",source)
    def test_qt_title_is_dynamic(self):
        source=(ROOT/'Application/qt_app.py').read_text()
        self.assertIn("'OpenRemote Studio V'+application_version()",source)
        self.assertNotIn("setWindowTitle('OpenRemote Studio V24.2",source)
