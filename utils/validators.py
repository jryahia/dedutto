"""Input validation for Dedutto."""
import re
from datetime import datetime
from typing import Optional


def validate_date(date_str: str) -> Optional[datetime]:
    """Parse date string in common Italian formats."""
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def validate_amount(amount_str: str) -> Optional[float]:
    """Parse Italian-style amount string (e.g. '1.234,56' or '1234.56')."""
    if not amount_str:
        return None
    cleaned = amount_str.strip().replace("€", "").replace(" ", "")
    # Italian format: 1.234,56
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        val = float(cleaned)
        if val < 0:
            return None
        return val
    except ValueError:
        return None


def validate_vat_code(code: str) -> bool:
    """Validate Italian Partita IVA (11 digits) or Codice Fiscale (16 chars)."""
    code = code.strip().upper()
    # Partita IVA: 11 digits
    if re.fullmatch(r"\d{11}", code):
        return _check_piva_luhn(code)
    # Codice Fiscale: 16 alphanumeric
    if re.fullmatch(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", code):
        return True
    return False


def _check_piva_luhn(piva: str) -> bool:
    """Verify Partita IVA check digit."""
    if len(piva) != 11 or not piva.isdigit():
        return False
    s = 0
    for i, ch in enumerate(piva[:10]):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    check = (10 - (s % 10)) % 10
    return check == int(piva[10])


def validate_api_key(key: str) -> bool:
    """Basic non-empty check for API keys."""
    return bool(key and key.strip() and len(key.strip()) >= 8)


def sanitize_text(text: str, max_len: int = 500) -> str:
    """Strip control chars and truncate."""
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return sanitized[:max_len]
