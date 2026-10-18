"""V27.4: fail closed on incomplete or duplicate release manifests."""
import unittest, tempfile, hashlib
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('release_verify_v274', ROOT/'VERIFY-RELEASE.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)

class ManifestCoverageTests(unittest.TestCase):
    def test_unlisted_file_blocks_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'VERSION.txt').write_text('27.4')
            (root/'README.md').write_text('hello')
            (root/'07-Manifestes').mkdir()
            digest=hashlib.sha256((root/'VERSION.txt').read_bytes()).hexdigest()
            (root/'07-Manifestes/FILES-SHA256.txt').write_text(f'{digest}  VERSION.txt\n')
            issues=verify.validate(root)
            self.assertIn('Non référencé: README.md',issues)
    def test_duplicate_manifest_entry_blocks_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'VERSION.txt').write_text('27.4')
            (root/'07-Manifestes').mkdir()
            digest=hashlib.sha256((root/'VERSION.txt').read_bytes()).hexdigest()
            line=f'{digest}  VERSION.txt\n'
            (root/'07-Manifestes/FILES-SHA256.txt').write_text(line+line)
            self.assertIn('Entrée manifeste dupliquée: VERSION.txt',verify.validate(root))

if __name__=='__main__': unittest.main()
