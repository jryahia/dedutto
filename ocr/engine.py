import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.helpers import log, parse_italian_date, parse_amount

try:
    import pytesseract
    from PIL import Image as PILImage
    HAS_TESSERACT = True
except ImportError:
    PILImage = None  # type: ignore
    HAS_TESSERACT = False
    log.error("pytesseract or Pillow not installed")

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
    log.warning("pdf2image not installed — PDF support disabled")


TESSERACT_CONFIG = "--oem 3 --psm 6 -l ita"


class OCRResult:
    def __init__(self):
        self.vendor: str = ""
        self.date: Optional[str] = None
        self.amount: Optional[float] = None
        self.vat_amount: Optional[float] = None
        self.description: str = ""
        self.raw_text: str = ""
        self.success: bool = False
        self.error: str = ""

    def is_complete(self) -> bool:
        return bool(self.vendor and self.date and self.amount is not None)


def _images_from_file(file_path: str) -> List[Any]:
    p = Path(file_path)
    suffix = p.suffix.lower()
    images = []

    if suffix == ".pdf":
        if not HAS_PDF2IMAGE:
            raise RuntimeError(
                "pdf2image non installato. Eseguire: pip install pdf2image\n"
                "È necessario anche poppler: sudo apt install poppler-utils"
            )
        images = convert_from_path(file_path, dpi=300)
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        images = [PILImage.open(file_path)]
    else:
        raise ValueError(f"Formato file non supportato: {suffix}")

    return images


def _preprocess_image(img: Any) -> Any:
    img = img.convert("L")
    if img.width < 1000:
        ratio = 1000 / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), PILImage.LANCZOS)
    return img


def _run_ocr(img: Any) -> str:
    if not HAS_TESSERACT:
        raise RuntimeError(
            "pytesseract non installato.\n"
            "Installare tesseract: sudo apt install tesseract-ocr tesseract-ocr-ita\n"
            "Poi: pip install pytesseract"
        )
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        raise RuntimeError(
            "Tesseract OCR non trovato nel PATH.\n"
            "Installare con: sudo apt install tesseract-ocr tesseract-ocr-ita\n"
            "oppure: brew install tesseract tesseract-lang"
        )
    return pytesseract.image_to_string(img, config=TESSERACT_CONFIG)


# ── Parsing helpers ────────────────────────────────────────────────────────────

_VENDOR_PATTERNS = [
    r"(?i)(?:ditta|società|azienda|s\.r\.l|s\.r\.l\.|srl|spa|s\.p\.a|snc|sas|di\s+)\s*([A-ZÀ-Ö][^\n]{3,40})",
    r"(?i)(?:fornitore|emittente|emesso da)[:\s]+([^\n]{3,50})",
    r"(?i)^([A-ZÀ-Ö][A-ZÀ-Öa-zà-ö\s&'\.]{3,40})\s*(?:srl|spa|snc|sas)",
]

_DATE_PATTERN = r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b"

_AMOUNT_PATTERNS = [
    r"(?i)(?:totale|importo|totale\s+fattura|da\s+pagare|importo\s+totale)[:\s]*(?:€|EUR)?\s*([\d.,]+)",
    r"(?:€|EUR)\s*([\d.,]+)",
    r"(?i)(?:totale)[:\s]*([\d.,]+)",
]

_VAT_PATTERNS = [
    r"(?i)(?:iva|i\.v\.a)[:\s]*(?:€|EUR)?\s*([\d.,]+)",
    r"(?i)(?:imposta)[:\s]*(?:€|EUR)?\s*([\d.,]+)",
]

_DESCRIPTION_PATTERNS = [
    r"(?i)(?:descrizione|oggetto|causale|prestazione)[:\s]+([^\n]{5,100})",
    r"(?i)(?:per)[:\s]+([^\n]{5,80})",
]


def _extract_vendor(text: str) -> str:
    for pat in _VENDOR_PATTERNS:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            return m.group(1).strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:5]:
        if len(line) > 3 and not re.match(r"^\d", line) and not re.match(r"(?i)^(data|numero|fattura|ricevuta|scontrino)", line):
            return line[:60]
    return ""


def _extract_date(text: str) -> Optional[str]:
    matches = re.findall(_DATE_PATTERN, text)
    for m in matches:
        dt = parse_italian_date(m)
        if dt:
            return dt.strftime("%d/%m/%Y")
    return None


def _extract_amount(text: str) -> Optional[float]:
    best = None
    for pat in _AMOUNT_PATTERNS:
        m = re.search(pat, text)
        if m:
            v = parse_amount(m.group(1))
            if v and (best is None or v > best):
                best = v
    return best


def _extract_vat(text: str) -> Optional[float]:
    for pat in _VAT_PATTERNS:
        m = re.search(pat, text)
        if m:
            v = parse_amount(m.group(1))
            if v is not None:
                return v
    return None


def _extract_description(text: str) -> str:
    for pat in _DESCRIPTION_PATTERNS:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            return m.group(1).strip()[:200]
    return ""


def process_file(file_path: str) -> OCRResult:
    result = OCRResult()
    try:
        images = _images_from_file(file_path)
        if not images:
            result.error = "Nessuna immagine trovata nel file"
            return result

        all_text = ""
        for img in images[:3]:
            processed = _preprocess_image(img)
            page_text = _run_ocr(processed)
            all_text += page_text + "\n"

        result.raw_text = all_text.strip()
        result.vendor = _extract_vendor(all_text)
        result.date = _extract_date(all_text)
        result.amount = _extract_amount(all_text)
        result.vat_amount = _extract_vat(all_text)
        result.description = _extract_description(all_text)
        result.success = True
        log.info(f"OCR completato: {file_path} | vendor={result.vendor} | importo={result.amount}")

    except RuntimeError as e:
        result.error = str(e)
        log.error(f"Errore OCR (runtime): {e}")
    except Exception as e:
        result.error = f"Errore inatteso durante OCR: {e}"
        log.exception(f"Errore OCR su {file_path}")

    return result
