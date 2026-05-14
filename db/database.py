import sqlite3
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from db.models import Expense, Classification, Amortization
from utils.helpers import log

# We use standard sqlite3 with AES encryption via BLOB for the master password
# pysqlcipher3 is optional; we fall back to plaintext sqlite3 with a warning
try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    HAS_SQLCIPHER = True
except ImportError:
    HAS_SQLCIPHER = False
    log.warning("pysqlcipher3 not available — DB will not be encrypted. Install libsqlcipher-dev + pysqlcipher3.")


class Database:
    def __init__(self, db_path: str, password: str = ""):
        self.db_path = db_path
        self.password = password
        self._conn: Optional[sqlite3.Connection] = None
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> None:
        if HAS_SQLCIPHER and self.password:
            self._conn = sqlcipher.connect(self.db_path)
            self._conn.execute(f"PRAGMA key='{self.password}'")
            self._conn.execute("PRAGMA cipher_page_size = 4096")
            self._conn.execute("PRAGMA kdf_iter = 256000")
            self._conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
        else:
            if not HAS_SQLCIPHER and self.password:
                log.warning("SQLCipher not available — storing without encryption.")
            self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self) -> None:
        assert self._conn
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT DEFAULT '',
                vendor TEXT DEFAULT '',
                date TEXT,
                amount REAL DEFAULT 0,
                vat_amount REAL DEFAULT 0,
                description TEXT DEFAULT '',
                raw_ocr_text TEXT DEFAULT '',
                classification_id INTEGER REFERENCES classifications(id),
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_hash TEXT UNIQUE NOT NULL,
                deductibility TEXT DEFAULT 'non_deductible',
                deductibility_pct REAL DEFAULT 0,
                amort_years INTEGER DEFAULT 0,
                vat_regime TEXT DEFAULT 'regime_ordinario',
                category TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                llm_response TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS amortizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
                year INTEGER NOT NULL,
                annual_amount REAL DEFAULT 0,
                remaining_value REAL DEFAULT 0,
                pct_used REAL DEFAULT 0,
                is_deducted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
            CREATE INDEX IF NOT EXISTS idx_classifications_hash ON classifications(expense_hash);
        """)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _cur(self):
        assert self._conn, "DB not connected"
        return self._conn.cursor()

    # ── Expenses ──────────────────────────────────────────────────────────────

    def insert_expense(self, e: Expense) -> int:
        cur = self._cur()
        cur.execute(
            """INSERT INTO expenses (file_path, vendor, date, amount, vat_amount,
               description, raw_ocr_text, classification_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                e.file_path,
                e.vendor,
                e.date.isoformat() if e.date else None,
                e.amount,
                e.vat_amount,
                e.description,
                e.raw_ocr_text,
                e.classification_id,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_expense(self, e: Expense) -> None:
        self._conn.execute(
            """UPDATE expenses SET vendor=?, date=?, amount=?, vat_amount=?,
               description=?, classification_id=?, updated_at=datetime('now')
               WHERE id=?""",
            (
                e.vendor,
                e.date.isoformat() if e.date else None,
                e.amount,
                e.vat_amount,
                e.description,
                e.classification_id,
                e.id,
            ),
        )
        self._conn.commit()

    def delete_expense(self, expense_id: int) -> None:
        self._conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        self._conn.commit()

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        row = self._cur().execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
        return self._row_to_expense(row) if row else None

    def get_all_expenses(self, year: Optional[int] = None) -> List[Expense]:
        if year:
            rows = self._cur().execute(
                "SELECT * FROM expenses WHERE date LIKE ? ORDER BY date DESC",
                (f"{year}%",),
            ).fetchall()
        else:
            rows = self._cur().execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()
        return [self._row_to_expense(r) for r in rows]

    def count_expenses(self) -> int:
        return self._cur().execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    def count_pending(self) -> int:
        return self._cur().execute(
            "SELECT COUNT(*) FROM expenses WHERE classification_id IS NULL"
        ).fetchone()[0]

    def _row_to_expense(self, row) -> Expense:
        d = dict(row)
        return Expense(
            id=d["id"],
            file_path=d.get("file_path", ""),
            vendor=d.get("vendor", ""),
            date=datetime.fromisoformat(d["date"]) if d.get("date") else None,
            amount=d.get("amount", 0.0),
            vat_amount=d.get("vat_amount", 0.0),
            description=d.get("description", ""),
            raw_ocr_text=d.get("raw_ocr_text", ""),
            classification_id=d.get("classification_id"),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else None,
        )

    # ── Classifications ───────────────────────────────────────────────────────

    def get_classification_by_hash(self, h: str) -> Optional[Classification]:
        row = self._cur().execute(
            "SELECT * FROM classifications WHERE expense_hash=?", (h,)
        ).fetchone()
        return self._row_to_classification(row) if row else None

    def insert_classification(self, c: Classification) -> int:
        cur = self._cur()
        cur.execute(
            """INSERT OR REPLACE INTO classifications
               (expense_hash, deductibility, deductibility_pct, amort_years,
                vat_regime, category, notes, llm_response)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                c.expense_hash,
                c.deductibility,
                c.deductibility_pct,
                c.amort_years,
                c.vat_regime,
                c.category,
                c.notes,
                c.llm_response,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_classification(self, class_id: int) -> Optional[Classification]:
        row = self._cur().execute(
            "SELECT * FROM classifications WHERE id=?", (class_id,)
        ).fetchone()
        return self._row_to_classification(row) if row else None

    def _row_to_classification(self, row) -> Classification:
        d = dict(row)
        return Classification(
            id=d["id"],
            expense_hash=d.get("expense_hash", ""),
            deductibility=d.get("deductibility", "non_deductible"),
            deductibility_pct=d.get("deductibility_pct", 0.0),
            amort_years=d.get("amort_years", 0),
            vat_regime=d.get("vat_regime", "regime_ordinario"),
            category=d.get("category", ""),
            notes=d.get("notes", ""),
            llm_response=d.get("llm_response", ""),
        )

    # ── Amortizations ─────────────────────────────────────────────────────────

    def insert_amortization_schedule(self, amorts: List[Amortization]) -> None:
        self._conn.execute(
            "DELETE FROM amortizations WHERE expense_id=?", (amorts[0].expense_id,)
        )
        for a in amorts:
            self._conn.execute(
                """INSERT INTO amortizations (expense_id, year, annual_amount,
                   remaining_value, pct_used, is_deducted)
                   VALUES (?,?,?,?,?,?)""",
                (a.expense_id, a.year, a.annual_amount, a.remaining_value, a.pct_used, int(a.is_deducted)),
            )
        self._conn.commit()

    def get_amortizations(self, expense_id: int) -> List[Amortization]:
        rows = self._cur().execute(
            "SELECT * FROM amortizations WHERE expense_id=? ORDER BY year",
            (expense_id,),
        ).fetchall()
        return [
            Amortization(
                id=r["id"],
                expense_id=r["expense_id"],
                year=r["year"],
                annual_amount=r["annual_amount"],
                remaining_value=r["remaining_value"],
                pct_used=r["pct_used"],
                is_deducted=bool(r["is_deducted"]),
            )
            for r in rows
        ]

    def get_all_amortizations(self) -> List[Amortization]:
        rows = self._cur().execute(
            "SELECT * FROM amortizations ORDER BY expense_id, year"
        ).fetchall()
        return [
            Amortization(
                id=r["id"],
                expense_id=r["expense_id"],
                year=r["year"],
                annual_amount=r["annual_amount"],
                remaining_value=r["remaining_value"],
                pct_used=r["pct_used"],
                is_deducted=bool(r["is_deducted"]),
            )
            for r in rows
        ]

    # ── Backup / Restore ──────────────────────────────────────────────────────

    def export_backup(self, dest_path: str) -> None:
        shutil.copy2(self.db_path, dest_path)

    def import_backup(self, src_path: str) -> None:
        shutil.copy2(src_path, self.db_path)
        self.close()
        self.connect()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def total_by_year(self) -> List[Tuple[int, float]]:
        rows = self._cur().execute(
            """SELECT CAST(substr(date,1,4) AS INTEGER) as yr, SUM(amount)
               FROM expenses WHERE date IS NOT NULL GROUP BY yr ORDER BY yr"""
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def total_by_category(self) -> List[Tuple[str, float]]:
        rows = self._cur().execute(
            """SELECT c.category, SUM(e.amount)
               FROM expenses e JOIN classifications c ON e.classification_id = c.id
               GROUP BY c.category ORDER BY SUM(e.amount) DESC"""
        ).fetchall()
        return [(r[0], r[1]) for r in rows]


# Global DB instance
_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    assert _db is not None, "Database not initialized"
    return _db


def init_db(db_path: str, password: str = "") -> Database:
    global _db
    _db = Database(db_path, password)
    _db.connect()
    return _db
