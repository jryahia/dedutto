"""Local file logging for Dedutto."""
import logging
import os
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    log_dir = Path.home() / ".dedutto"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "dedutto.log"

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)

        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(fmt)
        ch.setFormatter(fmt)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger
