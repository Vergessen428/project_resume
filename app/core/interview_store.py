"""Small local data store for interview records.

Keeps the candidate's interview material in one local JSON file instead of a
database. Writes are atomic (temp file + os.replace) and guarded by a lock.
"""

import copy
import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .local_store import read_json_value
from .research_grounding import calculate_relevance


def _action_text_signature(action: Dict[str, Any]) -> str:
    """Fallback identity for reviews created before source IDs were emitted."""
    material = "|".join([
        str(action.get("action", "")).strip(),
        str(action.get("priority", "中")).strip(),
        str(action.get("next_validation", "")).strip(),
        "|".join(str(value).strip() for value in (action.get("success_criteria") or []) if str(value).strip()),
    ])
    return "action-text-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


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
                stored_review = copy.deepcopy(review) if isinstance(review, dict) else {}
                previous_review = record.get("review") if isinstance(record.get("review"), dict) else {}
                previous_actions = previous_review.get("action_plan") if isinstance(previous_review.get("action_plan"), list) else []
                previous_by_key = {}
                previous_by_signature = {}
                for previous in previous_actions:
                    if not isinstance(previous, dict):
                        continue
                    action_key = str(previous.get("action_key", "")).strip()
                    if not action_key:
                        action_key = _action_text_signature(previous)
                    previous_by_key.setdefault(action_key, []).append(previous)
                    previous_by_signature.setdefault(_action_text_signature(previous), []).append(previous)
                actions = stored_review.get("action_plan") if isinstance(stored_review.get("action_plan"), list) else []
                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    action_key = str(action.get("action_key", "")).strip()
                    if not action_key:
                        action_key = _action_text_signature(action)
                    action.setdefault("action_key", action_key)
                    action.setdefault("id", action_key)
                    if action_key and previous_by_key.get(action_key):
                        previous = previous_by_key[action_key].pop(0)
                    elif previous_by_signature.get(_action_text_signature(action)):
                        previous = previous_by_signature[_action_text_signature(action)].pop(0)
                    else:
                        previous = None
                    if previous is not None:
                        # The new review owns diagnosis text; the store owns
                        # the training lifecycle and preserves it on reruns.
                        for field in ("id", "done", "completed_at", "acceptance_status", "acceptance_note", "attempts", "training_progress"):
                            if field in previous:
                                action[field] = copy.deepcopy(previous[field])
                    action.setdefault("source_interview_id", interview_id)
                    action.setdefault("source_interview_date", str(record.get("date", ""))[:20])
                    action.setdefault("source_company", str(record.get("company", ""))[:120])
                    action.setdefault("source_round_name", str(record.get("round_name", ""))[:80])
                    action.setdefault("source_role", str(record.get("role", ""))[:120])
                    action.setdefault("action_key", action_key)
                record["review"] = stored_review
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def delete(self, interview_id: str) -> bool:
        with self._lock:
            records = self._read_all()
            kept = [record for record in records if record.get("id") != interview_id]
            if len(kept) == len(records):
                return False
            self._write_all(kept)
            return True

    def replace_all(self, records: List[Dict[str, Any]]) -> None:
        if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
            raise ValueError("面试备份结构无效。")
        with self._lock:
            self._write_all(copy.deepcopy(records))

    def clear_transcripts(self, before: str = "") -> int:
        changed = 0
        with self._lock:
            records = self._read_all()
            for record in records:
                marker = str(record.get("date") or record.get("updated_at") or "")
                if before and marker and marker >= before:
                    continue
                if not str(record.get("transcript", "")):
                    continue
                record["transcript"] = ""
                record["transcript_cleared"] = True
                record["transcript_cleared_at"] = self._now()
                review = record.get("review") if isinstance(record.get("review"), dict) else None
                if review is not None:
                    quality = review.setdefault("review_quality", {})
                    note = "原始转写已由用户清除，历史证据不应重新解释。"
                    quality["data_quality"] = (str(quality.get("data_quality", "")).strip() + " " + note).strip()[:1500]
                record["updated_at"] = self._now()
                changed += 1
            if changed:
                self._write_all(records)
        return changed

    def set_action_done(
        self,
        interview_id: str,
        action_id: str,
        done: bool,
        acceptance_status: str = "",
        acceptance_note: str = "",
    ) -> Optional[Dict[str, Any]]:
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
                        if acceptance_status == "passed":
                            attempts = action.get("attempts") if isinstance(action.get("attempts"), list) else []
                            has_post_test = any(
                                isinstance(item, dict) and item.get("phase") == "post_test"
                                for item in attempts
                            )
                            if not has_post_test:
                                raise ValueError("完成后测训练记录后，才能将行动标记为已通过。")
                        action["done"] = bool(done)
                        action["completed_at"] = self._now() if done else ""
                        if acceptance_status in {"pending", "passed", "needs_retry"}:
                            action["acceptance_status"] = acceptance_status
                        elif not done:
                            action["acceptance_status"] = "pending"
                        if acceptance_note is not None:
                            action["acceptance_note"] = str(acceptance_note).strip()[:800]
                        found = True
                if not found:
                    return None
                record["review"] = review
                record["updated_at"] = self._now()
                records[index] = record
                self._write_all(records)
                return copy.deepcopy(record)
        return None

    def add_action_attempt(
        self,
        interview_id: str,
        action_id: str,
        phase: str,
        response: str,
        score: Any = None,
        criteria_met: Any = None,
        note: str = "",
    ) -> Dict[str, Any]:
        """Append one deterministic pre-test/rewrite/post-test training step.

        The store owns phase ordering and bounds. A model may later explain the
        answer, but it cannot manufacture completion or bypass the sequence.
        """
        phase = str(phase or "").strip().lower()
        if phase not in {"pre_test", "rewrite", "post_test"}:
            raise ValueError("训练阶段必须是 pre_test、rewrite 或 post_test。")
        response = str(response or "").strip()
        if not response:
            raise ValueError("请先填写这一阶段的回答。")
        if len(response) > 4000:
            raise ValueError("训练回答不能超过 4000 字。")
        if score in (None, ""):
            bounded_score = None
        else:
            try:
                bounded_score = max(0, min(100, int(score)))
            except (TypeError, ValueError):
                raise ValueError("训练自评必须是 0 到 100 的整数。")
        if not isinstance(criteria_met, list):
            criteria_met = []
        criteria = [str(item).strip()[:240] for item in criteria_met if str(item).strip()][:4]
        note = str(note or "").strip()[:800]
        with self._lock:
            records = self._read_all()
            for index, record in enumerate(records):
                if record.get("id") != interview_id:
                    continue
                review = record.get("review") if isinstance(record.get("review"), dict) else {}
                actions = review.get("action_plan") if isinstance(review.get("action_plan"), list) else []
                for action in actions:
                    if action.get("id") != action_id:
                        continue
                    attempts = action.get("attempts") if isinstance(action.get("attempts"), list) else []
                    phases = {str(item.get("phase", "")) for item in attempts if isinstance(item, dict)}
                    if phase == "rewrite" and "pre_test" not in phases:
                        raise ValueError("请先记录前测，再提交重写。")
                    if phase == "post_test" and not {"pre_test", "rewrite"}.issubset(phases):
                        raise ValueError("请先完成前测和重写，再提交后测。")
                    attempt = {
                        "id": uuid.uuid4().hex[:10],
                        "phase": phase,
                        "response": response,
                        "self_score": bounded_score,
                        "criteria_met": criteria,
                        "note": note,
                        "created_at": self._now(),
                    }
                    attempts.append(attempt)
                    action["attempts"] = attempts[-12:]
                    action["training_progress"] = {
                        "pre_test": any(item.get("phase") == "pre_test" for item in action["attempts"] if isinstance(item, dict)),
                        "rewrite": any(item.get("phase") == "rewrite" for item in action["attempts"] if isinstance(item, dict)),
                        "post_test": any(item.get("phase") == "post_test" for item in action["attempts"] if isinstance(item, dict)),
                        "attempt_count": len(action["attempts"]),
                    }
                    record["review"] = review
                    record["updated_at"] = self._now()
                    records[index] = record
                    self._write_all(records)
                    return copy.deepcopy(record)
                return None
        return None

    def _read_all(self) -> List[Dict[str, Any]]:
        return read_json_value(self.path, [], list, "面试")

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
        if not partial or "outcome" in payload:
            outcome = str(payload.get("outcome", "")).strip().lower()
            result["outcome"] = outcome if outcome in {"passed", "failed", "pending"} else ""
        if not partial or "outcome_source" in payload or "outcome" in payload:
            # Outcome feedback is opt-in. Legacy records remain readable, but
            # a new result must carry an explicit self-report source.
            source = str(payload.get("outcome_source", "")).strip().lower()
            result["outcome_source"] = "self_reported" if source == "self_reported" and result.get("outcome", "") else ""
        if "jd_analysis" in payload:
            result["jd_analysis"] = payload.get("jd_analysis") if isinstance(payload.get("jd_analysis"), dict) else None
        if "research_context" in payload:
            sources = payload.get("research_context")
            result["research_context"] = [
                self._research_snapshot(item)
                for item in sources[:8] if isinstance(item, dict)
            ] if isinstance(sources, list) else []
        if not partial:
            result.setdefault("status", "待复盘")
            result.setdefault("personal_notes", "")
            result.setdefault("outcome", "")
            result.setdefault("outcome_source", "")
        return result

    def _research_snapshot(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Keep bounded research context without copying raw public excerpts.

        The snapshot is context for question generation and review prompts, not
        evidence. Preserve the provenance and question-lead metadata so a saved
        interview remains connected to its JD-driven research after reload.
        """
        snapshot = {
            key: str(item.get(key, ""))[:900]
            for key in (
                "title", "url", "canonical_url", "platform", "platform_id", "company", "role",
                "round_name", "topic", "summary", "search_query", "query_source", "source_kind",
                "provenance_status", "retrieved_at", "fetch_status", "status",
            )
        }
        snapshot["research_id"] = str(item.get("id", "") or item.get("research_id", ""))[:80]
        raw_screening = item.get("screening") if isinstance(item.get("screening"), dict) else {}
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
        snapshot["screening"] = {
            "recommendation": str(raw_screening.get("recommendation", "needs_review"))[:30],
            "relevance": calculate_relevance(breakdown),
            "relevance_breakdown": breakdown,
            "relevance_method": str(raw_screening.get("relevance_method", "legacy_unknown"))[:40],
            "not_applicable_dimensions": [str(item)[:60] for item in raw_screening.get("not_applicable_dimensions", []) if str(item).strip()][:6],
            "match_reasons": [str(item)[:160] for item in raw_screening.get("match_reasons", []) if str(item).strip()][:5],
            "reason": str(raw_screening.get("reason", ""))[:300],
        }

        raw_assessment = item.get("assessment") if isinstance(item.get("assessment"), dict) else {}
        leads = []
        for lead in raw_assessment.get("question_leads", []) if isinstance(raw_assessment.get("question_leads"), list) else []:
            if not isinstance(lead, dict) or not str(lead.get("question", "")).strip():
                continue
            leads.append({
                "question": str(lead.get("question", ""))[:300],
                "topic": str(lead.get("topic", ""))[:120],
                # Do not copy excerpt text into an interview context snapshot.
                "evidence_status": str(lead.get("evidence_status", "unverified"))[:30],
            })
            if len(leads) >= 4:
                break
        try:
            assessment_confidence = max(0, min(100, int(raw_assessment.get("confidence", 0) or 0)))
        except (TypeError, ValueError):
            assessment_confidence = 0
        snapshot["assessment"] = {
            "recommendation": str(raw_assessment.get("recommendation", ""))[:30],
            "confidence": assessment_confidence,
            "summary": str(raw_assessment.get("summary", ""))[:500],
            "claims": [str(value)[:300] for value in raw_assessment.get("claims", []) if str(value).strip()][:4]
            if isinstance(raw_assessment.get("claims"), list) else [],
            "question_leads": leads,
            "concerns": [str(value)[:300] for value in raw_assessment.get("concerns", []) if str(value).strip()][:5]
            if isinstance(raw_assessment.get("concerns"), list) else [],
        }
        return snapshot

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
            "outcome": record.get("outcome", ""),
            "has_review": bool(record.get("review")),
            "action_count": len(actions),
            "open_actions": len([action for action in actions if not action.get("done")]),
            "resume_name": record.get("resume_name", ""),
            "updated_at": record.get("updated_at", ""),
        }

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
