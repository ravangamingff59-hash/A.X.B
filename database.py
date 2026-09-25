"""
Minimal JSON-file storage for warnings, keyed by guild -> user -> list of warnings.
Swap this out for SQLite/PostgreSQL if you need concurrency or scale.
"""
import json
import os
import threading
from datetime import datetime, timezone

_LOCK = threading.Lock()
_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "warnings.json")


def _ensure_file():
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    if not os.path.exists(_PATH):
        with open(_PATH, "w") as f:
            json.dump({}, f)


def _load():
    _ensure_file()
    with open(_PATH, "r") as f:
        return json.load(f)


def _save(data):
    with open(_PATH, "w") as f:
        json.dump(data, f, indent=2)


def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    """Adds a warning, returns the new total warning count for that user."""
    with _LOCK:
        data = _load()
        g = data.setdefault(str(guild_id), {})
        warnings = g.setdefault(str(user_id), [])
        warnings.append(
            {
                "moderator_id": moderator_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        _save(data)
        return len(warnings)


def get_warnings(guild_id: int, user_id: int) -> list:
    with _LOCK:
        data = _load()
        return data.get(str(guild_id), {}).get(str(user_id), [])


def clear_warnings(guild_id: int, user_id: int) -> None:
    with _LOCK:
        data = _load()
        g = data.setdefault(str(guild_id), {})
        g[str(user_id)] = []
        _save(data)


def remove_warning(guild_id: int, user_id: int, index: int) -> bool:
    """Removes a single warning by index. Returns True if removed."""
    with _LOCK:
        data = _load()
        warnings = data.get(str(guild_id), {}).get(str(user_id), [])
        if 0 <= index < len(warnings):
            warnings.pop(index)
            _save(data)
            return True
        return False
