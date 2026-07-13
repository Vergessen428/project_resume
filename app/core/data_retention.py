"""Deterministic, previewable retention policy for transient local content."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional


RETENTION_VERSION = "1.0"
MAX_RETENTION_DAYS = 3650
TRANSIENT_TARGETS = {"transcripts", "research_excerpts", "all_transient"}


def normalise_retention_days(value: Any) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(MAX_RETENTION_DAYS, days))


def retention_cutoff(days: Any, now: Optional[datetime] = None) -> str:
    days = normalise_retention_days(days)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (current.astimezone(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def _is_before(value: Any, cutoff: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        boundary = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) < boundary.astimezone(timezone.utc)
    except ValueError:
        # Date-only legacy records are compared lexically against the ISO date.
        return text[:10] < cutoff[:10]


def _count_interviews(records: Iterable[Dict[str, Any]], cutoff: str) -> int:
    return sum(
        1
        for record in records
        if str(record.get("transcript", "")).strip()
        and _is_before(record.get("date") or record.get("updated_at"), cutoff)
    )


def _count_research(records: Iterable[Dict[str, Any]], cutoff: str) -> int:
    return sum(
        1
        for record in records
        if (str(record.get("source_text", "")).strip() or str(record.get("comments_text", "")).strip())
        and _is_before(record.get("published_date") or record.get("updated_at"), cutoff)
    )


def preview_retention(interviews: List[Dict[str, Any]], research: List[Dict[str, Any]], days: Any, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return exactly what a retention run would clear; never mutates input."""
    normalised_days = normalise_retention_days(days)
    cutoff = retention_cutoff(normalised_days, now)
    transcript_records = _count_interviews(interviews, cutoff) if normalised_days else 0
    research_records = _count_research(research, cutoff) if normalised_days else 0
    return {
        "policy_version": RETENTION_VERSION,
        "retention_days": normalised_days,
        "cutoff": cutoff,
        "targets": ["transcripts", "research_excerpts"],
        "eligible_records": {
            "transcripts": transcript_records,
            "research_excerpts": research_records,
        },
        "total_eligible_records": transcript_records + research_records,
        "automatic": False,
        "note": "仅清理原始转写和面经正文，保留结构化复盘、来源链接和统计结果。",
    }


def apply_retention(interview_store: Any, research_store: Any, days: Any, target: str = "all_transient") -> Dict[str, Any]:
    """Apply an explicitly confirmed policy through the existing atomic stores."""
    normalised_days = normalise_retention_days(days)
    if normalised_days <= 0:
        return {"retention_days": 0, "cutoff": "", "cleared": {"transcripts": 0, "research_excerpts": 0}}
    if target not in TRANSIENT_TARGETS:
        raise ValueError("保留策略目标无效。")
    cutoff = retention_cutoff(normalised_days)
    cleared = {"transcripts": 0, "research_excerpts": 0}
    if target in {"transcripts", "all_transient"}:
        cleared["transcripts"] = interview_store.clear_transcripts(cutoff)
    if target in {"research_excerpts", "all_transient"}:
        cleared["research_excerpts"] = research_store.clear_excerpts(cutoff)
    return {"retention_days": normalised_days, "cutoff": cutoff, "cleared": cleared}
