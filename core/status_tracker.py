"""Status tracker for pending classifications and sync state."""
from datetime import datetime
from typing import Dict, Optional

from utils.logging import get_logger

log = get_logger(__name__)


class StatusTracker:
    """Tracks application state: pending classifications, last update, etc."""

    def __init__(self, db=None):
        self.db = db
        self._last_update: Optional[datetime] = None
        self._callbacks = []

    def register_callback(self, fn) -> None:
        """Register a function to call when status changes."""
        self._callbacks.append(fn)

    def _notify(self) -> None:
        for fn in self._callbacks:
            try:
                fn()
            except Exception as exc:
                log.warning("Status callback error: %s", exc)

    def mark_updated(self) -> None:
        self._last_update = datetime.now()
        self._notify()

    @property
    def last_update(self) -> Optional[datetime]:
        return self._last_update

    @property
    def last_update_str(self) -> str:
        if self._last_update is None:
            return "Mai"
        return self._last_update.strftime("%d/%m/%Y %H:%M")

    def get_status(self) -> Dict:
        if not self.db:
            return {
                "total_expenses": 0,
                "pending_classifications": 0,
                "last_update": self.last_update_str,
            }
        try:
            return {
                "total_expenses": self.db.count_expenses(),
                "pending_classifications": self.db.count_pending(),
                "last_update": self.last_update_str,
            }
        except Exception as exc:
            log.error("Status query failed: %s", exc)
            return {
                "total_expenses": 0,
                "pending_classifications": 0,
                "last_update": self.last_update_str,
            }

    def expense_added(self) -> None:
        self.mark_updated()

    def expense_deleted(self) -> None:
        self.mark_updated()

    def classification_done(self) -> None:
        self.mark_updated()
