"""Scrape products from a Shopify collection's public JSON endpoint."""

import argparse
import json
from typing import Any

from seleniumbase import Driver

from config.settings import BASE_DOMAIN
from src.cleaner import clean_products, export_to_csv
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_collection_products(collection_name: str) -> list[dict[str, Any]]:
    """Fetch all products for a collection, returning products fetched so far."""
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
            except Exception:
                logger.exception("HTTP/browser request failed for page %d", page)
                break
            try:
                data = json.loads(body_text)
            except json.JSONDecodeError:
                logger.exception("Invalid JSON returned for page %d", page)
                break
            if not isinstance(data, dict):
                logger.error("Unexpected JSON structure on page %d", page)
                break
            products = data.get("products", [])
            if not isinstance(products, list):
                logger.error("'products' is not a list on page %d", page)
                break
            if not products:
                logger.info("Reached the end of the collection")
                break
            all_products.extend(item for item in products if isinstance(item, dict))
            logger.info("Fetched %d products from page %d (%d total)", len(products), page, len(all_products))
            page += 1
    except Exception:
        logger.exception("Unexpected error while scraping collection '%s'", collection_name)
    finally:
        if driver is not None:
            try:
                logger.info("Closing browser")
                driver.quit()
            except Exception:
                logger.exception("Failed to close browser cleanly")
    return all_products


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape products from a Shopify collection.")
    parser.add_argument("--collection", type=str, default="mens-bestsellers",
                        help="Collection handle (for example: womens-shoes or sale)")
    args = parser.parse_args()
    products = get_all_collection_products(args.collection)
    cleaned_products = clean_products(products)
    export_to_csv(cleaned_products, args.collection)


if __name__ == "__main__":
    main()
