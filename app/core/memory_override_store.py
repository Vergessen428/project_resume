"""Local user overrides for deterministic long-term memory labels."""

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .local_store import read_json_value


class MemoryOverrideStore:
    """Keep label edits separate from model output and interview evidence."""

    def __init__(self, path: str, events_path: Optional[str] = None) -> None:
        self.path = path
        self.events_path = events_path or os.path.join(os.path.dirname(path), "memory_override_events.json")
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def list(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            data = self._read()
        return {str(key): copy.deepcopy(value) for key, value in data.items() if isinstance(value, dict)}

    def upsert(self, gap_key: str, title: str = "", ignored: bool = False) -> Dict[str, Any]:
        gap_key = str(gap_key or "").strip()[:180]
        if not gap_key:
            raise ValueError("缺口标识不能为空。")
        with self._lock:
            data = self._read()
            existing = data.get(gap_key) if isinstance(data.get(gap_key), dict) else {}
            previous = copy.deepcopy(existing) if existing else None
            record = {
                "gap_key": gap_key,
                "title": str(title if title is not None else existing.get("title", "")).strip()[:160],
                "ignored": bool(ignored),
                "updated_at": self._now(),
            }
            self._write_with_event(data, gap_key, record, previous, "upsert")
            return copy.deepcopy(record)

    def delete(self, gap_key: str) -> bool:
        gap_key = str(gap_key or "").strip()
        with self._lock:
            data = self._read()
            if gap_key not in data:
                return False
            previous = copy.deepcopy(data[gap_key]) if isinstance(data[gap_key], dict) else None
            self._write_with_event(data, gap_key, None, previous, "delete")
            return True

    def events(self, limit: Any = 100) -> List[Dict[str, Any]]:
        """Return recent governance events without interview or transcript content."""
        try:
            bounded = max(1, min(500, int(limit)))
        except (TypeError, ValueError):
            bounded = 100
        with self._lock:
            events = self._read_events()
        return [copy.deepcopy(item) for item in reversed(events[-bounded:])]

    def replace_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        if not isinstance(data, dict) or not all(isinstance(value, dict) for value in data.values()):
            raise ValueError("记忆治理备份结构无效。")
        with self._lock:
            self._write(copy.deepcopy(data))

    def replace_events(self, events: List[Dict[str, Any]]) -> None:
        if not isinstance(events, list) or not all(isinstance(value, dict) for value in events):
            raise ValueError("记忆治理事件备份结构无效。")
        with self._lock:
            self._write_events(copy.deepcopy(events[-500:]))

    def revert_event(self, event_id: str) -> Dict[str, Any]:
        """Restore the state before one label event and append an audit event."""
        event_id = str(event_id or "").strip()[:80]
        if not event_id:
            raise ValueError("治理事件标识不能为空。")
        with self._lock:
            data = self._read()
            events = self._read_events()
            target = next((item for item in events if item.get("id") == event_id), None)
            if not target:
                raise ValueError("未找到治理事件。")
            if target.get("action") == "revert":
                raise ValueError("不能直接撤销撤销事件，请用新的标签修改覆盖。")
            gap_key = str(target.get("gap_key", "")).strip()[:180]
            if not gap_key:
                raise ValueError("治理事件缺少缺口标识。")
            previous = target.get("previous") if isinstance(target.get("previous"), dict) else None
            current = copy.deepcopy(data.get(gap_key)) if isinstance(data.get(gap_key), dict) else None
            before = copy.deepcopy(data)
            if previous is None:
                data.pop(gap_key, None)
            else:
                data[gap_key] = copy.deepcopy(previous)
            restored = previous or current or {}
            event = {
                "id": uuid.uuid4().hex[:12],
                "action": "revert",
                "gap_key": gap_key,
                "title": str(restored.get("title", ""))[:160],
                "ignored": bool(restored.get("ignored", False)),
                "previous": current,
                "reverted_event_id": event_id,
                "actor": "local_user",
                "created_at": self._now(),
            }
            try:
                self._write(data)
                events.append(event)
                self._write_events(events)
            except Exception:
                try:
                    self._write(before)
                except Exception:
                    pass
                raise
            return copy.deepcopy(event)

    def _read(self) -> Dict[str, Any]:
        return read_json_value(self.path, {}, dict, "记忆标签")

    def _write(self, data: Dict[str, Any]) -> None:
        temporary_path = self.path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temporary_path, self.path)

    def _read_events(self) -> List[Dict[str, Any]]:
        return read_json_value(self.events_path, [], list, "记忆治理事件")

    def _write_events(self, events: List[Dict[str, Any]]) -> None:
        temporary_path = self.events_path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(events[-500:], handle, ensure_ascii=False, indent=2)
        os.replace(temporary_path, self.events_path)

    def _write_with_event(
        self,
        data: Dict[str, Any],
        gap_key: str,
        current: Optional[Dict[str, Any]],
        previous: Optional[Dict[str, Any]],
        action: str,
    ) -> None:
        before = copy.deepcopy(data)
        if current is None:
            data.pop(gap_key, None)
        else:
            data[gap_key] = current
        event = {
            "id": uuid.uuid4().hex[:12],
            "action": action,
            "gap_key": gap_key,
            "title": str((current or previous or {}).get("title", ""))[:160],
            "ignored": bool((current or previous or {}).get("ignored", False)),
            "previous": previous,
            "actor": "local_user",
            "created_at": self._now(),
        }
        try:
            self._write(data)
            events = self._read_events()
            events.append(event)
            self._write_events(events)
        except Exception:
            try:
                self._write(before)
            except Exception:
                pass
            raise

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
