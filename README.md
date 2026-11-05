# Shopify Collection Price Tracker

A modular Python scraper that retrieves product and variant data from a Shopify collection's public JSON endpoint, normalizes it, and stores each scraped snapshot in a local SQLite database (`prices.db`) for price tracking and analysis. The default store is Allbirds; pass a collection handle to choose which collection to scrape.

## Project objectives

- Collect product and variant identifiers, titles, prices, compare-at prices, SKUs, update times, and product URLs.
- Keep scraping, data cleaning, database persistence, configuration, and logging responsibilities separate.
- Store historical variant snapshots in the `product_history` table for monitoring price changes and trends.
- Record operational messages in the console and rotating UTF-8 log files.

## Architecture

- `src/scraper.py` — command-line entry point using `argparse` and `main()`; fetches collection pages and coordinates cleaning and database persistence.
- `src/cleaner.py` — transforms Shopify product JSON into standardized flat records, one per variant, through `clean_products()`.
- `src/database.py` — initializes the SQLite database and `product_history` table with `init_db()`, and inserts snapshots with `insert_product_records()`.
- `utils/logger.py` — configures named Python loggers with console output and rotating UTF-8 log files under `logs/`.
- `config/settings.py` — holds the store base domain (`BASE_DOMAIN`).

## Database schema

The `product_history` table stores each scraped variant snapshot:

| Column | Description |
| --- | --- |
| `id` | Auto-incrementing primary key |
| `scraper_time` | Timestamp of the scraping run |
| `product_id` | Shopify product identifier |
| `product_title` | Product name |
| `variant_id` | Shopify variant identifier |
| `variant_title` | Variant option, such as color or size |
| `variant_price` | Current variant price |
| `compare_at_price` | Original or comparison price |
| `variant_sku` | Stock Keeping Unit (SKU) |
| `update_time` | Last updated timestamp from Shopify |
| `url` | Direct link to the product page |

## Requirements

- Python 3.10 or newer
- A compatible browser and driver supported by SeleniumBase
- Internet access to the configured Shopify store

## Installation

From the repository root, create and activate a virtual environment, then install dependencies:

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Run from the repository root. The `--collection` argument is optional and defaults to `mens-bestsellers`:

```bash
python -m src.scraper
```

Choose another Shopify collection by passing its handle:

```bash
python -m src.scraper --collection mens-bestsellers
```

For example, scrape the `womens-shoes` collection:

```bash
python -m src.scraper --collection womens-shoes
```

Each run stores variant snapshots in `prices.db` and logs to the terminal and `logs/scraper.log`. Log files, SQLite database files, downloaded files, and local virtual environments are excluded from Git.

## Tests

Run the local unit and integration tests with Python's standard library:

```bash
python -m unittest discover -v
```

The scraper tests use a mocked browser and temporary SQLite databases; they do not send requests to the live store.

## Configuration

Change `BASE_DOMAIN` in `config/settings.py` to target another Shopify store. Only scrape public data you are authorized to access, and respect the store's terms and request limits.
