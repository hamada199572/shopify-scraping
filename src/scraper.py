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
    """Raised when a product listing cannot be fetched completely."""


def _get_all_products(endpoint: str, listing_name: str) -> list[dict[str, Any]]:
    """Fetch every page from a Shopify products JSON endpoint."""
    logger.info("Starting scrape for %s", listing_name)
    all_products: list[dict[str, Any]] = []
    driver: Any = None
    try:
        driver = Driver(uc=True, headless=True)
        page = 1
        while True:
            path = f"/{endpoint}/products.json" if endpoint else "/products.json"
            url = f"{BASE_DOMAIN}{path}?limit=250&page={page}"
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
                logger.info("Reached the end of %s", listing_name)
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


def get_all_collection_products(collection_name: str) -> list[dict[str, Any]]:
    """Fetch every page of a collection or raise instead of returning partial data."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", collection_name):
        raise ValueError("Collection handle contains unsupported characters")
    return _get_all_products(f"collections/{collection_name}", f"collection '{collection_name}'")


def get_all_catalog_products() -> list[dict[str, Any]]:
    """Fetch every page of the store-wide products JSON endpoint."""
    return _get_all_products("", "the full catalog")


def main() -> None:
    """Main execution function to handle CLI arguments, scrape, clean, and store product history."""
    parser = argparse.ArgumentParser(description="Scrape the full Shopify catalog or selected collections.")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--all", dest="all_catalog", action="store_true",
                              help="Fetch the full store catalog (default)")
    source_group.add_argument("--collection", nargs="+", metavar="HANDLE",
                              help="One or more collection handles, such as sale mens-shoes")
    args = parser.parse_args()

    try:
        if args.all_catalog or args.collection is None:
            products = get_all_catalog_products()
        else:
            products = []
            for collection_name in args.collection:
                products.extend(get_all_collection_products(collection_name))

        # A product can appear in both the full catalog and the selected collection.
        products_by_id = {str(product.get("id")): product for product in products}
        products = list(products_by_id.values())
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
