"""SQLite persistence for scraped Shopify variant snapshots."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)
DB_PATH = Path(__file__).resolve().parent.parent / "prices.db"


class DatabaseError(RuntimeError):
    """Raised when the database cannot be initialized or updated."""


def init_db() -> None:
    """Create the history table and its lookup index if they do not exist."""
    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS product_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scraper_time TEXT NOT NULL,
                        product_id TEXT,
                        product_title TEXT,
                        variant_id TEXT NOT NULL,
                        variant_title TEXT,
                        variant_price TEXT,
                        compare_at_price TEXT,
                        variant_sku TEXT,
                        update_time TEXT,
                        url TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_product_history_variant_time
                    ON product_history (variant_id, scraper_time)
                    """
                )
    except sqlite3.Error as exc:
        logger.exception("Failed to initialize database at %s", DB_PATH)
        raise DatabaseError("Could not initialize the price history database") from exc

    logger.info("Database initialized at %s", DB_PATH)


def insert_product_records(rows: list[dict[str, Any]]) -> int:
    """Atomically insert cleaned variant snapshots and return the inserted count."""
    if not rows:
        logger.warning("No product records to insert")
        return 0

    values = [
        (
            row.get("scraper_time"),
            row.get("product_id"),
            row.get("product_title"),
            row.get("variant_id"),
            row.get("variant_title"),
            row.get("variant_price"),
            row.get("compare_at_price"),
            row.get("variant_sku"),
            row.get("update_time"),
            row.get("url"),
        )
        for row in rows
    ]

    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO product_history (
                        scraper_time, product_id, product_title, variant_id,
                        variant_title, variant_price, compare_at_price,
                        variant_sku, update_time, url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
    except sqlite3.Error as exc:
        logger.exception("Failed to insert records into database at %s", DB_PATH)
        raise DatabaseError("Could not write product history records") from exc

    logger.info("Inserted %d product records", len(rows))
    return len(rows)
