"""Cross-store schema and atomic write regression tests. Author: Abdelhalim Talbi."""
import json
import tempfile
import unittest
from pathlib import Path

from core import Store
from routes import RouteStore
from pam_profiles import PamProfileStore


class StoreSchemaIsolationTests(unittest.TestCase):
    def test_route_store_rejects_duplicates_without_overwriting_existing_data(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "routes.json"
            store = RouteStore(path)
            store.items = [{"id": "one", "route": {"mode": "direct"}}]
            store.save()
            original = path.read_bytes()
            store.items.append(dict(store.items[0]))
            with self.assertRaisesRegex(ValueError, "dupliquées"):
                store.save()
            self.assertEqual(path.read_bytes(), original)

    def test_profile_store_rejects_duplicates_without_overwriting_existing_data(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "profiles.json"
            store = PamProfileStore(path)
            valid = {"name": "one", "provider": "cyberark", "endpoint": "https://vault.example"}
            # Only exercise duplicate validation if the configured provider is supported.
            from pam_refs import PROVIDERS
            valid["provider"] = next(iter(PROVIDERS))
            store.items = [valid]
            store.save()
            original = path.read_bytes()
            store.items.append({**valid, "name": "ONE"})
            with self.assertRaisesRegex(ValueError, "dupliqués"):
                store.save()
            self.assertEqual(path.read_bytes(), original)

    def test_connection_store_still_requires_connection_schema(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / "connections.json")
            store.items = [{"id": "one", "route": {"mode": "direct"}}]
            with self.assertRaises(ValueError):
                store.save()
            self.assertFalse(store.path.exists())


if __name__ == "__main__":
    unittest.main()
