"""R110/R114: cumulative package must contain every named, valid Qt UI capture."""
from pathlib import Path
import tempfile
import unittest

from build_cumulative_v318 import PNG_SIGNATURE, UI_CAPTURE_NAMES, collect_required_ui_captures


class ArchiveUICaptureR110(unittest.TestCase):
    def test_both_required_pngs_are_collected_in_stable_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in UI_CAPTURE_NAMES:
                (root / name).write_bytes(PNG_SIGNATURE + b"R110-CI-CAPTURE" + bytes(128))
            found = collect_required_ui_captures(root)
            self.assertEqual([name for name, _ in found], list(UI_CAPTURE_NAMES))
            self.assertTrue(all(data.startswith(PNG_SIGNATURE) for _, data in found))
            self.assertTrue(all(len(data) >= 128 for _, data in found))

    def test_missing_capture_blocks_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / UI_CAPTURE_NAMES[0]).write_bytes(PNG_SIGNATURE + bytes(128))
            with self.assertRaisesRegex(SystemExit, "Missing required Qt UI capture"):
                collect_required_ui_captures(root)

    def test_invalid_png_signature_blocks_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in UI_CAPTURE_NAMES:
                (root / name).write_bytes(b"NOT-PNG" + bytes(128))
            with self.assertRaisesRegex(SystemExit, "Invalid Qt UI capture"):
                collect_required_ui_captures(root)


if __name__ == "__main__":
    unittest.main()
