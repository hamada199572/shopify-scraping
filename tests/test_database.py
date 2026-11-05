import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src import database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_prices.db"
        self.db_path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        database.init_db()

    def tearDown(self) -> None:
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def test_init_is_repeatable_and_creates_history_index(self) -> None:
        database.init_db()
        with closing(sqlite3.connect(self.db_path)) as connection:
            indexes = connection.execute(
                "PRAGMA index_list(product_history)"
            ).fetchall()

        self.assertIn("idx_product_history_variant_time", [index[1] for index in indexes])

    def test_inserts_snapshot_records(self) -> None:
        inserted = database.insert_product_records([self.record()])
        with closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(
                "SELECT variant_id, variant_price FROM product_history"
            ).fetchall()

        self.assertEqual(inserted, 1)
        self.assertEqual(rows, [("variant-1", "129.99")])

    def test_batch_insert_rolls_back_on_invalid_value(self) -> None:
        invalid = self.record()
        invalid["variant_price"] = object()

        with self.assertRaises(database.DatabaseError):
            database.insert_product_records([self.record(), invalid])

        with closing(sqlite3.connect(self.db_path)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM product_history"
            ).fetchone()[0]
        self.assertEqual(count, 0)

    @staticmethod
    def record() -> dict[str, str]:
        return {
            "scraper_time": "2026-11-05 10:00:00 +0400",
            "product_id": "product-1",
            "product_title": "Trail Runner",
            "variant_id": "variant-1",
            "variant_title": "Blue / 8",
            "variant_price": "129.99",
            "compare_at_price": "149.99",
            "variant_sku": "TR-8-BL",
            "update_time": "2026-11-05 10:00:00 +0000",
            "url": "https://example.com/products/trail-runner",
        }


if __name__ == "__main__":
    unittest.main()
