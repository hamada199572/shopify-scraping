# Shopify Collection Price Tracker

A Python scraper that retrieves product and variant data from a Shopify collection's public JSON endpoint, normalizes it, and exports timestamped CSV snapshots. The default store is Allbirds; set the collection handle to choose which collection to scrape.

## Project objectives

- Collect product and variant identifiers, titles, prices, SKUs, update times, and product URLs.
- Keep scraping, data cleaning, configuration, and logging responsibilities separate.
- Save CSV output locally and record operational messages in the console and rotating log file.

## Architecture

- `src/scraper.py` — command-line entry point; pages through the collection JSON endpoint and coordinates cleaning and export.
- `src/cleaner.py` — transforms Shopify product JSON into one flat row per variant and exports CSV files to `output/`.
- `utils/logger.py` — configures named Python loggers with console output and rotating UTF-8 logs under `logs/`.
- `config/settings.py` — holds the store base domain (`BASE_DOMAIN`).

## Requirements

- Python 3.10 or newer
- A compatible browser driver/browser installation supported by SeleniumBase
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

`src/scraper.py` uses Python's built-in `argparse` command-line parser. Run from the repository root so the project packages resolve correctly. If `--collection` is omitted, the scraper uses `mens-bestsellers`:

```bash
python -m src.scraper
```

Pass `--collection` followed by the Shopify collection handle to scrape another collection:

```bash
python -m src.scraper --collection mens-bestsellers
```

For example, to scrape the `womens-shoes` collection:

```bash
python -m src.scraper --collection womens-shoes
```

The scraper writes a timestamped CSV file to `output/` and logs to the terminal and `logs/scraper.log`. `output/`, `logs/`, and local virtual environments are excluded from Git.

## Configuration

Change `BASE_DOMAIN` in `config/settings.py` to target another Shopify store. Only scrape public data you are authorized to access, and respect the store's terms and request limits.
