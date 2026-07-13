"""Deterministic, compact long-term memory for the PM interview coach.

All aggregation here is plain, reproducible Python (no model calls): recurring
weaknesses are counted by a controlled tag, skill trends compare the latest
score against the mean of earlier ones, and stage gates the cold-start guidance.
"""

from collections import defaultdict
from typing import Any, Dict, List


# Trend: latest score vs. mean of earlier scores. A move of at least this many
# points (on the 1-5 scale) counts as improving / declining; otherwise stable.
_TREND_DELTA = 0.5

# Stage gates, based on how many interviews have been reviewed.
_STAGE_EMERGING_MIN = 2
_STAGE_ESTABLISHED_MIN = 5


def _skill_trend(scores: List[int]) -> str:
    """improving / stable / declining from a date-ordered score series."""
    if len(scores) < 2:
        return "insufficient_data"
    latest = scores[-1]
    earlier = scores[:-1]
    diff = latest - (sum(earlier) / len(earlier))
    if diff >= _TREND_DELTA:
        return "improving"
    if diff <= -_TREND_DELTA:
        return "declining"
    return "stable"


def _stage_for(reviewed_count: int) -> Dict[str, Any]:
    if reviewed_count < _STAGE_EMERGING_MIN:
        return {"stage": "cold_start", "interviews_to_unlock_trend": _STAGE_EMERGING_MIN - reviewed_count}
    if reviewed_count < _STAGE_ESTABLISHED_MIN:
        return {"stage": "emerging", "interviews_to_unlock_trend": 0}
    return {"stage": "established", "interviews_to_unlock_trend": 0}


def build_candidate_memory(interviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    reviewed = [item for item in interviews if isinstance(item.get("review"), dict)]
    # Sort by date ascending so "latest" and trend are deterministic. A missing
    # date is treated as earliest, so undated records never masquerade as recent.
    reviewed_sorted = sorted(reviewed, key=lambda item: str(item.get("date", "") or ""))

    skill_scores: Dict[str, List[int]] = defaultdict(list)
    gap_groups: Dict[str, Dict[str, Any]] = {}
    open_actions: List[Dict[str, str]] = []
    timeline: List[Dict[str, str]] = []

    for interview in reviewed_sorted:
        review = interview.get("review") or {}
        timeline.append({
            "id": str(interview.get("id", "")),
            "company": str(interview.get("company", "")),
            "role": str(interview.get("role", "")),
            "round_name": str(interview.get("round_name", "")),
            "date": str(interview.get("date", "")),
        })
        for gap in review.get("gaps") or []:
            title = str(gap.get("title", "")).strip()
            canonical = str(gap.get("canonical_gap_id", "")).strip()
            # Count by the controlled tag when present; fall back to the title for
            # old data (no tag) or the heterogeneous "other" bucket.
            if canonical and canonical != "other":
                key, out_canonical = canonical, canonical
            elif title:
                key, out_canonical = "title::" + title, "other"
            else:
                continue
            group = gap_groups.get(key)
            if group is None:
                gap_groups[key] = {"canonical_gap_id": out_canonical, "title": title, "occurrences": 1}
            else:
                group["occurrences"] += 1
                if title:  # keep the most recent (date-sorted) title for display
                    group["title"] = title
        for skill in review.get("skill_diagnosis") or []:
            skill_id = str(skill.get("skill_id", "")).strip()
            try:
                score = int(skill.get("score", 0))
            except (TypeError, ValueError):
                continue
            if skill_id and 1 <= score <= 5:
                skill_scores[skill_id].append(score)
        for action in review.get("action_plan") or []:
            if not action.get("done"):
                open_actions.append({
                    "action": str(action.get("action", ""))[:500],
                    "reason": str(action.get("reason", ""))[:700],
                    "priority": str(action.get("priority", "中"))[:10],
                    "from": "%s · %s" % (interview.get("company", ""), interview.get("round_name", "面试")),
                })

    skill_summary = []
    for skill_id, scores in skill_scores.items():
        skill_summary.append({
            "skill_id": skill_id,
            "average_score": round(sum(scores) / len(scores), 1),
            "observations": len(scores),
            "latest_score": scores[-1],
            "trend": _skill_trend(scores),
        })
    skill_summary.sort(key=lambda item: (item["average_score"], -item["observations"]))

    recurring_gaps = sorted(
        gap_groups.values(),
        key=lambda group: (-group["occurrences"], group["title"]),
    )[:8]

    memory = {
        "reviewed_interviews": len(reviewed),
        "total_interviews": len(interviews),
        "recurring_gaps": recurring_gaps,
        "skill_summary": skill_summary,
        "open_actions": open_actions[:8],
        "timeline": sorted(timeline, key=lambda item: item.get("date", "")),
    }
    memory.update(_stage_for(len(reviewed)))
    return memory
