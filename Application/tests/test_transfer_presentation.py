"""Pure transfer presentation tests without Qt or network access."""
import unittest
from transfer_presentation import (
    TRANSFER_COLUMNS, transfer_query_state, transfer_row_cells, transfer_count_label
)


class TransferPresentationTests(unittest.TestCase):
    def test_all_filter_is_unrestricted(self):
        self.assertIsNone(transfer_query_state("Tous"))
        self.assertEqual(transfer_query_state("failed"), "failed")

    def test_valid_row_has_eight_display_cells(self):
        row = (1, "server", "upload", "/remote", "C:/local", "done", 100, None)
        cells = transfer_row_cells(row)
        self.assertEqual(len(cells), len(TRANSFER_COLUMNS))
        self.assertEqual(cells[-1], "")

    def test_malformed_row_rejected(self):
        for row in (None, "not a row", (), [1]):
            with self.subTest(row=row), self.assertRaises(ValueError):
                transfer_row_cells(row)

    def test_count_rejects_invalid(self):
        self.assertIn("2 entrées", transfer_count_label(2))
        with self.assertRaises(ValueError):
            transfer_count_label(-1)


if __name__ == "__main__":
    unittest.main()
