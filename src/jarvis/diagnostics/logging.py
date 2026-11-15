"""Opt-in size-limited diagnostics. Only fixed messages may be logged."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure(path: Path | None) -> logging.Logger:
    logger = logging.getLogger("jarvis")
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(logging.INFO)
    if path is not None:
        handler = RotatingFileHandler(path, maxBytes=256_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    else:
        logger.addHandler(logging.NullHandler())
    return logger
