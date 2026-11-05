"""Scrape products from a Shopify collection's public JSON endpoint."""

import argparse
import json
import re
from typing import Any

from seleniumbase import Driver
from selenium.common.exceptions import WebDriverException

from config.settings import BASE_DOMAIN
from src.cleaner import clean_products
from src.database import DatabaseError, init_db, insert_product_records
from utils.logger import get_logger

logger = get_logger(__name__)


class ScraperError(RuntimeError):
    """Raised when a collection cannot be fetched completely."""


def get_all_collection_products(collection_name: str) -> list[dict[str, Any]]:
    """Fetch every page of a collection or raise instead of returning partial data."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", collection_name):
        raise ValueError("Collection handle contains unsupported characters")

    logger.info("Starting scrape for collection '%s'", collection_name)
    all_products: list[dict[str, Any]] = []
    driver: Any = None
    try:
        driver = Driver(uc=True, headless=True)
        page = 1
        while True:
            url = f"{BASE_DOMAIN}/collections/{collection_name}/products.json?page={page}"
            logger.info("Scraping page %d: %s", page, url)
            try:
                driver.get(url)
                body_text = driver.find_element("tag name", "body").text
            except WebDriverException as exc:
                raise ScraperError(f"Browser request failed on page {page}") from exc
            try:
                data = json.loads(body_text)
            except json.JSONDecodeError as exc:
                raise ScraperError(f"Invalid JSON returned on page {page}") from exc
            if not isinstance(data, dict):
                raise ScraperError(f"Unexpected JSON structure on page {page}")
            products = data.get("products", [])
            if not isinstance(products, list):
                raise ScraperError(f"'products' is not a list on page {page}")
            if not products:
                logger.info("Reached the end of the collection")
                break
            if any(not isinstance(item, dict) for item in products):
                raise ScraperError(f"Malformed product record on page {page}")
            all_products.extend(products)
            logger.info("Fetched %d products from page %d (%d total)", len(products), page, len(all_products))
            page += 1
    finally:
        if driver is not None:
            try:
                logger.info("Closing browser")
                driver.quit()
            except Exception:
                logger.exception("Failed to close browser cleanly")
    return all_products


def main() -> None:
    """Main execution function to handle CLI arguments, scrape, clean, and store product history."""
    parser = argparse.ArgumentParser(description="Scrape products from a Shopify collection.")
    parser.add_argument("--collection", type=str, default="mens-bestsellers",
                        help="Collection handle (for example: womens-shoes or sale)")
    args = parser.parse_args()

    try:
        products = get_all_collection_products(args.collection)
        cleaned_products = clean_products(products)
        init_db()
        inserted_count = insert_product_records(cleaned_products)
    except (ScraperError, DatabaseError, WebDriverException, ValueError):
        logger.exception("Scraping pipeline failed")
        raise SystemExit(1) from None
    except Exception:
        logger.exception("Unexpected error in scraping pipeline")
        raise SystemExit(1) from None

    logger.info("Scraping pipeline completed; stored %d variant snapshots", inserted_count)

if __name__ == "__main__":
    main()
