"""Persistence safety tests: malformed snapshots must not reach disk."""
import json
import tempfile
import unittest
from pathlib import Path
from core import Store


class RegistrySnapshotTests(unittest.TestCase):
    def test_save_rejects_duplicate_ids_without_touching_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "connections.json"
            store = Store(path)
            store.upsert({"name": "one", "host": "one.example", "protocol": "SSH"})
            original = path.read_bytes()
            store.items = [dict(store.items[0]), dict(store.items[0])]
            with self.assertRaisesRegex(ValueError, "dupliqués"):
                store.save()
            self.assertEqual(path.read_bytes(), original)

    def test_save_rejects_invalid_snapshot_without_touching_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "connections.json"
            store = Store(path)
            store.upsert({"name": "one", "host": "one.example", "protocol": "SSH"})
            original = path.read_bytes()
            store.items.append({"name": "bad", "host": "", "protocol": "SSH"})
            with self.assertRaises(ValueError):
                store.save()
            self.assertEqual(path.read_bytes(), original)

    def test_save_normalizes_optional_null_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "connections.json"
            store = Store(path)
            store.items = [{"name": "one", "host": "one.example", "protocol": "SSH", "user": None}]
            store.save()
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored[0]["user"], "")
            self.assertEqual(len(stored[0]["id"]), 36)


if __name__ == "__main__":
    unittest.main()
