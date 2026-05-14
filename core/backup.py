"""Encrypted backup export/import for Dedutto."""
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.logging import get_logger

log = get_logger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    log.warning("cryptography not installed — backups will not be encrypted")

BACKUP_MAGIC = b"DEDUTTO_BACKUP_V1\n"
ITERATIONS = 480_000


def _derive_key(password: str, salt: bytes) -> bytes:
    if not _CRYPTO_AVAILABLE:
        return b""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


class BackupManager:
    """Export and import encrypted JSON backups of all Dedutto data."""

    def __init__(self, db=None):
        self.db = db

    def export_backup(self, output_path: str, password: str) -> str:
        """Export all data as an encrypted backup file. Returns file path."""
        if not self.db:
            raise RuntimeError("Database non disponibile")

        data = self._collect_data()
        serialized = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        if _CRYPTO_AVAILABLE and password:
            salt = os.urandom(16)
            key = _derive_key(password, salt)
            fernet = Fernet(key)
            encrypted = fernet.encrypt(serialized)
            payload = BACKUP_MAGIC + salt + b"\n" + encrypted
        else:
            # No encryption: just compress
            import gzip
            payload = BACKUP_MAGIC + b"PLAIN\n" + gzip.compress(serialized)

        output = Path(output_path)
        output.write_bytes(payload)
        log.info("Backup exported to %s (%d bytes)", output, len(payload))
        return str(output)

    def import_backup(self, input_path: str, password: str) -> int:
        """Import data from an encrypted backup. Returns number of expenses restored."""
        if not self.db:
            raise RuntimeError("Database non disponibile")

        data = Path(input_path).read_bytes()

        if not data.startswith(BACKUP_MAGIC):
            raise ValueError("File non è un backup Dedutto valido")

        rest = data[len(BACKUP_MAGIC):]

        if rest.startswith(b"PLAIN\n"):
            import gzip
            serialized = gzip.decompress(rest[6:])
        else:
            if not _CRYPTO_AVAILABLE:
                raise RuntimeError("cryptography non installato — impossibile decifrare il backup")
            salt = rest[:16]
            encrypted = rest[17:]  # skip salt + \n
            key = _derive_key(password, salt)
            from cryptography.fernet import Fernet, InvalidToken
            fernet = Fernet(key)
            try:
                serialized = fernet.decrypt(encrypted)
            except InvalidToken:
                raise ValueError("Password errata o file corrotto")

        backup_data = json.loads(serialized.decode("utf-8"))
        return self._restore_data(backup_data)

    def _collect_data(self) -> dict:
        """Read all tables into a serializable dict."""
        return {
            "version": 1,
            "exported_at": datetime.utcnow().isoformat(),
            "expenses": self.db.execute_raw("SELECT * FROM expenses"),
            "amortization_schedule": self.db.execute_raw("SELECT * FROM amortization_schedule"),
            "classification_cache": self.db.execute_raw("SELECT * FROM classification_cache"),
            "settings": self.db.execute_raw("SELECT * FROM settings"),
            "tax_deadlines": self.db.execute_raw("SELECT * FROM tax_deadlines"),
        }

    def _restore_data(self, data: dict) -> int:
        """Write backup data into the current database. Returns expense count."""
        count = 0
        conn = self.db._conn

        # Clear existing data (except tax_deadlines which are seeded)
        with self.db.transaction():
            conn.execute("DELETE FROM expenses")
            conn.execute("DELETE FROM amortization_schedule")
            conn.execute("DELETE FROM classification_cache")
            conn.execute("DELETE FROM settings")

        for expense in data.get("expenses", []):
            expense.pop("id", None)
            self.db.add_expense(expense)
            count += 1

        now = datetime.utcnow().isoformat()
        for row in data.get("amortization_schedule", []):
            row.pop("id", None)
            with self.db.transaction():
                conn.execute(
                    "INSERT INTO amortization_schedule (expense_id, year, amount, remaining_value, created_at) VALUES (?,?,?,?,?)",
                    (row["expense_id"], row["year"], row["amount"], row["remaining_value"], row.get("created_at", now)),
                )

        for row in data.get("settings", []):
            row.pop("id", None)
            self.db.set_setting(row["key"], row["value"])

        log.info("Restored %d expenses from backup", count)
        return count
