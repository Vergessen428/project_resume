"""Local resume library used by the interview assistant."""

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .local_store import read_json_value


class ResumeStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
        return [self._summary(record) for record in sorted(records, key=lambda item: item["updated_at"], reverse=True)]

    def get(self, resume_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for record in self._read_all():
                if record["id"] == resume_id:
                    return copy.deepcopy(record)
        return None

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = self._normalise(payload)
        now = self._now()
        record.update({"id": uuid.uuid4().hex, "created_at": now, "updated_at": now})
        with self._lock:
            records = self._read_all()
            records.append(record)
            self._write_all(records)
        return copy.deepcopy(record)

    def update(self, resume_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        record = self._normalise(payload)
        with self._lock:
            records = self._read_all()
            for index, existing in enumerate(records):
                if existing["id"] != resume_id:
                    continue
                record.update({"id": resume_id, "created_at": existing["created_at"], "updated_at": self._now()})
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def delete(self, resume_id: str) -> bool:
        with self._lock:
            records = self._read_all()
            kept = [record for record in records if record.get("id") != resume_id]
            if len(kept) == len(records):
                return False
            self._write_all(kept)
            return True

    def replace_all(self, records: List[Dict[str, Any]]) -> None:
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise ValueError("简历备份结构无效。")
        with self._lock:
            self._write_all(copy.deepcopy(records))

    def _normalise(self, payload: Dict[str, Any]) -> Dict[str, str]:
        return {
            "name": str(payload.get("name", "")).strip()[:120],
            "target_role": str(payload.get("target_role", "")).strip()[:120],
            "content": str(payload.get("content", "")).strip()[:24000],
        }

    def _summary(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record["id"],
            "name": record.get("name", "未命名简历"),
            "target_role": record.get("target_role", ""),
            "updated_at": record.get("updated_at", ""),
        }

    def _read_all(self) -> List[Dict[str, Any]]:
        return read_json_value(self.path, [], list, "简历")

    def _write_all(self, records: List[Dict[str, Any]]) -> None:
        temporary_path = self.path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        os.replace(temporary_path, self.path)

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
