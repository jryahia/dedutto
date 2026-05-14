"""Amortization tracker for capital expenses."""
from datetime import datetime
from typing import Dict, List, Optional

from utils.logging import get_logger

log = get_logger(__name__)

# Italian tax amortization rates (years) per asset type
AMORTIZATION_TABLE: Dict[str, Dict] = {
    "laptop": {"years": 2, "label": "Laptop / PC / Tablet"},
    "hardware": {"years": 2, "label": "Hardware Informatico"},
    "furniture": {"years": 5, "label": "Mobili e Arredi"},
    "machinery": {"years": 10, "label": "Macchinari e Attrezzature"},
    "vehicle": {"years": 4, "label": "Veicoli"},
    "renovation": {"years": 20, "label": "Ristrutturazioni"},
    "building": {"years": 33, "label": "Fabbricati"},
    "other": {"years": 5, "label": "Altro Bene Strumentale"},
}

# Italian IRES amortization coefficients (DM 31/12/1988)
ITALIAN_RATES: Dict[str, float] = {
    "laptop": 0.50,       # 50% per anno = 2 anni
    "hardware": 0.50,
    "furniture": 0.20,    # 20% per anno = 5 anni
    "machinery": 0.10,    # 10% per anno = 10 anni
    "vehicle": 0.25,      # 25% per anno = 4 anni
    "renovation": 0.05,   # 5% per anno = 20 anni
    "building": 0.03,     # 3% per anno ≈ 33 anni
    "other": 0.20,
}


class AmortizationTracker:
    """Computes and tracks amortization schedules."""

    def __init__(self, db=None):
        self.db = db

    def compute_schedule(
        self,
        expense_id: int,
        amount: float,
        purchase_date: str,
        asset_type: str,
        custom_years: Optional[int] = None,
    ) -> List[Dict]:
        """Compute annual amortization entries.

        Returns list of {year, amount, remaining_value}.
        First year is pro-rated by remaining months.
        """
        cfg = AMORTIZATION_TABLE.get(asset_type, AMORTIZATION_TABLE["other"])
        years = custom_years or cfg["years"]
        annual_amount = amount / years

        try:
            purchase_dt = datetime.fromisoformat(purchase_date)
        except ValueError:
            purchase_dt = datetime.now()

        purchase_year = purchase_dt.year
        # Pro-rate first year: months remaining / 12
        months_remaining_first_year = 12 - purchase_dt.month + 1
        first_year_amount = annual_amount * (months_remaining_first_year / 12)

        schedule = []
        remaining = amount

        # First year
        first_amt = min(first_year_amount, remaining)
        remaining -= first_amt
        schedule.append({
            "year": purchase_year,
            "amount": round(first_amt, 2),
            "remaining_value": round(remaining, 2),
        })

        # Intermediate full years
        current_year = purchase_year + 1
        while remaining > 0.01:
            amt = min(annual_amount, remaining)
            remaining -= amt
            if remaining < 0.01:
                remaining = 0.0
            schedule.append({
                "year": current_year,
                "amount": round(amt, 2),
                "remaining_value": round(remaining, 2),
            })
            current_year += 1

        # Persist to DB
        if self.db and expense_id:
            try:
                self.db.add_amortization_schedule(expense_id, schedule)
            except Exception as exc:
                log.error("Failed to persist amortization schedule: %s", exc)

        return schedule

    def get_schedule(self, expense_id: int) -> List[Dict]:
        if not self.db:
            return []
        return self.db.get_amortization_schedule(expense_id)

    def current_year_deductible(self, expense_id: int, year: Optional[int] = None) -> float:
        """Return deductible amount for a specific year."""
        year = year or datetime.now().year
        schedule = self.get_schedule(expense_id)
        for entry in schedule:
            if entry["year"] == year:
                return entry["amount"]
        return 0.0

    def total_remaining_value(self, expense_id: int) -> float:
        """Return remaining book value as of today."""
        current_year = datetime.now().year
        schedule = self.get_schedule(expense_id)
        # Find last entry up to current year
        last_entry = None
        for entry in schedule:
            if entry["year"] <= current_year:
                last_entry = entry
        if last_entry:
            return last_entry["remaining_value"]
        return 0.0

    def get_all_amortizable(self) -> List[Dict]:
        """Return all amortizable expenses with their schedules."""
        if not self.db:
            return []
        expenses = self.db.list_amortizable_expenses()
        result = []
        for exp in expenses:
            schedule = self.get_schedule(exp["id"])
            result.append({
                "expense": exp,
                "schedule": schedule,
                "remaining": self.total_remaining_value(exp["id"]),
                "current_year_deductible": self.current_year_deductible(exp["id"]),
            })
        return result

    def missing_amortization_alerts(self) -> List[Dict]:
        """Find amortizable expenses without a schedule."""
        if not self.db:
            return []
        expenses = self.db.list_amortizable_expenses()
        alerts = []
        for exp in expenses:
            schedule = self.get_schedule(exp["id"])
            if not schedule:
                years = exp.get("amortization_years", 2) or 2
                annual = exp["amount"] / years
                alerts.append({
                    "expense": exp,
                    "suggested_annual": annual,
                    "years": years,
                    "message": (
                        f"Hai acquistato {exp.get('vendor', 'un bene')} per "
                        f"€{exp['amount']:.2f} il {exp.get('date', '?')} "
                        f"ma non hai avviato l'ammortamento — "
                        f"risparmia ~€{annual:.2f} ripartendo in {years} anni"
                    ),
                })
        return alerts

    def summary_by_year(self, year: Optional[int] = None) -> Dict:
        """Aggregate amortization deductions by year."""
        year = year or datetime.now().year
        if not self.db:
            return {"year": year, "total_deductible": 0, "assets": []}

        expenses = self.db.list_amortizable_expenses()
        total = 0.0
        assets = []
        for exp in expenses:
            schedule = self.get_schedule(exp["id"])
            for entry in schedule:
                if entry["year"] == year:
                    total += entry["amount"]
                    assets.append({
                        "vendor": exp.get("vendor", ""),
                        "description": exp.get("description", ""),
                        "annual_amount": entry["amount"],
                        "remaining_value": entry["remaining_value"],
                    })
        return {"year": year, "total_deductible": total, "assets": assets}
