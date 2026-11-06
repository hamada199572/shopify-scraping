import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import analayzer, database


class AnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_prices.db"
        self.database_path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.analyzer_path_patch = patch.object(analayzer, "DB_PATH", self.db_path)
        self.database_path_patch.start()
        self.analyzer_path_patch.start()
        database.init_db()

    def tearDown(self) -> None:
        self.analyzer_path_patch.stop()
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_detects_numeric_change_but_ignores_format_only_difference(self) -> None:
        database.insert_product_records([
            self.record("2026-11-05 10:00:00 +0400", "10.0", "variant-down"),
            self.record("2026-11-06 10:00:00 +0400", "10.00", "variant-down"),
            self.record("2026-11-07 10:00:00 +0400", "8.75", "variant-down"),
            self.record("2026-11-05 10:00:00 +0400", "5.00", "variant-up"),
            self.record("2026-11-07 10:00:00 +0400", "7.00", "variant-up"),
        ])

        changes = analayzer.detect_price_changes()

        self.assertEqual(len(changes), 2)
        changes_by_variant = {item["variant_id"]: item for item in changes}
        self.assertEqual(changes_by_variant["variant-down"]["prev_price"], "10.00")
        self.assertEqual(changes_by_variant["variant-down"]["variant_price"], "8.75")
        self.assertEqual(changes_by_variant["variant-up"]["prev_price"], "5.00")
        self.assertEqual(changes_by_variant["variant-up"]["variant_price"], "7.00")

    def test_missing_database_raises_clear_analyzer_error(self) -> None:
        self.db_path.unlink()

        with self.assertRaisesRegex(analayzer.AnalyzerError, "Database file not found"):
            analayzer.detect_price_changes()

    @staticmethod
    def record(scraper_time: str, price: str, variant_id: str) -> dict[str, str]:
        return {
            "scraper_time": scraper_time,
            "product_id": "product-1",
            "product_title": "Trail Runner",
            "variant_id": variant_id,
            "variant_title": "Blue / 8",
            "variant_price": price,
            "compare_at_price": "",
            "variant_sku": "TR-8-BL",
            "update_time": "",
            "url": "https://example.com/products/trail-runner",
        }


if __name__ == "__main__":
    unittest.main()
