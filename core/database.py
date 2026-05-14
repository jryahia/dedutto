"""Encrypted SQLite database layer for Dedutto.

Uses pysqlcipher3 when available, falls back to plain sqlite3 with a
warning. This keeps the app functional even without SQLCipher installed.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from utils.logging import get_logger

log = get_logger(__name__)

# Try to import sqlcipher; graceful fallback
try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    _SQLCIPHER_AVAILABLE = True
except ImportError:
    _SQLCIPHER_AVAILABLE = False
    log.warning("pysqlcipher3 not available — using plain sqlite3 (no encryption)")

DB_DIR = Path.home() / ".dedutto"
DB_PATH = DB_DIR / "dedutto.db"

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    vat_amount REAL DEFAULT 0,
    description TEXT DEFAULT '',
    category TEXT DEFAULT '',
    deductibility_type TEXT DEFAULT '',
    amortization_years INTEGER DEFAULT 0,
    remaining_value REAL DEFAULT 0,
    vat_regime TEXT DEFAULT '',
    classification_confidence REAL DEFAULT 0,
    llm_provider TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS amortization_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    amount REAL NOT NULL,
    remaining_value REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classification_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT NOT NULL,
    description TEXT NOT NULL,
    amount_bucket TEXT NOT NULL,
    category TEXT NOT NULL,
    deductibility_type TEXT NOT NULL,
    amortization_years INTEGER DEFAULT 0,
    vat_regime TEXT DEFAULT '',
    confidence REAL DEFAULT 0,
    llm_provider TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tax_deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    deadline_date TEXT NOT NULL,
    description TEXT DEFAULT '',
    year INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_cache_vendor ON classification_cache(vendor);
"""

DEFAULT_DEADLINES = [
    # 2025
    ("Liquidazione IVA trimestrale Q4 2024", "2025-02-17", "Versamento IVA 4° trimestre 2024", 2025),
    ("Certificazione Unica 2025", "2025-03-17", "Invio CU ai dipendenti e collaboratori", 2025),
    ("Contributi INPS 1° rata", "2025-05-16", "Versamento contributi INPS Gestione Separata 1ª rata", 2025),
    ("Liquidazione IVA trimestrale Q1 2025", "2025-05-16", "Versamento IVA 1° trimestre 2025", 2025),
    ("Modello Redditi PF 2025", "2025-11-30", "Presentazione dichiarazione redditi 2024", 2025),
    ("Liquidazione IVA trimestrale Q2 2025", "2025-08-20", "Versamento IVA 2° trimestre 2025", 2025),
    ("Liquidazione IVA trimestrale Q3 2025", "2025-11-17", "Versamento IVA 3° trimestre 2025", 2025),
    ("IMU 2025 1ª rata", "2025-06-16", "Prima rata IMU su immobili", 2025),
    ("IMU 2025 saldo", "2025-12-16", "Saldo IMU su immobili", 2025),
    # 2026
    ("Certificazione Unica 2026", "2026-03-17", "Invio CU ai dipendenti e collaboratori", 2026),
    ("Liquidazione IVA trimestrale Q1 2026", "2026-05-16", "Versamento IVA 1° trimestre 2026", 2026),
    ("Modello Redditi PF 2026", "2026-11-30", "Presentazione dichiarazione redditi 2025", 2026),
    ("IMU 2026 1ª rata", "2026-06-16", "Prima rata IMU su immobili", 2026),
    ("IMU 2026 saldo", "2026-12-16", "Saldo IMU su immobili", 2026),
]


