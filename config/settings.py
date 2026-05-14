import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from utils.helpers import log

SETTINGS_DIR = Path.home() / ".dedutto"
SETTINGS_FILE = SETTINGS_DIR / "settings.enc"
KEY_FILE = SETTINGS_DIR / "settings.key"


def _load_or_create_key() -> bytes:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return key


def _get_fernet() -> Fernet:
    return Fernet(_load_or_create_key())


_defaults: Dict[str, Any] = {
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "llm_api_key": "",
    "llm_base_url": "",
    "language": "it",
    "theme": "dark",
    "db_path": str(SETTINGS_DIR / "dedutto.db"),
    "irpef_rate": 23.0,
    "regional_rate": 2.03,
    "regime": "ordinario",
    "last_sync": "",
}

_cache: Optional[Dict[str, Any]] = None


def load_settings() -> Dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    if not SETTINGS_FILE.exists():
        _cache = dict(_defaults)
        return _cache
    try:
        f = _get_fernet()
        data = f.decrypt(SETTINGS_FILE.read_bytes())
        loaded = json.loads(data.decode())
        _cache = {**_defaults, **loaded}
    except (InvalidToken, json.JSONDecodeError, Exception) as e:
        log.warning(f"Failed to load settings: {e}. Using defaults.")
        _cache = dict(_defaults)
    return _cache


def save_settings(settings: Dict[str, Any]) -> None:
    global _cache
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    _cache = {**_defaults, **settings}
    try:
        f = _get_fernet()
        data = json.dumps(_cache, ensure_ascii=False, indent=2).encode()
        SETTINGS_FILE.write_bytes(f.encrypt(data))
        SETTINGS_FILE.chmod(0o600)
    except Exception as e:
        log.error(f"Failed to save settings: {e}")


def get_setting(key: str, default: Any = None) -> Any:
    s = load_settings()
    return s.get(key, default if default is not None else _defaults.get(key))


def set_setting(key: str, value: Any) -> None:
    s = load_settings()
    s[key] = value
    save_settings(s)
