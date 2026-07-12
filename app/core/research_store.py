"""Local, provenance-first store for public interview research."""

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


VALID_STATUSES = {"candidate", "auto_approved", "needs_review", "approved", "dismissed"}


class ResearchStore:
    """Keeps public-source excerpts separate from candidate interview records."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
        return [copy.deepcopy(item) for item in sorted(records, key=lambda item: item.get("updated_at", ""), reverse=True)]

    def get(self, research_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for record in self._read_all():
                if record.get("id") == research_id:
                    return copy.deepcopy(record)
        return None

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = self._normalise(payload)
        record.update({
            "id": uuid.uuid4().hex,
            "created_at": now,
            "updated_at": now,
            "assessment": None,
        })
        with self._lock:
            records = self._read_all()
            records.append(record)
            self._write_all(records)
        return copy.deepcopy(record)

    def update(self, research_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
            for index, existing in enumerate(records):
                if existing.get("id") != research_id:
                    continue
                updated = self._normalise(payload, partial=True)
                existing.update(updated)
                existing["updated_at"] = self._now()
                records[index] = existing
                self._write_all(records)
                return copy.deepcopy(existing)
        return None

    def save_assessment(self, research_id: str, assessment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record.get("id") != research_id:
                    continue
                record["assessment"] = copy.deepcopy(assessment)
                recommendation = str(assessment.get("recommendation", "needs_review"))
                record["status"] = recommendation if recommendation in VALID_STATUSES else "needs_review"
                record["confidence"] = max(0, min(100, int(assessment.get("confidence", 0))))
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def set_status(self, research_id: str, status: str) -> Optional[Dict[str, Any]]:
        if status not in VALID_STATUSES:
            return None
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record.get("id") != research_id:
                    continue
                record["status"] = status
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def approved_for(self, company: str, role: str, limit: int = 6) -> List[Dict[str, Any]]:
        company_key = company.strip().lower()
        role_key = role.strip().lower()
        records = self.list()
        approved = [item for item in records if item.get("status") in {"auto_approved", "approved"}]
        matched = [
            item for item in approved
            if (company_key and company_key in str(item.get("company", "")).lower())
            or (role_key and role_key in str(item.get("role", "")).lower())
        ]
        # Generic, approved PM sources are a fallback only when there is no direct match.
        return (matched or approved)[:limit]

    def stats(self) -> Dict[str, int]:
        records = self.list()
        return {
            "total": len(records),
            "usable": len([item for item in records if item.get("status") in {"auto_approved", "approved"}]),
            "needs_review": len([item for item in records if item.get("status") == "needs_review"]),
        }

    def _normalise(self, payload: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
        fields = {
            "title": 300,
            "url": 2000,
            "platform": 60,
            "company": 120,
            "role": 120,
            "round_name": 80,
            "published_date": 30,
            "source_text": 18000,
            "comments_text": 12000,
            "tags": 800,
            "notes": 2000,
        }
        result: Dict[str, Any] = {}
        for field, limit in fields.items():
            if partial and field not in payload:
                continue
            result[field] = str(payload.get(field, "")).strip()[:limit]
        if not partial:
            status = str(payload.get("status", "candidate"))
            result["status"] = status if status in VALID_STATUSES else "candidate"
            result["confidence"] = max(0, min(100, int(payload.get("confidence", 0) or 0)))
        return result

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

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
