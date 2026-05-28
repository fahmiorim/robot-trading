"""
Centralised logging for the trading bot.
Writes to both file and console with rotation.
"""
import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_DIR = "logs"


def ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)


def get_logger(name: str, level: int = logging.INFO,
               log_file: Optional[str] = None) -> logging.Logger:
    """Get or create a logger with console + rotating file handler."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured
    logger.setLevel(level)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(console)

    if log_file is None:
        ensure_log_dir()
        log_file = os.path.join(_LOG_DIR, f"robot_{datetime.now().strftime('%Y%m%d')}.log")

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(file_handler)
    return logger
