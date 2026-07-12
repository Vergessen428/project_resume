"""Deterministic, compact long-term memory for the PM interview coach."""

from collections import Counter, defaultdict
from typing import Any, Dict, List


def build_candidate_memory(interviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    reviewed = [item for item in interviews if isinstance(item.get("review"), dict)]
    skill_scores: Dict[str, List[int]] = defaultdict(list)
    gap_counts: Counter = Counter()
    open_actions: List[Dict[str, str]] = []
    timeline: List[Dict[str, str]] = []

    for interview in reviewed:
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
            if title:
                gap_counts[title] += 1
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
        })
    skill_summary.sort(key=lambda item: (item["average_score"], -item["observations"]))

    return {
        "reviewed_interviews": len(reviewed),
        "total_interviews": len(interviews),
        "recurring_gaps": [{"title": title, "occurrences": count} for title, count in gap_counts.most_common(8)],
        "skill_summary": skill_summary,
        "open_actions": open_actions[:8],
        "timeline": sorted(timeline, key=lambda item: item.get("date", "")),
    }
