import logging
import logging.handlers
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_PATH = Path.home() / ".dedutto" / "dedutto.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_logger_configured = False


def get_logger(name: str = "dedutto") -> logging.Logger:
    global _logger_configured
    logger = logging.getLogger(name)
    if not _logger_configured:
        logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        ch.setLevel(logging.WARNING)
        logger.addHandler(fh)
        logger.addHandler(ch)
        _logger_configured = True
    return logger


log = get_logger()


def parse_italian_date(text: str) -> Optional[datetime]:
    patterns = [
        r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})",
        r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})",
        r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            g = m.groups()
            try:
                if len(g[2]) == 4 and int(g[2]) > 31:
                    return datetime(int(g[2]), int(g[1]), int(g[0]))
                elif len(g[0]) == 4:
                    return datetime(int(g[0]), int(g[1]), int(g[2]))
                else:
                    year = int(g[2])
                    if year < 100:
                        year += 2000
                    return datetime(year, int(g[1]), int(g[0]))
            except ValueError:
                continue
    return None


def format_currency(amount: float) -> str:
    return f"€ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_amount(text: str) -> Optional[float]:
    text = text.replace("€", "").replace("EUR", "").strip()
    m = re.search(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)", text)
    if not m:
        return None
    raw = m.group(1)
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)


def truncate(text: str, max_len: int = 50) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."
