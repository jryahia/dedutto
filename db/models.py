from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Expense:
    id: Optional[int] = None
    file_path: str = ""
    vendor: str = ""
    date: Optional[datetime] = None
    amount: float = 0.0
    vat_amount: float = 0.0
    description: str = ""
    raw_ocr_text: str = ""
    classification_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def date_str(self) -> str:
        return self.date.strftime("%d/%m/%Y") if self.date else ""

    def amount_str(self) -> str:
        return f"€ {self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class Classification:
    id: Optional[int] = None
    expense_hash: str = ""
    deductibility: str = "non_deductible"  # full, partial, amortizable, non_deductible
    deductibility_pct: float = 0.0
    amort_years: int = 0
    vat_regime: str = "regime_ordinario"
    category: str = ""
    notes: str = ""
    llm_response: str = ""
    created_at: Optional[datetime] = None

    DEDUCTIBILITY_LABELS = {
        "full": "100% Deducibile",
        "partial": "50% Uso Misto",
        "amortizable": "Ammortizzabile",
        "non_deductible": "Non Deducibile",
    }

    VAT_REGIME_LABELS = {
        "sospensione_imposta": "Sospensione d'Imposta",
        "split_payment": "Split Payment",
        "reverse_charge": "Reverse Charge",
        "regime_ordinario": "Regime Ordinario",
        "regime_forfettario": "Regime Forfettario",
    }

    def deductibility_label(self) -> str:
        return self.DEDUCTIBILITY_LABELS.get(self.deductibility, self.deductibility)

    def vat_regime_label(self) -> str:
        return self.VAT_REGIME_LABELS.get(self.vat_regime, self.vat_regime)


@dataclass
class Amortization:
    id: Optional[int] = None
    expense_id: int = 0
    year: int = 0
    annual_amount: float = 0.0
    remaining_value: float = 0.0
    pct_used: float = 0.0
    is_deducted: bool = False
    created_at: Optional[datetime] = None
