"""Privacy-bounded local operational events.

This is deliberately not an application transcript log. Only a small allowlist
of operational fields is written, and rotation keeps the file bounded. Model
prompts, responses, JD text, interview text and source URLs are never accepted.
"""

from datetime import datetime, timezone
import json
import os
import re
import threading
from typing import Any, Dict, Optional


_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_SAFE_FIELDS = {
    "task_id", "kind", "status", "attempt", "max_attempts", "duration_ms",
    "error_code", "route", "status_code", "provider", "model", "cache_hit",
}
_SENSITIVE = (
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[email]"),
    (re.compile(r"(?:\+?86[-\s]?)?1[3-9]\d{9}"), "[phone]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"), "Bearer [redacted]"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationalLog:
    """Append safe event records to a bounded local JSONL file."""

    def __init__(self, path: Optional[str] = None, max_bytes: int = 2 * 1024 * 1024, keep_rotated: int = 2):
        self.path = os.path.realpath(path) if path else ""
        self.max_bytes = max(4096, min(20 * 1024 * 1024, int(max_bytes)))
        self.keep_rotated = max(1, min(5, int(keep_rotated)))
        self._lock = threading.RLock()

    def emit(self, event: str, fields: Optional[Dict[str, Any]] = None) -> None:
        if not self.path:
            return
        name = str(event or "event").strip().lower()
        if not _EVENT_NAME.match(name):
            name = "invalid_event"
        record = {"timestamp": _now(), "event": name}
        for key, value in (fields or {}).items():
            if key not in _SAFE_FIELDS:
                continue
            record[key] = self._safe_value(value)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        try:
            with self._lock:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                self._rotate_if_needed(len(line.encode("utf-8")))
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(line)
        except OSError:
            return

    def list(self, limit: int = 100) -> list:
        if not self.path or not os.path.isfile(self.path):
            return []
        try:
            with self._lock, open(self.path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()[-max(1, min(500, int(limit))):]
        except (OSError, UnicodeError, ValueError):
            return []
        result = []
        for line in lines:
            try:
                value = json.loads(line)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and isinstance(value.get("event"), str):
                result.append(value)
        return result

    def summary(self) -> Dict[str, Any]:
        events = self.list(500)
        counts: Dict[str, int] = {}
        for item in events:
            name = str(item.get("event", "unknown"))
            counts[name] = counts.get(name, 0) + 1
        return {"path_configured": bool(self.path), "recent_count": len(events), "event_counts": counts}

    def _rotate_if_needed(self, incoming_bytes: int) -> None:
        try:
            current_size = os.path.getsize(self.path) if os.path.isfile(self.path) else 0
        except OSError:
            current_size = 0
        if current_size + incoming_bytes <= self.max_bytes:
            return
        for index in range(self.keep_rotated, 0, -1):
            source = self.path if index == 1 else "%s.%s" % (self.path, index - 1)
            target = "%s.%s" % (self.path, index)
            if os.path.exists(source):
                try:
                    os.replace(source, target)
                except OSError:
                    pass

    @staticmethod
    def _safe_value(value: Any) -> Any:
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (int, float)):
            return value
        text = str(value).strip()[:160]
        for pattern, replacement in _SENSITIVE:
            text = pattern.sub(replacement, text)
        return text
