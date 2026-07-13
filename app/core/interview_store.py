"""Small local data store for interview records.

Keeps the candidate's interview material in one local JSON file instead of a
database. Writes are atomic (temp file + os.replace) and guarded by a lock.
"""

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class InterviewStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
        return [self._summary(record) for record in sorted(records, key=lambda item: item["updated_at"], reverse=True)]

    def get(self, interview_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for record in self._read_all():
                if record["id"] == interview_id:
                    return copy.deepcopy(record)
        return None

    def records(self) -> List[Dict[str, Any]]:
        """Return full records for local aggregate memory, never just sidebar summaries."""
        with self._lock:
            return copy.deepcopy(self._read_all())

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = self._normalise(payload)
        record.update({"id": uuid.uuid4().hex, "created_at": now, "updated_at": now, "review": None})
        with self._lock:
            records = self._read_all()
            records.append(record)
            self._write_all(records)
        return copy.deepcopy(record)

    def update(self, interview_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record["id"] != interview_id:
                    continue
                merged = dict(record)
                merged.update(self._normalise(payload, partial=True))
                merged["updated_at"] = self._now()
                records[index] = merged
                self._write_all(records)
                return copy.deepcopy(merged)
        return None

    def save_review(self, interview_id: str, review: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record["id"] != interview_id:
                    continue
                record["review"] = review
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def set_action_done(self, interview_id: str, action_id: str, done: bool) -> Optional[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record["id"] != interview_id:
                    continue
                review = record.get("review") or {}
                actions = review.get("action_plan") or []
                found = False
                for action in actions:
                    if action.get("id") == action_id:
                        action["done"] = bool(done)
                        found = True
                if not found:
                    return None
                record["review"] = review
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def _read_all(self) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_all(self, records: List[Dict[str, Any]]) -> None:
        temporary_path = self.path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        os.replace(temporary_path, self.path)

    def _normalise(self, payload: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
        fields = {
            "company": 120,
            "role": 120,
            "round_name": 80,
            "date": 20,
            "status": 40,
            "job_description": 12000,
            "resume_context": 8000,
            "resume_id": 80,
            "resume_name": 120,
            "transcript": 32000,
            "personal_notes": 8000,
        }
        result: Dict[str, Any] = {}
        for field, limit in fields.items():
            if partial and field not in payload:
                continue
            value = str(payload.get(field, "")).strip()
            result[field] = value[:limit]
        if "jd_analysis" in payload:
            result["jd_analysis"] = payload.get("jd_analysis") if isinstance(payload.get("jd_analysis"), dict) else None
        if "research_context" in payload:
            sources = payload.get("research_context")
            result["research_context"] = [
                {key: str(item.get(key, ""))[:900] for key in ("title", "url", "platform", "summary", "search_query", "provenance_status")}
                for item in sources[:8] if isinstance(item, dict)
            ] if isinstance(sources, list) else []
        if not partial:
            result.setdefault("status", "待复盘")
            result.setdefault("personal_notes", "")
        return result

    def _summary(self, record: Dict[str, Any]) -> Dict[str, Any]:
        review = record.get("review") or {}
        actions = review.get("action_plan") or []
        return {
            "id": record["id"],
            "company": record.get("company", "未命名公司"),
            "role": record.get("role", "未命名岗位"),
            "round_name": record.get("round_name", "面试"),
            "date": record.get("date", ""),
            "status": record.get("status", "待复盘"),
            "has_review": bool(record.get("review")),
            "action_count": len(actions),
            "open_actions": len([action for action in actions if not action.get("done")]),
            "resume_name": record.get("resume_name", ""),
            "updated_at": record.get("updated_at", ""),
        }

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
