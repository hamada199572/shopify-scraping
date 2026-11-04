import csv
import os
from datetime import datetime
from typing import Any

from config.settings import BASE_DOMAIN
from utils.logger import get_logger

logger = get_logger(__name__)


def clean_products(raw_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Shopify products into flat rows, one per variant."""
    rows: list[dict[str, Any]] = []
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    for product in raw_products:
        if not isinstance(product, dict):
            logger.warning("Skipping product with unexpected type %s", type(product).__name__)
            continue
        product_url = f"{BASE_DOMAIN}/products/{product.get('handle', '')}"
        variants = product.get("variants", [])
        if not isinstance(variants, list):
            logger.warning("Skipping malformed variants for product %s", product.get("id"))
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                logger.warning("Skipping malformed variant for product %s", product.get("id"))
                continue
            raw_update = variant.get("updated_at")
            update_time = ""
            if raw_update:
                try:
                    update_time = datetime.fromisoformat(
                        str(raw_update).replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M:%S %z")
                except (ValueError, TypeError):
                    logger.warning("Could not parse updated_at value %r", raw_update)
                    update_time = str(raw_update)
            rows.append({
                "scraper_time": timestamp,
                "product_id": product.get("id"),
                "product_title": product.get("title"),
                "variant_id": variant.get("id"),
                "variant_title": variant.get("title"),
                "variant_price": variant.get("price"),
                "compare_at_price": variant.get("compare_at_price") or "",
                "variant_sku": variant.get("sku"),
                "update_time": update_time,
                "url": product_url,
            })
    logger.info("Cleaned %d variants from %d products", len(rows), len(raw_products))
    return rows


def export_to_csv(rows: list[dict[str, Any]], collection_name: str) -> str | None:
    """Export rows to CSV and return the generated path, or None on failure."""
    output_dir = "output"
    filename = f"{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(output_dir, filename)
    fieldnames = list(rows[0].keys()) if rows else [
        "scraper_time", "product_id", "product_title", "variant_id", "variant_title",
        "variant_price", "compare_at_price", "variant_sku", "update_time", "url",
    ]
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, csv.Error):
        logger.exception("Failed to export CSV to %s", file_path)
        return None
    logger.info("Exported %d rows to %s", len(rows), file_path)
    return file_path
