"""Execute both packaging recipes with the SPECPATH supplied by PyInstaller."""
import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class PackagingPathTests(unittest.TestCase):
    def test_specs_resolve_entrypoint_and_version_from_any_working_directory(self):
        app = Path(__file__).resolve().parents[1]

        def analysis(scripts, **kwargs):
            self.assertEqual([Path(s).resolve() for s in scripts], [app / 'qt_app.py'])
            self.assertEqual(Path(kwargs['pathex'][0]), app)
            for source, _ in kwargs['datas']:
                self.assertTrue(Path(source).is_file(), source)
            return types.SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])

        hooks = types.ModuleType('PyInstaller.utils.hooks')
        hooks.collect_submodules = lambda name: [name]
        modules = {name: types.ModuleType(name) for name in ('PyInstaller', 'PyInstaller.utils')}
        modules['PyInstaller.utils.hooks'] = hooks
        for filename in ('OpenRemoteStudio.spec', 'OpenRemoteStudio-onefile.spec'):
            with self.subTest(spec=filename), patch.dict(sys.modules, modules):
                runpy.run_path(str(app / 'windows' / filename), init_globals={
                    'SPECPATH': str(app / 'windows'), 'Analysis': analysis,
                    'PYZ': lambda *a, **k: [], 'EXE': lambda *a, **k: [],
                    'COLLECT': lambda *a, **k: [],
                })
