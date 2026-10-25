"""R104: source manifest must match bytes that actually ship in cumulative ZIP."""
import hashlib
import unittest
from build_cumulative_v318 import reconcile_archive_source_manifest

class ArchiveSourceManifestR104(unittest.TestCase):
    def test_excludes_untracked_workspace_and_reconciles_changed_metadata(self):
        files = {
            '03-Sources/Application/main.py': b'print(1)\n',
            '03-Sources/Application/windows/version.generated.iss': b'#define V "31.8"\n',
            '03-Sources/07-Manifestes/FILES-SHA256.txt':
                b'bad  05-Documentation/Dossier-V31.8.pdf\n',
            '05-Documentation/Dossier-V31.8.pdf': b'%PDF-1.4',
        }
        self.assertEqual(reconcile_archive_source_manifest(files), 2)
        rows = files['03-Sources/07-Manifestes/FILES-SHA256.txt'].decode().splitlines()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows, [
            f"{hashlib.sha256(files['03-Sources/Application/main.py']).hexdigest()}  Application/main.py",
            f"{hashlib.sha256(files['03-Sources/Application/windows/version.generated.iss']).hexdigest()}  Application/windows/version.generated.iss",
        ])
        self.assertNotIn('Dossier-V31.8.pdf', '\n'.join(rows))

    def test_idempotent_and_empty_source_snapshot(self):
        files = {'03-Sources/07-Manifestes/FILES-SHA256.txt': b'stale'}
        self.assertEqual(reconcile_archive_source_manifest(files), 0)
        self.assertEqual(files['03-Sources/07-Manifestes/FILES-SHA256.txt'], b'\n')
        self.assertEqual(reconcile_archive_source_manifest(files), 0)

if __name__ == '__main__':
    unittest.main()
