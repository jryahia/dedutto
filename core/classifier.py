"""Italian tax expense classifier using LLM with local caching."""
import json
import re
from typing import Any, Dict, Optional

from core.llm_adapter import LLMAdapter
from utils.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """Sei un esperto di fiscalità italiana per liberi professionisti con Partita IVA.
Il tuo compito è classificare le spese secondo le regole fiscali italiane.

Rispondi SOLO con un oggetto JSON valido, senza testo aggiuntivo.

Struttura JSON richiesta:
{
  "category": "<categoria>",
  "deductibility_type": "<full|partial|amortizable|none>",
  "amortization_years": <0 se non ammortizzabile, altrimenti anni>,
  "vat_regime": "<normale|sospensione|split_payment|reverse_charge|esente|forfettario>",
  "confidence": <0-100>,
  "reasoning": "<breve spiegazione in italiano>"
}

Regole di deducibilità:
- full (100%): cloud hosting, domini, licenze software, formazione professionale, assicurazioni professionali, spese bancarie, commercialista, pubblicità/marketing, cancelleria, abbonamenti professionali
- partial (50%): internet, telefono, spese auto, utenze domestiche per home office, pasti di lavoro (75%)
- amortizable: laptop/PC = 2 anni, tablet = 2 anni, mobili/arredi = 5 anni, macchinari = 10 anni, veicoli = 4 anni, ristrutturazioni = 20 anni
- none: sanzioni/multe, acquisti personali, svago senza giustificazione commerciale

Regimi IVA:
- normale: acquisti ordinari da fornitori italiani
- sospensione: acquisti PA con IVA in sospensione
- split_payment: acquisti da/per PA con split payment
- reverse_charge: servizi intracomunitari o edilizia
- esente: operazioni esenti ex art.10 DPR 633/72
- forfettario: per chi è in regime forfettario (nessuna IVA detraibile)

Categorie disponibili:
software, hosting, hardware, office, training, insurance, accounting, bank, advertising, internet, transport, utilities, food, travel, other, personal, fines"""

USER_PROMPT_TEMPLATE = """Classifica questa spesa:
Fornitore: {vendor}
Descrizione: {description}
Importo: €{amount:.2f}
IVA: €{vat:.2f}"""


# Amortization periods in years per category
AMORTIZATION_YEARS: Dict[str, int] = {
    "laptop": 2,
    "pc": 2,
    "computer": 2,
    "tablet": 2,
    "smartphone": 2,
    "server": 2,
    "hardware": 2,
    "mobili": 5,
    "furniture": 5,
    "arredi": 5,
    "scrivania": 5,
    "sedia": 5,
    "macchinari": 10,
    "machinery": 10,
    "attrezzature": 10,
    "veicolo": 4,
    "vehicle": 4,
    "auto": 4,
    "automobile": 4,
    "moto": 4,
    "ristrutturazione": 20,
    "renovation": 20,
    "immobile": 33,
}


