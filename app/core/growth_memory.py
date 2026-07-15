"""Deterministic, compact long-term memory for the PM interview coach.

All aggregation here is plain, reproducible Python (no model calls): recurring
weaknesses are counted by a controlled tag, skill trends compare the latest
score against the mean of earlier ones, and stage gates the cold-start guidance.
"""

from collections import defaultdict
from datetime import datetime, timezone
import re
from typing import Any, Dict, List

from .pm_skills import PM_SKILL_DIMENSIONS, derive_role_family, gap_tag_ids


# Trend: latest score vs. mean of earlier scores. A move of at least this many
# points (on the 1-5 scale) counts as improving / declining; otherwise stable.
_TREND_DELTA = 0.5
_VALIDATION_DELTA = 0.5

# Stage gates, based on how many interviews have been reviewed.
_STAGE_EMERGING_MIN = 2
_STAGE_ESTABLISHED_MIN = 5

# Outcome feedback is descriptive until enough records exist in both groups.
_OUTCOME_DESCRIPTIVE_MIN = 4
_OUTCOME_STABLE_MIN = 6
_OUTCOME_GROUP_MIN = 2


def _normalise_match_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(value or "").lower())


def _review_score(skill: Dict[str, Any]) -> float:
    for key in ("exact_score", "score"):
        try:
            value = float(skill.get(key))
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 5:
            return value
    return None


def _verified_skill_evidence(skill: Dict[str, Any]) -> str:
    evidence = str(skill.get("evidence", "")).strip()
    if evidence and not evidence.startswith("（无转写原文"):
        return evidence[:500]
    for dimension in skill.get("dimensions") if isinstance(skill.get("dimensions"), list) else []:
        if not isinstance(dimension, dict):
            continue
        status = str(dimension.get("status", "")).strip()
        evidence = str(dimension.get("evidence", "")).strip()
        if status in {"observed", "contradicted"} and evidence and not evidence.startswith("（无转写原文"):
            return evidence[:500]
    return ""


def _review_gap_ids(review: Dict[str, Any]) -> set:
    ids = set()
    for gap in review.get("gaps") if isinstance(review.get("gaps"), list) else []:
        if isinstance(gap, dict):
            value = str(gap.get("canonical_gap_id", "") or gap.get("gap_id", "")).strip()
            if value:
                ids.add(value)
    for skill in review.get("skill_diagnosis") if isinstance(review.get("skill_diagnosis"), list) else []:
        if not isinstance(skill, dict):
            continue
        for gap in skill.get("gaps") if isinstance(skill.get("gaps"), list) else []:
            if isinstance(gap, dict) and str(gap.get("gap_id", "")).strip():
                ids.add(str(gap["gap_id"]).strip())
    return ids


