"""Local, provenance-first store for public interview research."""

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .local_store import read_json_value
from .research_grounding import calculate_relevance, is_allowed_public_post_url, is_allowed_public_url


VALID_STATUSES = {"candidate", "auto_approved", "needs_review", "approved", "dismissed"}
MANUAL_STATUSES = {"needs_review", "approved", "dismissed"}


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
            "approval": None,
        })
        # A newly discovered or manually entered source is never usable until
        # the assessment gate or an explicit human confirmation changes it.
        record["status"] = "candidate"
        record["citation_allowed"] = False
        record["source_role"] = "question_lead_only"
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
                if "url" in payload and not is_allowed_public_url(str(payload.get("url", "")).strip()):
                    raise ValueError("研究资料链接不在公开域名白名单内。")
                requires_reassessment = any(
                    field in payload
                    for field in {
                        "title", "url", "canonical_url", "platform", "platform_id", "company", "role",
                        "round_name", "published_date", "source_text", "comments_text", "tags",
                        "source_kind", "provenance_status", "search_query", "query_source", "fetch_status", "fetch_reason",
                    }
                )
                updated = self._normalise(payload, partial=True)
                existing.update(updated)
                if requires_reassessment and existing.get("status") in {"auto_approved", "approved"}:
                    # Editing evidence or provenance invalidates the previous
                    # decision. The caller must run AI assessment again or
                    # explicitly confirm the new excerpt after the gate.
                    existing["status"] = "candidate"
                    existing["assessment"] = None
                    existing["confidence"] = 0
                    existing["assessment_gate"] = None
                    existing["citation_allowed"] = False
                    existing["source_role"] = "question_lead_only"
                    existing["approval"] = None
                existing["updated_at"] = self._now()
                records[index] = existing
                self._write_all(records)
                return copy.deepcopy(existing)
        return None

    def delete(self, research_id: str) -> bool:
        with self._lock:
            records = self._read_all()
            kept = [record for record in records if record.get("id") != research_id]
            if len(kept) == len(records):
                return False
            self._write_all(kept)
            return True

    def replace_all(self, records: List[Dict[str, Any]]) -> None:
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise ValueError("研究备份结构无效。")
        with self._lock:
            self._write_all(copy.deepcopy(records))

    def clear_excerpts(self, before: str = "") -> int:
        changed = 0
        with self._lock:
            records = self._read_all()
            for record in records:
                marker = str(record.get("published_date") or record.get("updated_at") or "")
                if before and marker and marker >= before:
                    continue
                if not str(record.get("source_text", "")) and not str(record.get("comments_text", "")):
                    continue
                record["source_text"] = ""
                record["comments_text"] = ""
                record["excerpt_cleared"] = True
                record["excerpt_cleared_at"] = self._now()
                if record.get("status") in {"approved", "auto_approved"}:
                    record["status"] = "candidate"
                    record["confidence"] = 0
                    record["assessment_gate"] = None
                    record["citation_allowed"] = False
                    record["source_role"] = "question_lead_only"
                    record["approval"] = None
                record["updated_at"] = self._now()
                changed += 1
            if changed:
                self._write_all(records)
        return changed

    def save_assessment(self, research_id: str, assessment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record.get("id") != research_id:
                    continue
                normalized_assessment = self._normalise_assessment(assessment, str(record.get("source_text", "")))
                record["assessment"] = normalized_assessment
                recommendation = normalized_assessment["recommendation"]
                try:
                    confidence = max(0, min(100, int(normalized_assessment["confidence"])))
                except (TypeError, ValueError):
                    confidence = 0
                # The model may suggest a verdict, but deterministic gates own
                # the stored state. No short/cleared excerpt can become usable,
                # and only the explicit AI pre-review state is accepted here;
                # human confirmation uses set_status("approved").
                enough_excerpt = len(str(record.get("source_text", "")).strip()) >= 80
                allowed_post_url = is_allowed_public_post_url(str(record.get("url", "")).strip())
                allowed_recommendation = recommendation if recommendation in {"auto_approved", "needs_review", "dismissed"} else "needs_review"
                if allowed_recommendation == "auto_approved" and (confidence < 80 or not enough_excerpt or not allowed_post_url):
                    allowed_recommendation = "needs_review"
                record["status"] = allowed_recommendation
                record["confidence"] = confidence
                # AI pre-review can extract leads, but it cannot grant the
                # human citation gate. Only set_status("approved") may do so.
                record["citation_allowed"] = False
                record["source_role"] = "question_lead_only"
                record["approval"] = None
                record["assessment_gate"] = {
                    "excerpt_chars": len(str(record.get("source_text", "")).strip()),
                    "minimum_excerpt_chars": 80,
                    "allowed_post_url": allowed_post_url,
                    "confidence_threshold": 80,
                    "deterministic_status": allowed_recommendation,
                }
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def set_status(self, research_id: str, status: str) -> Optional[Dict[str, Any]]:
        # `auto_approved` is reserved for save_assessment after deterministic
        # evidence gates. The browser can only request a human decision.
        if status not in MANUAL_STATUSES:
            return None
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record.get("id") != research_id:
                    continue
                if status == "approved" and not self._has_approval_evidence(record):
                    return None
                record["status"] = status
                record["citation_allowed"] = status == "approved"
                record["source_role"] = "approved_context" if status == "approved" else "question_lead_only"
                record["approval"] = (
                    {
                        "mode": "human_confirmed",
                        "actor": "local_user",
                        "confirmed_at": self._now(),
                        "excerpt_chars": len(str(record.get("source_text", "")).strip()),
                    }
                    if status == "approved" else None
                )
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def approved_for(self, company: str, role: str, limit: int = 6) -> List[Dict[str, Any]]:
        company_key = company.strip().lower()
        role_key = role.strip().lower()
        records = self.list()
        approved = [item for item in records if self._is_usable(item)]
        matched = [
            item for item in approved
            if (company_key and company_key in str(item.get("company", "")).lower())
            or (role_key and role_key in str(item.get("role", "")).lower())
        ]
        # Generic, approved PM sources are a fallback only when there is no direct match.
        return (matched or approved)[:limit]

    def recent_candidates_for_queries(
        self,
        queries: List[str],
        platform: str = "all",
        ttl_seconds: int = 3600,
        limit: int = 3,
        now: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Reuse recent Agent candidates without turning them into approvals."""
        try:
            ttl = max(0, min(86400, int(ttl_seconds)))
        except (TypeError, ValueError):
            ttl = 3600
        if ttl <= 0 or not isinstance(queries, list):
            return []
        query_set = {str(query).strip() for query in queries if str(query).strip()}
        if not query_set:
            return []
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        cutoff = current.astimezone(timezone.utc) - timedelta(seconds=ttl)
        selected = []
        seen_urls = set()
        for record in self.list():
            if str(record.get("status", "candidate")).strip().lower() == "dismissed":
                continue
            if str(record.get("search_query", "")).strip() not in query_set:
                continue
            if platform != "all" and str(record.get("platform_id", "")).strip().lower() != str(platform).strip().lower():
                continue
            try:
                retrieved_at = datetime.fromisoformat(str(record.get("retrieved_at", "")).replace("Z", "+00:00"))
                if retrieved_at.tzinfo is None:
                    retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if retrieved_at.astimezone(timezone.utc) < cutoff:
                continue
            url = str(record.get("url", "")).strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            selected.append(record)
            if len(selected) >= max(1, min(20, int(limit))):
                break
        return selected

    def stats(self) -> Dict[str, int]:
        records = self.list()
        return {
            "total": len(records),
            "usable": len([item for item in records if self._is_usable(item)]),
            "needs_review": len([item for item in records if item.get("status") in {"needs_review", "auto_approved"}]),
        }

    @staticmethod
    def _has_approval_evidence(record: Dict[str, Any]) -> bool:
        return (
            is_allowed_public_post_url(str(record.get("url", "")).strip())
            and len(str(record.get("source_text", "")).strip()) >= 80
        )

    @classmethod
    def _is_usable(cls, record: Dict[str, Any]) -> bool:
        # Automatic pre-review is intentionally question-only. A human must
        # confirm the concrete public excerpt before it can support facts.
        return (
            record.get("status") == "approved"
            and record.get("citation_allowed", True) is not False
            and cls._has_approval_evidence(record)
        )

    @classmethod
    def is_usable_record(cls, record: Dict[str, Any]) -> bool:
        """Public read-only gate for reconciling saved interview snapshots."""
        return isinstance(record, dict) and cls._is_usable(record)

    def _normalise(self, payload: Dict[str, Any], partial: bool = False) -> Dict[str, Any]:
        fields = {
            "title": 300,
            "url": 2000,
            "canonical_url": 2000,
            "platform": 60,
            "company": 120,
            "role": 120,
            "round_name": 80,
            "topic": 300,
            "published_date": 30,
            "platform_id": 40,
            "search_query": 1000,
            "query_source": 40,
            "source_kind": 60,
            "provenance_status": 60,
            "retrieved_at": 40,
            "fetched_at": 40,
            "fetch_status": 40,
            "fetch_reason": 300,
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
        if not partial or "screening" in payload:
            raw_screening = payload.get("screening") if isinstance(payload.get("screening"), dict) else {}
            breakdown = {}
            for key in ("company_match", "role_match", "round_match", "topic_match", "interview_specificity", "recency"):
                raw_value = (raw_screening.get("relevance_breakdown") or {}).get(key)
                if raw_value is None:
                    breakdown[key] = None
                    continue
                try:
                    breakdown[key] = max(0, min(100, int(raw_value)))
                except (TypeError, ValueError):
                    breakdown[key] = 0
            result["screening"] = {
                "recommendation": str(raw_screening.get("recommendation", "needs_review"))[:30],
                "relevance": calculate_relevance(breakdown),
                "relevance_breakdown": breakdown,
                "relevance_method": str(raw_screening.get("relevance_method", "legacy_unknown"))[:40],
                "not_applicable_dimensions": [str(item)[:60] for item in raw_screening.get("not_applicable_dimensions", []) if str(item).strip()][:6],
                "match_reasons": [str(item)[:160] for item in raw_screening.get("match_reasons", []) if str(item).strip()][:5],
                "reason": str(raw_screening.get("reason", ""))[:300],
            }
        if not partial:
            status = str(payload.get("status", "candidate"))
            result["status"] = status if status in VALID_STATUSES else "candidate"
            try:
                confidence = int(payload.get("confidence", 0) or 0)
            except (TypeError, ValueError):
                confidence = 0
            result["confidence"] = max(0, min(100, confidence))
            result["citation_allowed"] = bool(payload.get("citation_allowed", False)) and result["status"] == "approved"
            result["source_role"] = "approved_context" if result["citation_allowed"] else "question_lead_only"
        return result

    def _normalise_assessment(self, assessment: Any, source_text: str = "") -> Dict[str, Any]:
        raw = assessment if isinstance(assessment, dict) else {}
        recommendation = str(raw.get("recommendation", "needs_review"))
        if recommendation not in {"auto_approved", "needs_review", "dismissed"}:
            recommendation = "needs_review"
        try:
            confidence = max(0, min(100, int(raw.get("confidence", 0))))
        except (TypeError, ValueError):
            confidence = 0

        def text_list(value: Any, item_limit: int = 300, max_items: int = 4) -> List[str]:
            if not isinstance(value, list):
                return []
            return [str(item).strip()[:item_limit] for item in value[:max_items] if str(item).strip()]

        question_leads = []
        for item in raw.get("question_leads", []) if isinstance(raw.get("question_leads"), list) else []:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()[:300]
            if not question:
                continue
            topic = str(item.get("topic", "")).strip()[:120]
            evidence = str(item.get("evidence", "")).strip()[:700]
            verified = bool(evidence and evidence in source_text)
            question_leads.append({
                "question": question,
                "topic": topic,
                "evidence": evidence if verified else "",
                "evidence_status": "verified" if verified else "unverified",
            })
            if len(question_leads) >= 4:
                break

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "summary": str(raw.get("summary", "")).strip()[:500],
            "claims": text_list(raw.get("claims")),
            "question_leads": question_leads,
            "credibility_signals": text_list(raw.get("credibility_signals")),
            "concerns": text_list(raw.get("concerns")),
            "review_reason": str(raw.get("review_reason", "")).strip()[:500],
        }

    def _read_all(self) -> List[Dict[str, Any]]:
        return read_json_value(self.path, [], list, "面经")

    def _write_all(self, records: List[Dict[str, Any]]) -> None:
        temporary_path = self.path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        os.replace(temporary_path, self.path)

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