class ExpenseClassifier:
    """Classifies expenses using LLM with SQLite-backed caching."""

    def __init__(self, llm_adapter: LLMAdapter, db=None):
        self.llm = llm_adapter
        self.db = db  # Optional Database instance for caching

    def classify(
        self,
        vendor: str,
        description: str,
        amount: float,
        vat: float = 0.0,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Classify an expense. Returns dict with category, deductibility, etc."""

        # Check cache first
        if not force_refresh and self.db:
            cached = self.db.lookup_cache(vendor, description, amount)
            if cached:
                log.info("Cache hit for vendor=%s desc=%s", vendor, description)
                return {
                    "category": cached["category"],
                    "deductibility_type": cached["deductibility_type"],
                    "amortization_years": cached["amortization_years"],
                    "vat_regime": cached["vat_regime"],
                    "confidence": cached["confidence"],
                    "reasoning": "Risultato dalla cache locale",
                    "from_cache": True,
                }

        # LLM classification
        result = self._llm_classify(vendor, description, amount, vat)

        # Store in cache
        if self.db and result:
            try:
                self.db.store_cache(vendor, description, amount, result, self.llm.provider)
            except Exception as exc:
                log.warning("Failed to store cache: %s", exc)

        result["from_cache"] = False
        return result

    def _llm_classify(
        self,
        vendor: str,
        description: str,
        amount: float,
        vat: float,
    ) -> Dict[str, Any]:
        user_msg = USER_PROMPT_TEMPLATE.format(
            vendor=vendor or "Sconosciuto",
            description=description or "Non specificata",
            amount=amount,
            vat=vat,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        try:
            raw = self.llm.complete(messages, temperature=0.05, max_tokens=512)
            return self._parse_response(raw)
        except Exception as exc:
            log.error("LLM classification failed: %s", exc)
            # Return best-effort heuristic classification
            return self._heuristic_classify(vendor, description, amount)

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON block
        json_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return self._validate_classification(data)
            except json.JSONDecodeError:
                pass

        # Try full response
        try:
            data = json.loads(raw.strip())
            return self._validate_classification(data)
        except json.JSONDecodeError:
            log.warning("Could not parse LLM response as JSON: %s", raw[:200])
            return self._heuristic_classify("", "", 0)

    def _validate_classification(self, data: Dict) -> Dict[str, Any]:
        valid_deduct = {"full", "partial", "amortizable", "none"}
        valid_vat = {"normale", "sospensione", "split_payment", "reverse_charge", "esente", "forfettario"}

        deduct = data.get("deductibility_type", "none")
        if deduct not in valid_deduct:
            deduct = "none"

        vat_regime = data.get("vat_regime", "normale")
        if vat_regime not in valid_vat:
            vat_regime = "normale"

        amort_years = int(data.get("amortization_years", 0))
        if deduct == "amortizable" and amort_years == 0:
            amort_years = 2  # default

        confidence = float(data.get("confidence", 50))
        confidence = max(0.0, min(100.0, confidence))

        return {
            "category": str(data.get("category", "other"))[:50],
            "deductibility_type": deduct,
            "amortization_years": amort_years,
            "vat_regime": vat_regime,
            "confidence": confidence,
            "reasoning": str(data.get("reasoning", ""))[:500],
        }

    def _heuristic_classify(self, vendor: str, description: str, amount: float) -> Dict[str, Any]:
        """Rule-based fallback when LLM is unavailable."""
        text = f"{vendor} {description}".lower()

        # Check amortizable items first
        for keyword, years in AMORTIZATION_YEARS.items():
            if keyword in text:
                return {
                    "category": "hardware",
                    "deductibility_type": "amortizable",
                    "amortization_years": years,
                    "vat_regime": "normale",
                    "confidence": 40.0,
                    "reasoning": f"Classificazione euristica: {keyword} rilevato",
                }

        # Fully deductible keywords
        full_deduct = {
            "software", "licenza", "license", "hosting", "cloud", "domini", "domain",
            "formazione", "corso", "training", "assicurazione", "insurance", "banca",
            "bank", "commercialista", "consulenza", "pubblicità", "advertising",
            "cancelleria", "abbonamento", "subscription",
        }
        for kw in full_deduct:
            if kw in text:
                return {
                    "category": _keyword_to_category(kw),
                    "deductibility_type": "full",
                    "amortization_years": 0,
                    "vat_regime": "normale",
                    "confidence": 45.0,
                    "reasoning": f"Classificazione euristica: {kw} rilevato",
                }

        # Partial deductible
        partial_deduct = {"internet", "telefono", "phone", "auto", "utenza", "utility"}
        for kw in partial_deduct:
            if kw in text:
                return {
                    "category": "internet" if "internet" in kw or "telefono" in kw else "transport",
                    "deductibility_type": "partial",
                    "amortization_years": 0,
                    "vat_regime": "normale",
                    "confidence": 40.0,
                    "reasoning": f"Classificazione euristica: {kw} rilevato (uso misto 50%)",
                }

        return {
            "category": "other",
            "deductibility_type": "none",
            "amortization_years": 0,
            "vat_regime": "normale",
            "confidence": 20.0,
            "reasoning": "Classificazione euristica: categoria non determinata",
        }


def _keyword_to_category(kw: str) -> str:
    mapping = {
        "software": "software", "licenza": "software", "license": "software",
        "hosting": "hosting", "cloud": "hosting", "domini": "hosting", "domain": "hosting",
        "formazione": "training", "corso": "training", "training": "training",
        "assicurazione": "insurance", "insurance": "insurance",
        "banca": "bank", "bank": "bank",
        "commercialista": "accounting", "consulenza": "accounting",
        "pubblicità": "advertising", "advertising": "advertising",
        "cancelleria": "office", "abbonamento": "software", "subscription": "software",
    }
    return mapping.get(kw, "other")