class Database:
    """Thin wrapper around SQLite (or SQLCipher) for Dedutto."""

    def __init__(self, password: Optional[str] = None, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.password = password
        self._conn: Optional[Any] = None
        DB_DIR.mkdir(exist_ok=True)
        self._connect()
        self._init_schema()
        self._seed_deadlines()

    # ------------------------------------------------------------------ #
    # Connection                                                           #
    # ------------------------------------------------------------------ #

    def _connect(self) -> None:
        if _SQLCIPHER_AVAILABLE and self.password:
            self._conn = sqlcipher.connect(str(self.db_path))
            # Key must be set immediately after opening
            self._conn.execute(f"PRAGMA key='{self.password}'")
            try:
                self._conn.execute("SELECT count(*) FROM sqlite_master")
            except Exception as exc:
                raise ValueError("Password errata o database corrotto") from exc
        else:
            self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(DDL)

    def _seed_deadlines(self) -> None:
        cur = self._conn.execute("SELECT COUNT(*) FROM tax_deadlines")
        if cur.fetchone()[0] == 0:
            now = datetime.utcnow().isoformat()
            with self._conn:
                self._conn.executemany(
                    "INSERT INTO tax_deadlines (name, deadline_date, description, year) VALUES (?,?,?,?)",
                    DEFAULT_DEADLINES,
                )

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------ #
    # Expenses                                                             #
    # ------------------------------------------------------------------ #

    def add_expense(self, data: Dict[str, Any]) -> int:
        now = datetime.utcnow().isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO expenses ({cols}) VALUES ({placeholders})"
        with self.transaction():
            cur = self._conn.execute(sql, list(data.values()))
        return cur.lastrowid

    def update_expense(self, expense_id: int, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.utcnow().isoformat()
        sets = ", ".join(f"{k}=?" for k in data)
        sql = f"UPDATE expenses SET {sets} WHERE id=?"
        with self.transaction():
            self._conn.execute(sql, list(data.values()) + [expense_id])

    def delete_expense(self, expense_id: int) -> None:
        with self.transaction():
            self._conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))

    def get_expense(self, expense_id: int) -> Optional[Dict]:
        cur = self._conn.execute("SELECT * FROM expenses WHERE id=?", (expense_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_expenses(
        self,
        year: Optional[int] = None,
        vendor: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        order_by: str = "date DESC",
    ) -> List[Dict]:
        conditions = []
        params: List[Any] = []
        if year:
            conditions.append("strftime('%Y', date) = ?")
            params.append(str(year))
        if vendor:
            conditions.append("lower(vendor) LIKE ?")
            params.append(f"%{vendor.lower()}%")
        if category:
            conditions.append("category = ?")
            params.append(category)
        if search:
            conditions.append(
                "(lower(vendor) LIKE ? OR lower(description) LIKE ? OR lower(category) LIKE ?)"
            )
            term = f"%{search.lower()}%"
            params.extend([term, term, term])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM expenses {where} ORDER BY {order_by}"
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def count_expenses(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    def count_pending(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE classification_confidence = 0 OR deductibility_type = ''"
        ).fetchone()[0]

    def expense_totals(self, year: Optional[int] = None) -> Dict[str, float]:
        where = f"WHERE strftime('%Y', date) = '{year}'" if year else ""
        row = self._conn.execute(
            f"""SELECT
                COALESCE(SUM(amount), 0) as total,
                COALESCE(SUM(CASE WHEN deductibility_type='full' THEN amount
                               WHEN deductibility_type='partial' THEN amount*0.5
                               ELSE 0 END), 0) as deductible,
                COALESCE(SUM(vat_amount), 0) as vat_total
            FROM expenses {where}"""
        ).fetchone()
        return {"total": row[0], "deductible": row[1], "vat_total": row[2]}

    def monthly_totals(self, year: int) -> List[Dict]:
        rows = self._conn.execute(
            """SELECT strftime('%m', date) as month, SUM(amount) as total
               FROM expenses WHERE strftime('%Y', date)=?
               GROUP BY month ORDER BY month""",
            (str(year),),
        ).fetchall()
        return [dict(r) for r in rows]

    def category_totals(self, year: Optional[int] = None) -> List[Dict]:
        where = f"WHERE strftime('%Y', date) = '{year}'" if year else ""
        rows = self._conn.execute(
            f"""SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM expenses {where}
                GROUP BY category ORDER BY total DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Amortization                                                         #
    # ------------------------------------------------------------------ #

    def add_amortization_schedule(self, expense_id: int, schedule: List[Dict]) -> None:
        now = datetime.utcnow().isoformat()
        with self.transaction():
            self._conn.execute(
                "DELETE FROM amortization_schedule WHERE expense_id=?", (expense_id,)
            )
            for entry in schedule:
                self._conn.execute(
                    "INSERT INTO amortization_schedule (expense_id, year, amount, remaining_value, created_at) VALUES (?,?,?,?,?)",
                    (expense_id, entry["year"], entry["amount"], entry["remaining_value"], now),
                )

    def get_amortization_schedule(self, expense_id: int) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM amortization_schedule WHERE expense_id=? ORDER BY year",
            (expense_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_amortizable_expenses(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM expenses WHERE deductibility_type='amortizable' ORDER BY date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Classification cache                                                 #
    # ------------------------------------------------------------------ #

    def lookup_cache(self, vendor: str, description: str, amount: float) -> Optional[Dict]:
        bucket = _amount_bucket(amount)
        row = self._conn.execute(
            """SELECT * FROM classification_cache
               WHERE lower(vendor)=? AND lower(description)=? AND amount_bucket=?
               ORDER BY created_at DESC LIMIT 1""",
            (vendor.lower(), description.lower(), bucket),
        ).fetchone()
        return dict(row) if row else None

    def store_cache(self, vendor: str, description: str, amount: float, result: Dict, llm_provider: str) -> None:
        now = datetime.utcnow().isoformat()
        with self.transaction():
            self._conn.execute(
                """INSERT OR REPLACE INTO classification_cache
                   (vendor, description, amount_bucket, category, deductibility_type,
                    amortization_years, vat_regime, confidence, llm_provider, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    vendor.lower(),
                    description.lower(),
                    _amount_bucket(amount),
                    result.get("category", ""),
                    result.get("deductibility_type", ""),
                    result.get("amortization_years", 0),
                    result.get("vat_regime", ""),
                    result.get("confidence", 0),
                    llm_provider,
                    now,
                ),
            )

    # ------------------------------------------------------------------ #
    # Settings                                                             #
    # ------------------------------------------------------------------ #

    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return row[0]
        return default

    def set_setting(self, key: str, value: Any) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        with self.transaction():
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                (key, serialized),
            )

    def get_all_settings(self) -> Dict[str, Any]:
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        result = {}
        for row in rows:
            try:
                result[row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                result[row[0]] = row[1]
        return result

    # ------------------------------------------------------------------ #
    # Tax deadlines                                                        #
    # ------------------------------------------------------------------ #

    def get_deadlines(self, year: Optional[int] = None) -> List[Dict]:
        if year:
            rows = self._conn.execute(
                "SELECT * FROM tax_deadlines WHERE year=? ORDER BY deadline_date", (year,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM tax_deadlines ORDER BY deadline_date"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_upcoming_deadlines(self, days: int = 30) -> List[Dict]:
        today = datetime.utcnow().date().isoformat()
        rows = self._conn.execute(
            """SELECT * FROM tax_deadlines
               WHERE deadline_date >= ? AND deadline_date <= date(?, '+' || ? || ' days')
               ORDER BY deadline_date""",
            (today, today, str(days)),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Raw query (for backup / export)                                      #
    # ------------------------------------------------------------------ #

    def execute_raw(self, sql: str, params: tuple = ()) -> List[Dict]:
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def _amount_bucket(amount: float) -> str:
    """Group amounts into buckets so cache is more broadly reusable."""
    if amount < 10:
        return "<10"
    elif amount < 50:
        return "10-50"
    elif amount < 200:
        return "50-200"
    elif amount < 500:
        return "200-500"
    elif amount < 2000:
        return "500-2000"
    elif amount < 10000:
        return "2000-10000"
    else:
        return ">10000"
