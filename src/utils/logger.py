"""
src/utils/logger.py
===================
Centralised logging setup.
Logs to both the console and a rotating file in /logs/.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_INITIALIZED = False


def _setup_root_logger() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler — INFO and above
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(console)

    # Rotating file handler — DEBUG and above, max 5 MB, 3 backups
    log_file = LOGS_DIR / "transcription.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    _setup_root_logger()
    return logging.getLogger(name)
