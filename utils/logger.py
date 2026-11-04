"""Application logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIRECTORY = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIRECTORY / "scraper.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a named logger writing to the terminal and a rotating UTF-8 log."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(LOG_FORMAT)
    configured_types = {
        getattr(handler, "_shopify_logger_handler", None)
        for handler in logger.handlers
    }

    if "console" not in configured_types:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler._shopify_logger_handler = "console"  # type: ignore[attr-defined]
        logger.addHandler(console_handler)

    if "file" not in configured_types:
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler._shopify_logger_handler = "file"  # type: ignore[attr-defined]
        logger.addHandler(file_handler)

    return logger
