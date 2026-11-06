"""Analyze historical product prices and detect price changes between scraping sessions."""

import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

# Define the local database path
DB_PATH = Path(__file__).resolve().parent.parent / "prices.db"


class AnalyzerError(RuntimeError):
    """Raised when price history cannot be analyzed."""


def _as_price(value: Any) -> Decimal | None:
    """Convert a stored price to Decimal, returning None for missing or invalid values."""
    if value is None or not str(value).strip():
        return None
    try:
        price = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return price if price.is_finite() else None


def detect_price_changes() -> list[dict[str, Any]]:
    """Compare product variant prices between consecutive scraping runs to detect changes."""
    if not DB_PATH.exists():
        raise AnalyzerError(f"Database file not found at {DB_PATH}. Run the scraper first.")

    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                WITH RankedPrices AS (
                    SELECT 
                        id,
                        product_title,
                        variant_title,
                        variant_price,
                        compare_at_price,
                        scraper_time,
                        url,
                        variant_id,
                        LAG(variant_price) OVER (
                            PARTITION BY variant_id ORDER BY scraper_time ASC, id ASC
                        ) AS prev_price,
                        LAG(scraper_time) OVER (
                            PARTITION BY variant_id ORDER BY scraper_time ASC, id ASC
                        ) AS prev_time
                    FROM product_history
                )
                SELECT * FROM RankedPrices
                WHERE prev_price IS NOT NULL
                ORDER BY scraper_time DESC, id DESC
            """
            rows = conn.execute(query).fetchall()

        changes: list[dict[str, Any]] = []
        for row in rows:
            previous = _as_price(row["prev_price"])
            current = _as_price(row["variant_price"])
            if previous is not None and current is not None and previous != current:
                changes.append(dict(row))

        logger.info("Detected %d price changes compared to previous runs.", len(changes))
        return changes
    except sqlite3.Error as exc:
        logger.exception("Failed to analyze historical price changes.")
        raise AnalyzerError("Could not read price history from the database") from exc


def print_price_tracker_report() -> None:
    """Format and print a detailed price change report to the console."""
    changes = detect_price_changes()
    
    if not changes:
        print("\nNo price changes found. The same variants need at least two recorded snapshots to compare.\n")
        return

    print("\n" + "=" * 80)
    print(f" 📊 Historical Price Change Report ({len(changes)} item(s) changed) 📊")
    print("=" * 80)
    
    for idx, item in enumerate(changes, 1):
        old_p = _as_price(item["prev_price"])
        new_p = _as_price(item["variant_price"])
        diff = new_p - old_p if old_p is not None and new_p is not None else Decimal(0)
        status = "📉 Price Drop!" if diff < 0 else "📈 Price Increase"
            
        print(f"{idx}. Product: {item['product_title']}")
        print(f"   - Variant: {item['variant_title'] or 'Default'}")
        print(f"   - Status: {status}")
        print(f"   - Previous Price ({item['prev_time']}): {item['prev_price']}")
        print(f"   - Current Price ({item['scraper_time']}): {item['variant_price']}")
        print(f"   - URL: {item['url']}")
        print("-" * 80)


if __name__ == "__main__":
    try:
        print_price_tracker_report()
    except AnalyzerError as exc:
        logger.error("Price analysis failed: %s", exc)
        raise SystemExit(1) from None