def _compatible_interview(source: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
    source_profile = source.get("jd_profile") if isinstance(source.get("jd_profile"), dict) else {}
    candidate_profile = candidate.get("jd_profile") if isinstance(candidate.get("jd_profile"), dict) else {}
    source_family = str(source_profile.get("role_family", "") or derive_role_family(source.get("role", ""), source.get("jd_analysis"))).strip()
    candidate_family = str(candidate_profile.get("role_family", "") or derive_role_family(candidate.get("role", ""), candidate.get("jd_analysis"))).strip()
    if not source_family or not candidate_family or source_family != candidate_family:
        return False
    return (
        _normalise_match_text(source.get("company"))
        and _normalise_match_text(source.get("company")) == _normalise_match_text(candidate.get("company"))
    ) or (
        _normalise_match_text(source.get("role"))
        and _normalise_match_text(source.get("role")) == _normalise_match_text(candidate.get("role"))
    )


def compute_validations(records: List[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
    """Compute action validation without mutating records or trusting model fields."""
    reviewed = [item for item in records if isinstance(item, dict) and isinstance(item.get("review"), dict)]
    result = {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for source in reviewed:
        source_review = source.get("review") or {}
        source_date = str(source.get("date", "")).strip()
        for action in source_review.get("action_plan") if isinstance(source_review.get("action_plan"), list) else []:
            if not isinstance(action, dict):
                continue
            skill_ids = [str(value).strip() for value in action.get("source_skill_ids", []) if str(value).strip() in PM_SKILL_DIMENSIONS]
            gap_ids = {str(value).strip() for value in action.get("source_gap_ids", []) if str(value).strip()}
            if not skill_ids:
                inferred = [value.split("__", 1)[0] for value in gap_ids if value.split("__", 1)[0] in PM_SKILL_DIMENSIONS]
                skill_ids = list(dict.fromkeys(inferred))
            key = (str(source.get("id", "")), str(action.get("id", "")))
            base = {"status": "pending", "interview_id": "", "source_skill_id": skill_ids[0] if skill_ids else "", "delta": None, "evidence": "", "match_reason": "", "computed_at": now}
            if not skill_ids or not source_date:
                base["match_reason"] = "缺少稳定能力来源或面试日期，暂不自动验证"
                result[key] = base
                continue
            later = sorted(
                [
                    candidate for candidate in reviewed
                    if str(candidate.get("date", "")).strip() > source_date
                    and _compatible_interview(source, candidate)
                ],
                key=lambda item: (str(item.get("date", "")), str(item.get("updated_at", ""))),
            )
            if not later:
                base["match_reason"] = "尚无同岗位族且公司或岗位相同的后续复盘"
                result[key] = base
                continue
            candidate = later[0]
            candidate_review = candidate.get("review") or {}
            target_skill = next((skill for skill in candidate_review.get("skill_diagnosis", []) if isinstance(skill, dict) and skill.get("skill_id") == skill_ids[0]), None)
            base["interview_id"] = str(candidate.get("id", ""))
            base["match_reason"] = "同岗位族，且公司或归一化岗位名称一致"
            if not isinstance(target_skill, dict):
                base["match_reason"] = "自动找到后续面试，但验证场没有该能力的诊断记录"
                result[key] = base
                continue
            evidence = _verified_skill_evidence(target_skill)
            if not evidence:
                base["match_reason"] = "验证场没有可核对的该能力原文证据"
                result[key] = base
                continue
            base["evidence"] = evidence
            source_skill = next((skill for skill in source_review.get("skill_diagnosis", []) if isinstance(skill, dict) and skill.get("skill_id") == skill_ids[0]), {})
            source_score = _review_score(source_skill)
            candidate_score = _review_score(target_skill)
            if source_score is not None and candidate_score is not None:
                base["delta"] = round(candidate_score - source_score, 1)
            persisted_gaps = _review_gap_ids(candidate_review)
            gap_persists = bool(gap_ids & persisted_gaps)
            if not gap_persists and base["delta"] is not None and base["delta"] >= _VALIDATION_DELTA:
                base["status"] = "supported"
                base["match_reason"] = "验证场实际覆盖能力，目标缺口未重复且 exact_score 提升至少 0.5"
            else:
                base["status"] = "partially"
                base["match_reason"] = "验证场实际覆盖能力，但缺口仍在或分数提升不足 0.5"
            result[key] = base
    return result


def read_related_interviews(records: List[Dict[str, Any]], skill_id: str = "", gap_id: str = "", limit: int = 3) -> List[Dict[str, Any]]:
    """Return bounded historical evidence fragments, never raw interview text."""
    limit = max(1, min(3, int(limit or 3)))
    skill_id = str(skill_id or "").strip()
    gap_id = str(gap_id or "").strip()
    rows = []
    for interview in sorted(
        [item for item in records if isinstance(item, dict) and isinstance(item.get("review"), dict)],
        key=lambda item: str(item.get("date", "")),
        reverse=True,
    ):
        review = interview.get("review") or {}
        matched = []
        for skill in review.get("skill_diagnosis") if isinstance(review.get("skill_diagnosis"), list) else []:
            if skill_id and isinstance(skill, dict) and skill.get("skill_id") == skill_id:
                evidence = _verified_skill_evidence(skill)
                if evidence:
                    matched.append({"gap_title": "", "evidence": evidence})
        for gap in review.get("gaps") if isinstance(review.get("gaps"), list) else []:
            if not isinstance(gap, dict):
                continue
            candidate_gap = str(gap.get("canonical_gap_id", "") or gap.get("gap_id", "")).strip()
            if gap_id and candidate_gap != gap_id:
                continue
            evidence = str(gap.get("evidence", "")).strip()
            if evidence and not evidence.startswith("（无转写原文"):
                matched.append({"gap_title": str(gap.get("title", ""))[:180], "evidence": evidence[:500]})
        for match in matched:
            rows.append({
                "company": str(interview.get("company", ""))[:120],
                "role": str(interview.get("role", ""))[:120],
                "round_name": str(interview.get("round_name", ""))[:80],
                "date": str(interview.get("date", ""))[:20],
                "gap_title": match["gap_title"],
                "skill_id": skill_id,
                "evidence": match["evidence"],
            })
            if len(rows) >= limit:
                return rows
    return rows


def _skill_trend(scores: List[float]) -> str:
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


def _scoring_identity(review: Dict[str, Any]):
    scored_by = review.get("scored_by") if isinstance(review.get("scored_by"), dict) else {}
    provider = str(scored_by.get("provider", "")).strip() or "legacy_unknown"
    model = str(scored_by.get("model", "")).strip() or "legacy_unknown"
    prompt_version = str(scored_by.get("prompt_version", "")).strip() or "legacy_unknown"
    rubric_version = str(scored_by.get("rubric_version", "")).strip() or "legacy_unknown"
    complete = "legacy_unknown" not in {provider, model, prompt_version, rubric_version}
    return (provider, model, prompt_version, rubric_version), complete


def _outcome_signal(reviewed: List[Dict[str, Any]], comparable: str) -> Dict[str, Any]:
    groups = {"passed": [], "failed": []}
    for interview in reviewed:
        outcome = str(interview.get("outcome", "")).strip().lower()
        if outcome not in groups:
            continue
        # Legacy records without an explicit source remain readable, but must
        # not enter outcome feedback: only a declared self-report is eligible.
        outcome_source = str(interview.get("outcome_source", "")).strip().lower()
        if outcome_source != "self_reported":
            continue
        review = interview.get("review") or {}
        summary = review.get("score_summary") or {}
        try:
            score = float(summary.get("coach_score"))
        except (TypeError, ValueError):
            score = None
        # A zero coach score means that no scoreable skill was observed. Do not
        # turn an evidence-empty review into a meaningful outcome datapoint.
        if score is None or score <= 0:
            scores = []
            for skill in review.get("skill_diagnosis") or []:
                try:
                    skill_score = float(skill.get("exact_score"))
                except (TypeError, ValueError):
                    try:
                        skill_score = float(skill.get("score"))
                    except (TypeError, ValueError):
                        continue
                if 1 <= skill_score <= 5:
                    scores.append(skill_score)
            if not scores:
                continue
            score = sum(scores) / len(scores) * 20
        if 0 <= score <= 100:
            groups[outcome].append(score)

    total = len(groups["passed"]) + len(groups["failed"])
    result = {
        "status": "insufficient_data",
        "sample_count": total,
        "minimum_descriptive_sample": _OUTCOME_DESCRIPTIVE_MIN,
        "minimum_stable_sample": _OUTCOME_STABLE_MIN,
        "group_minimum": _OUTCOME_GROUP_MIN,
        "passed": {"count": len(groups["passed"]), "average_coach_score": None},
        "failed": {"count": len(groups["failed"]), "average_coach_score": None},
        "direction": "unknown",
        "interpretation": "至少需要 4 场有明确结果的面试，才展示描述性反馈；这不是录用预测。",
        "comparability": comparable,
    }
    for name, scores in groups.items():
        if scores:
            result[name]["average_coach_score"] = round(sum(scores) / len(scores), 1)
    if total < _OUTCOME_DESCRIPTIVE_MIN:
        return result
    passed_average = result["passed"]["average_coach_score"]
    failed_average = result["failed"]["average_coach_score"]
    if passed_average is not None and failed_average is not None:
        delta = passed_average - failed_average
        result["direction"] = "passed_higher" if delta >= 5 else "failed_higher" if delta <= -5 else "no_clear_difference"
    result["status"] = "descriptive"
    result["interpretation"] = "这是带样本数的描述性分组观察，不表示分数导致了面试结果。"
    if total >= _OUTCOME_STABLE_MIN and all(len(groups[name]) >= _OUTCOME_GROUP_MIN for name in groups):
        result["status"] = "ready" if comparable == "comparable" else "mixed_scoring"
        if comparable != "comparable":
            result["interpretation"] = "样本达到门槛，但评分模型或版本不完全一致，只能谨慎参考。"
    return result


def build_candidate_memory(interviews: List[Dict[str, Any]], gap_overrides: Dict[str, Dict[str, Any]] = None) -> Dict[str, Any]:
    gap_overrides = gap_overrides if isinstance(gap_overrides, dict) else {}
    reviewed = [item for item in interviews if isinstance(item.get("review"), dict)]
    # Sort by date ascending so "latest" and trend are deterministic. A missing
    # date is treated as earliest, so undated records never masquerade as recent.
    reviewed_sorted = sorted(reviewed, key=lambda item: str(item.get("date", "") or ""))

    skill_scores: Dict[str, List[float]] = defaultdict(list)
    skill_sources: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    gap_groups: Dict[str, Dict[str, Any]] = {}
    open_actions: List[Dict[str, str]] = []
    validation_rows: List[Dict[str, Any]] = []
    timeline: List[Dict[str, str]] = []
    scoring_identities = set()
    has_unknown_scoring = False

    for interview in reviewed_sorted:
        review = interview.get("review") or {}
        timeline.append({
            "id": str(interview.get("id", "")),
            "company": str(interview.get("company", "")),
            "role": str(interview.get("role", "")),
            "round_name": str(interview.get("round_name", "")),
            "date": str(interview.get("date", "")),
            "outcome": str(interview.get("outcome", "")),
            "updated_at": str(interview.get("updated_at", "")),
            "review_schema_version": str(review.get("schema_version", "legacy_unknown")),
        })
        identity, complete = _scoring_identity(review)
        scoring_identities.add(identity)
        has_unknown_scoring = has_unknown_scoring or not complete
        for gap in review.get("gaps") or []:
            title = str(gap.get("title", "")).strip()
            raw_canonical = str(gap.get("canonical_gap_id", "")).strip()
            canonical = raw_canonical if raw_canonical in gap_tag_ids() else ""
            # Count by the controlled tag when present; fall back to the title for
            # old data (no tag) or the heterogeneous "other" bucket.
            if canonical and canonical != "other":
                key, out_canonical = canonical, canonical
            elif title:
                key, out_canonical = "title::" + title, "other"
            else:
                continue
            override = gap_overrides.get(key) if isinstance(gap_overrides.get(key), dict) else {}
            if override.get("ignored") is True:
                continue
            display_title = str(override.get("title", "")).strip()[:160] or title
            group = gap_groups.get(key)
            source = {
                "interview_id": str(interview.get("id", "")),
                "company": str(interview.get("company", "")),
                "role": str(interview.get("role", "")),
                "round_name": str(interview.get("round_name", "")),
                "date": str(interview.get("date", "")),
                "evidence": str(gap.get("evidence", ""))[:500],
            }
            if group is None:
                gap_groups[key] = {"gap_key": key, "canonical_gap_id": out_canonical, "title": display_title, "occurrences": 1, "sources": [source]}
            else:
                group["occurrences"] += 1
                if display_title:  # keep the most recent (date-sorted) title for display
                    group["title"] = display_title
                if source not in group["sources"]:
                    group["sources"].append(source)
        for skill in review.get("skill_diagnosis") or []:
            skill_id = str(skill.get("skill_id", "")).strip()
            if skill_id not in PM_SKILL_DIMENSIONS:
                continue
            try:
                exact_score = float(skill.get("exact_score"))
            except (TypeError, ValueError):
                exact_score = None
            if exact_score is None:
                try:
                    exact_score = float(skill.get("score"))
                except (TypeError, ValueError):
                    exact_score = None
            if skill_id and exact_score is not None and 1 <= exact_score <= 5:
                skill_scores[skill_id].append(exact_score)
                skill_sources[skill_id].append({
                    "interview_id": str(interview.get("id", "")),
                    "company": str(interview.get("company", "")),
                    "role": str(interview.get("role", "")),
                    "round_name": str(interview.get("round_name", "")),
                    "date": str(interview.get("date", "")),
                    "score": int(round(exact_score)) if exact_score.is_integer() else round(exact_score, 1),
                    "exact_score": round(exact_score, 1),
                    "evidence": str(skill.get("evidence", ""))[:500],
                })
        for action in review.get("action_plan") or []:
            validation = action.get("validation") if isinstance(action.get("validation"), dict) else {"status": "pending"}
            validation_status = str(validation.get("status", "pending")).strip().lower()
            if validation_status not in {"supported", "partially", "pending"}:
                validation_status = "partially" if validation_status == "inconclusive" else "pending"
            validation_rows.append({
                "action_id": str(action.get("id", ""))[:100],
                "source_interview_id": str(action.get("source_interview_id", interview.get("id", "")))[:80],
                "source_date": str(action.get("source_interview_date", interview.get("date", "")))[:20],
                "action": str(action.get("action", ""))[:500],
                "status": validation_status,
                "interview_id": str(validation.get("interview_id", ""))[:80],
                "evidence": str(validation.get("evidence", ""))[:500],
                "match_reason": str(validation.get("match_reason", ""))[:240],
                "delta": validation.get("delta") if isinstance(validation.get("delta"), (int, float)) else None,
                "computed_at": str(validation.get("computed_at", ""))[:40],
            })
            if not action.get("done"):
                criteria = action.get("success_criteria") if isinstance(action.get("success_criteria"), list) else []
                open_actions.append({
                    "action": str(action.get("action", ""))[:500],
                    "reason": str(action.get("reason", ""))[:700],
                    "priority": str(action.get("priority", "中"))[:10],
                    "success_criteria": [str(value)[:300] for value in criteria if str(value).strip()][:4],
                    "next_validation": str(action.get("next_validation", ""))[:500],
                    "acceptance_status": str(action.get("acceptance_status", "pending"))[:20],
                    "acceptance_note": str(action.get("acceptance_note", ""))[:800],
                    "source_interview_id": str(action.get("source_interview_id", interview.get("id", "")))[:80],
                    "source_date": str(action.get("source_interview_date", interview.get("date", "")))[:20],
                    "from": "%s · %s" % (interview.get("company", ""), interview.get("round_name", "面试")),
                    "validation": validation_rows[-1],
                    "is_primary": bool(action.get("is_primary")),
                })

    skill_summary = []
    for skill_id, scores in skill_scores.items():
        skill_summary.append({
            "skill_id": skill_id,
            "average_score": round(sum(scores) / len(scores), 1),
            "observations": len(scores),
            "latest_score": scores[-1],
            "trend": _skill_trend(scores),
            "trend_comparable": False,
            "sources": skill_sources[skill_id][-8:],
        })
    skill_summary.sort(key=lambda item: (item["average_score"], -item["observations"]))

    recurring_gaps = sorted(
        gap_groups.values(),
        key=lambda group: (-group["occurrences"], group["title"]),
    )[:8]

    validation_summary = {"supported": 0, "partially": 0, "pending": 0}
    for row in validation_rows:
        validation_summary[row["status"]] = validation_summary.get(row["status"], 0) + 1
    recent_validations = sorted(
        validation_rows,
        key=lambda item: (str(item.get("computed_at", "")), str(item.get("source_date", ""))),
        reverse=True,
    )[:6]

    if not scoring_identities:
        comparability = "no_data"
    elif has_unknown_scoring:
        comparability = "legacy_unknown"
    elif len(scoring_identities) > 1:
        comparability = "mixed_model"
    else:
        comparability = "comparable"
    for item in skill_summary:
        item["trend_comparable"] = comparability == "comparable"

    memory = {
        "memory_version": "1.4",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reviewed_interviews": len(reviewed),
        "total_interviews": len(interviews),
        "recurring_gaps": recurring_gaps,
        "skill_summary": skill_summary,
        "open_actions": open_actions[:8],
        "validation_summary": validation_summary,
        "recent_validations": recent_validations,
        "timeline": sorted(timeline, key=lambda item: item.get("date", "")),
        "scoring_providers": sorted({identity[0] for identity in scoring_identities}),
        "scoring_models": sorted({identity[1] for identity in scoring_identities}),
        "gap_overrides": [value for value in gap_overrides.values() if isinstance(value, dict)],
        "mixed_scoring": comparability in {"mixed_model", "legacy_unknown"},
        "comparability": comparability,
    }
    replay_inputs = []
    for interview in reviewed_sorted:
        review = interview.get("review") or {}
        scored_by = review.get("scored_by") if isinstance(review.get("scored_by"), dict) else {}
        replay_inputs.append({
            "interview_id": str(interview.get("id", "")),
            "date": str(interview.get("date", "")),
            "updated_at": str(interview.get("updated_at", "")),
            "review_schema_version": str(review.get("schema_version", "legacy_unknown")),
            "scored_by": {
                "provider": str(scored_by.get("provider", "legacy_unknown"))[:80] or "legacy_unknown",
                "model": str(scored_by.get("model", "legacy_unknown"))[:160] or "legacy_unknown",
                "prompt_version": str(scored_by.get("prompt_version", "legacy_unknown"))[:40] or "legacy_unknown",
                "rubric_version": str(scored_by.get("rubric_version", "legacy_unknown"))[:40] or "legacy_unknown",
            },
        })
    memory["audit"] = {
        "aggregation": "deterministic",
        "algorithm_version": "growth-memory-1.4",
        "replayable": True,
        "input_count": len(replay_inputs),
        "inputs": replay_inputs,
        "override_keys": sorted(str(key)[:180] for key in gap_overrides.keys()),
        "notes": [
            "长期记忆由结构化复盘和用户治理修改重新计算，不由模型直接生成。",
            "能力趋势只能在评分身份可比时作为趋势展示。",
        ],
    }
    memory["outcome_signal"] = _outcome_signal(reviewed_sorted, comparability)
    memory.update(_stage_for(len(reviewed)))
    return memory
