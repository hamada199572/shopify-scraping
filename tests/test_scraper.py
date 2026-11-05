import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src import database, scraper


class FakeElement:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeDriver:
    def __init__(self, pages: list[str]) -> None:
        self.pages = pages
        self.page_index = -1
        self.closed = False

    def get(self, _url: str) -> None:
        self.page_index += 1

    def find_element(self, _by: str, _value: str) -> FakeElement:
        return FakeElement(self.pages[self.page_index])

    def quit(self) -> None:
        self.closed = True


class ScraperTests(unittest.TestCase):
    def test_rejects_invalid_collection_handle(self) -> None:
        with self.assertRaises(ValueError):
            scraper.get_all_collection_products("../invalid")

    def test_invalid_json_fails_instead_of_returning_partial_products(self) -> None:
        driver = FakeDriver(['{"products": [{"id": 1}]}', "not-json"])
        with patch("src.scraper.Driver", return_value=driver):
            with self.assertRaises(scraper.ScraperError):
                scraper.get_all_collection_products("mens-bestsellers")

        self.assertTrue(driver.closed)

    def test_main_does_not_store_partial_collection_after_page_failure(self) -> None:
        driver = FakeDriver(['{"products": [{"id": 1}]}', "not-json"])
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "prices.db"
            with (
                patch.object(database, "DB_PATH", db_path),
                patch("src.scraper.Driver", return_value=driver),
                patch.object(sys, "argv", ["scraper", "--collection", "trail-runners"]),
            ):
                with self.assertRaises(SystemExit) as exit_context:
                    scraper.main()

        self.assertEqual(exit_context.exception.code, 1)
        self.assertFalse(db_path.exists())
        self.assertTrue(driver.closed)

    def test_main_persists_scraped_history_without_csv_export(self) -> None:
        product = {
            "id": 10,
            "title": "Trail Runner",
            "handle": "trail-runner",
            "variants": [{"id": 11, "title": "Blue / 8", "price": "129.99"}],
        }
        driver = FakeDriver([
            json.dumps({"products": [product]}),
            json.dumps({"products": []}),
        ])
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "prices.db"
            with (
                patch.object(database, "DB_PATH", db_path),
                patch("src.scraper.Driver", return_value=driver),
                patch.object(sys, "argv", ["scraper", "--collection", "trail-runners"]),
            ):
                scraper.main()

            with closing(sqlite3.connect(db_path)) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM product_history"
                ).fetchone()[0]

        self.assertEqual(count, 1)
        self.assertTrue(driver.closed)


if __name__ == "__main__":
    unittest.main()
