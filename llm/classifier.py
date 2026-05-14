import hashlib
import json
from datetime import datetime
from typing import Optional

from db.models import Classification, Amortization
from llm.adapter import LLMAdapter
from utils.helpers import log

SYSTEM_PROMPT = """Sei un esperto fiscale italiano specializzato in Partita IVA.
Classifica le spese aziendali secondo il TUIR e le norme IVA italiane.

Rispondi SOLO con un oggetto JSON valido, senza markdown, senza spiegazioni extra.

Schema risposta:
{
  "deductibility": "full|partial|amortizable|non_deductible",
  "deductibility_pct": 0-100,
  "amort_years": 0,
  "vat_regime": "sospensione_imposta|split_payment|reverse_charge|regime_ordinario|regime_forfettario",
  "category": "stringa categoria",
  "notes": "spiegazione breve in italiano"
}

Regole:
- full (100%): cloud hosting, domini, software, formazione professionale, cancelleria, spese direttamente produttive
- partial (50%): internet, telefono, auto, utenze miste
- amortizable: laptop/PC=2 anni, mobili=5 anni, macchinari=10 anni, veicoli=4 anni
- non_deductible: multe, acquisti personali, intrattenimento senza scopo commerciale
- regime_forfettario: se il freelance è in regime forfettario (aliquota 15% o 5%)
- split_payment: PA e enti pubblici
- reverse_charge: servizi UE B2B
"""

USER_PROMPT_TEMPLATE = """Classifica questa spesa:
Fornitore: {vendor}
Importo: €{amount}
Data: {date}
Descrizione: {description}

Restituisci solo JSON."""


def _expense_hash(vendor: str, amount: float, date: str) -> str:
    key = f"{vendor.lower().strip()}|{amount:.2f}|{date}"
    return hashlib.sha256(key.encode()).hexdigest()


def classify_expense(
    vendor: str,
    amount: float,
    date: str,
    description: str,
    adapter: LLMAdapter,
    db,
) -> Optional[Classification]:
    h = _expense_hash(vendor, amount, date)

    cached = db.get_classification_by_hash(h)
    if cached:
        log.info(f"Cache hit classificazione: {vendor}")
        return cached

    prompt = USER_PROMPT_TEMPLATE.format(
        vendor=vendor,
        amount=f"{amount:.2f}",
        date=date,
        description=description or "N/D",
    )

    raw = adapter.complete_with_retry(SYSTEM_PROMPT, prompt)
    if not raw:
        log.error(f"Classificazione LLM fallita per: {vendor}")
        return None

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                log.error(f"JSON non valido nella risposta LLM: {raw[:200]}")
                return None
        else:
            log.error(f"Nessun JSON trovato nella risposta LLM: {raw[:200]}")
            return None

    c = Classification(
        expense_hash=h,
        deductibility=data.get("deductibility", "non_deductible"),
        deductibility_pct=float(data.get("deductibility_pct", 0)),
        amort_years=int(data.get("amort_years", 0)),
        vat_regime=data.get("vat_regime", "regime_ordinario"),
        category=data.get("category", ""),
        notes=data.get("notes", ""),
        llm_response=raw,
    )

    _validate_classification(c)
    c.id = db.insert_classification(c)
    log.info(f"Classificazione salvata: {vendor} -> {c.deductibility} ({c.deductibility_pct}%)")
    return c


def _validate_classification(c: Classification) -> None:
    valid_ded = {"full", "partial", "amortizable", "non_deductible"}
    valid_vat = {"sospensione_imposta", "split_payment", "reverse_charge", "regime_ordinario", "regime_forfettario"}

    if c.deductibility not in valid_ded:
        c.deductibility = "non_deductible"
    if c.vat_regime not in valid_vat:
        c.vat_regime = "regime_ordinario"
    if c.deductibility == "full":
        c.deductibility_pct = 100.0
    elif c.deductibility == "partial" and c.deductibility_pct == 0:
        c.deductibility_pct = 50.0
    elif c.deductibility == "non_deductible":
        c.deductibility_pct = 0.0
    c.amort_years = max(0, c.amort_years)


def build_amortization_schedule(
    expense_id: int,
    amount: float,
    years: int,
    start_year: Optional[int] = None,
) -> list:
    if years <= 0 or amount <= 0:
        return []
    year = start_year or datetime.now().year
    annual = round(amount / years, 2)
    schedule = []
    remaining = amount
    for i in range(years):
        remaining = round(remaining - annual, 2)
        pct = round(((i + 1) / years) * 100, 1)
        schedule.append(
            Amortization(
                expense_id=expense_id,
                year=year + i,
                annual_amount=annual,
                remaining_value=max(0, remaining),
                pct_used=pct,
                is_deducted=False,
            )
        )
    return schedule
