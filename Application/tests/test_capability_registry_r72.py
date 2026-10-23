"""Acceptance tests for the 12-product capability registry. Author: Abdelhalim Talbi."""
import unittest
from dataclasses import replace
from capability_registry import CAPABILITIES, Capability, Status, validate_registry


class CapabilityRegistryTests(unittest.TestCase):
    def test_all_twelve_reference_products_are_present(self):
        self.assertTrue(validate_registry())
        self.assertEqual(len(CAPABILITIES), 12)
        self.assertEqual(len({c.product for c in CAPABILITIES}), 12)

    def test_unverified_is_not_claimed_implemented(self):
        self.assertTrue(all(c.status == Status.UNVERIFIED for c in CAPABILITIES))

    def test_implemented_requires_evidence(self):
        entries = list(CAPABILITIES)
        entries[0] = replace(entries[0], status=Status.IMPLEMENTED)
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            validate_registry(entries)
        entries[0] = replace(entries[0], evidence=("tests/test_ssh.py",))
        self.assertTrue(validate_registry(entries))

    def test_duplicate_product_rejected(self):
        entries = list(CAPABILITIES)
        entries[-1] = entries[0]
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_registry(entries)

    def test_invalid_priority_rejected(self):
        entries = list(CAPABILITIES)
        entries[0] = replace(entries[0], priority="P9")
        with self.assertRaisesRegex(ValueError, "priority"):
            validate_registry(entries)


if __name__ == "__main__":
    unittest.main()
