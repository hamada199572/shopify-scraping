import unittest
from unittest.mock import patch

from src.cleaner import clean_products


class CleanProductsTests(unittest.TestCase):
    def test_flattens_variants_and_preserves_price_strings(self) -> None:
        products = [
            {
                "id": 123,
                "title": "Trail Runner",
                "handle": "trail-runner",
                "variants": [
                    {
                        "id": 456,
                        "title": "Blue / 8",
                        "price": "129.99",
                        "compare_at_price": "149.99",
                        "sku": "TR-8-BL",
                        "updated_at": "2026-11-05T10:00:00Z",
                    }
                ],
            }
        ]

        rows = clean_products(products)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["variant_price"], "129.99")
        self.assertEqual(rows[0]["compare_at_price"], "149.99")
        self.assertEqual(rows[0]["url"], "https://www.allbirds.com/products/trail-runner")
        self.assertTrue(rows[0]["update_time"].startswith("2026-11-05 10:00:00"))

    def test_skips_malformed_variants(self) -> None:
        with patch("src.cleaner.logger.warning") as warning:
            rows = clean_products([{"id": 1, "variants": "invalid"}])

        self.assertEqual(rows, [])
        warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
