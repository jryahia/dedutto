"""OCR pipeline using pytesseract with Italian language support."""
import io
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from utils.logging import get_logger
from utils.validators import validate_amount, validate_date

log = get_logger(__name__)

try:
    import pytesseract
    from PIL import Image
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    log.warning("pytesseract or Pillow not installed — OCR disabled")

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False
    log.warning("PyMuPDF not installed — PDF support disabled")


@dataclass
class OCRResult:
    raw_text: str = ""
    vendor: str = ""
    date: str = ""
    amount: float = 0.0
    vat_amount: float = 0.0
    description: str = ""
    confidence: float = 0.0
    page_count: int = 1
    warnings: List[str] = field(default_factory=list)


class OCRProcessor:
    """Extracts structured data from images and PDFs."""

    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    MIN_CONFIDENCE = 70.0

    def __init__(self):
        self._check_tesseract()

    def _check_tesseract(self) -> None:
        if not _TESSERACT_AVAILABLE:
            return
        try:
            pytesseract.get_tesseract_version()
        except Exception as exc:
            log.warning("Tesseract binary not found: %s", exc)

    def is_available(self) -> bool:
        if not _TESSERACT_AVAILABLE:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def process_file(self, file_path: str) -> OCRResult:
        """Main entry point: process a file and return structured result."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Tipo file non supportato: {ext}")

        if not self.is_available():
            raise RuntimeError(
                "Tesseract non trovato. Installare tesseract-ocr con supporto lingua italiana."
            )

        try:
            if ext == ".pdf":
                images = self._pdf_to_images(path)
            else:
                images = [Image.open(path)]

            texts = []
            for img in images:
                text = self._ocr_image(img)
                texts.append(text)

            full_text = "\n\n".join(texts)
            result = self._parse_text(full_text)
            result.page_count = len(images)
            return result

        except Exception as exc:
            log.error("OCR error for %s: %s", file_path, exc)
            raise

    def _pdf_to_images(self, path: Path) -> List["Image.Image"]:
        if not _PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF non installato — impossibile elaborare PDF")

        doc = fitz.open(str(path))
        images = []
        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            images.append(Image.open(io.BytesIO(img_data)))
        doc.close()
        return images

    def _ocr_image(self, image: "Image.Image") -> str:
        # Pre-process: convert to grayscale for better accuracy
        gray = image.convert("L")

        config = "--oem 3 --psm 6 -l ita+eng"
        text = pytesseract.image_to_string(gray, config=config)
        return text

    def _ocr_confidence(self, image: "Image.Image") -> float:
        try:
            gray = image.convert("L")
            data = pytesseract.image_to_data(
                gray, config="--oem 3 --psm 6 -l ita+eng",
                output_type=pytesseract.Output.DICT
            )
            confs = [c for c in data["conf"] if c != -1]
            return sum(confs) / len(confs) if confs else 0.0
        except Exception:
            return 0.0

    def _parse_text(self, text: str) -> OCRResult:
        result = OCRResult(raw_text=text)
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        result.vendor = self._extract_vendor(lines)
        result.date = self._extract_date(text)
        result.amount, result.vat_amount = self._extract_amounts(text)
        result.description = self._extract_description(lines, result.vendor)
        result.confidence = self._compute_confidence(result)

        if result.confidence < self.MIN_CONFIDENCE:
            result.warnings.append(
                f"Bassa confidenza ({result.confidence:.0f}%) — verificare i dati manualmente"
            )
        return result

    def _extract_vendor(self, lines: List[str]) -> str:
        """Heuristic: vendor is usually in the first non-empty lines."""
        skip_keywords = {
            "fattura", "ricevuta", "scontrino", "invoice", "receipt",
            "totale", "total", "iva", "vat", "data", "date", "n°", "nr",
            "numero", "codice fiscale", "partita iva", "p.iva",
        }
        for line in lines[:8]:
            lower = line.lower()
            if any(kw in lower for kw in skip_keywords):
                continue
            # Filter out lines that look like dates or amounts
            if re.search(r"\d{2}[/.\-]\d{2}[/.\-]\d{2,4}", line):
                continue
            if re.search(r"€\s*[\d.,]+", line):
                continue
            if len(line) > 5:
                return line[:80]
        return ""

    def _extract_date(self, text: str) -> str:
        # Italian date patterns
        patterns = [
            r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b",
            r"\b(\d{1,2})\s+(\w+)\s+(\d{4})\b",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                raw = m.group(0)
                parsed = validate_date(raw)
                if parsed:
                    return parsed.strftime("%Y-%m-%d")
                # Try to fix Italian month names
                italian_months = {
                    "gennaio": "01", "febbraio": "02", "marzo": "03",
                    "aprile": "04", "maggio": "05", "giugno": "06",
                    "luglio": "07", "agosto": "08", "settembre": "09",
                    "ottobre": "10", "novembre": "11", "dicembre": "12",
                }
                lower = raw.lower()
                for name, num in italian_months.items():
                    if name in lower:
                        parts = lower.split()
                        if len(parts) == 3:
                            return f"{parts[2]}-{num}-{parts[0].zfill(2)}"
        return ""

    def _extract_amounts(self, text: str) -> Tuple[float, float]:
        """Extract total amount and VAT amount."""
        amount = 0.0
        vat = 0.0

        # Total amount patterns
        total_patterns = [
            r"(?:totale|total|importo|da pagare|amount|tot\.?)\s*[:\.]?\s*(?:€\s*)?([\d.,]+)",
            r"€\s*([\d.,]+)\s*$",
            r"([\d.,]+)\s*€\s*$",
        ]
        for pat in total_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
                val = validate_amount(m.group(1))
                if val and val > amount:
                    amount = val

        # VAT patterns
        vat_patterns = [
            r"(?:iva|i\.v\.a\.|vat)\s*(?:\d+\s*%\s*)?[:\.]?\s*(?:€\s*)?([\d.,]+)",
        ]
        for pat in vat_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                val = validate_amount(m.group(1))
                if val and val < amount:
                    vat = val
                    break

        return amount, vat

    def _extract_description(self, lines: List[str], vendor: str) -> str:
        """Build description from key lines, excluding vendor and totals."""
        desc_keywords = {
            "descrizione", "description", "oggetto", "servizio", "prodotto",
            "articolo", "prestazione", "fornitura",
        }
        for line in lines:
            if line == vendor:
                continue
            lower = line.lower()
            if any(kw in lower for kw in desc_keywords):
                # Return the next non-empty line or extract after colon
                idx = lines.index(line)
                if ":" in line:
                    part = line.split(":", 1)[1].strip()
                    if part:
                        return part[:200]
                if idx + 1 < len(lines):
                    return lines[idx + 1][:200]
        # Fallback: concatenate middle lines
        mid = lines[2:5] if len(lines) > 5 else lines[1:3]
        return " | ".join(mid)[:200]

    def _compute_confidence(self, result: OCRResult) -> float:
        score = 0.0
        if result.vendor:
            score += 25
        if result.date:
            score += 30
        if result.amount > 0:
            score += 30
        if result.description:
            score += 10
        if result.vat_amount > 0:
            score += 5
        return score
