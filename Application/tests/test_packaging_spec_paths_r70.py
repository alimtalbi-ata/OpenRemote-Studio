"""R70 regression: Windows builds must work from a standalone PR branch.

Static checks do not constitute a Windows build. Author: Abdelhalim Talbi.
"""
import ast
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
APP_DIR = REPO / 'Application'
SPEC_DIR = APP_DIR / 'windows'


class WindowsSpecEntrypointR70(unittest.TestCase):
    def test_application_entrypoint_exists(self):
        self.assertTrue((APP_DIR / 'qt_app.py').is_file())
        self.assertTrue((REPO / 'VERSION.txt').is_file())

    def test_specs_compile_as_python(self):
        for name in ('OpenRemoteStudio.spec', 'OpenRemoteStudio-onefile.spec'):
            with self.subTest(name=name):
                compile((SPEC_DIR / name).read_text(encoding='utf-8'), name, 'exec')

    def test_specs_resolve_specpath_without_ascending_to_repo_root(self):
        for name in ('OpenRemoteStudio.spec', 'OpenRemoteStudio-onefile.spec'):
            with self.subTest(name=name):
                tree = ast.parse((SPEC_DIR / name).read_text(encoding='utf-8'))
                roots = [n for n in tree.body if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == 'root' for t in n.targets)]
                self.assertEqual(len(roots), 1)
                expr = ast.unparse(roots[0].value)
                self.assertEqual(expr, 'Path(SPECPATH).resolve().parent')

    def test_specs_reference_app_and_version_relative_to_spec(self):
        for name in ('OpenRemoteStudio.spec', 'OpenRemoteStudio-onefile.spec'):
            with self.subTest(name=name):
                content = (SPEC_DIR / name).read_text(encoding='utf-8')
                self.assertIn("root / 'qt_app.py'", content)
                self.assertIn("root.parent / 'VERSION.txt'", content)
                self.assertIn('pathex=[str(root)]', content)


if __name__ == '__main__':
    unittest.main()
