"""R104 regression: outer and nested source manifests are both mandatory."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from verify_cumulative_v318 import verify, REQUIRED

class ArchiveManifestVerifierR104(unittest.TestCase):
    def _archive(self, path, *, broken_source=False):
        files = {
            '03-Sources/Application/core.py': b'print("safe")',
            '03-Sources/07-Manifestes/FILES-SHA256.txt': b'',
            '07-Manifestes/provenance.json': json.dumps({'commit': 'a'*40,
                'windows_build_run': '42'}).encode(),
        }
        data = files['03-Sources/Application/core.py']
        digest = hashlib.sha256(data).hexdigest()
        files['03-Sources/07-Manifestes/FILES-SHA256.txt'] = (
            ('0'*64 if broken_source else digest) + '  Application/core.py\n').encode()
        outer = [f'{hashlib.sha256(v).hexdigest()}  {k}' for k,v in sorted(files.items())]
        files['07-Manifestes/FILES-SHA256.txt'] = ('\n'.join(outer)+'\n').encode()
        with zipfile.ZipFile(path, 'w') as z:
            for prefix in REQUIRED: z.writestr(prefix, b'')
            for name, value in files.items(): z.writestr(name, value)

    def test_good_nested_manifest_passes(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'valid.zip'
            self._archive(path)
            self.assertEqual(verify(path, 'a'*40)['status'], 'PASS')

    def test_bad_nested_manifest_fails_even_if_outer_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'bad.zip'
            self._archive(path, broken_source=True)
            result = verify(path, 'a'*40)
            self.assertEqual(result['status'], 'FAIL')
            self.assertTrue(any('03-Sources' in error for error in result['errors']))

if __name__ == '__main__':
    unittest.main()
