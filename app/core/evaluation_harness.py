"""Deterministic regression checks for normalised PM review fixtures.

This harness deliberately does not score model quality. It checks the safety
contract around model output: schema migration, controlled IDs, bounded scores,
and evidence that remains grounded in the supplied transcript.
"""

import json
import copy
import math
import os
import sys
from itertools import combinations
from typing import Any, Dict, List

from .interview_review import _normalise_review
from .pm_skills import PM_SKILL_DIMENSIONS, gap_tag_ids
from .research_grounding import (
    AGENT_PLAN_PROMPT,
    RELEVANCE_DIMENSIONS,
    SCREEN_CANDIDATE_PROMPT,
    UNTRUSTED_PUBLIC_TEXT_MARKER,
    run_research_agent,
)


VALID_GAP_IDS = gap_tag_ids()
UNVERIFIED = "（无转写原文可佐证）"


def _grounded(value: Any, transcript: str) -> bool:
    text = str(value or "").strip()
    return not text or text == UNVERIFIED or text in transcript


def _check_case(case: Dict[str, Any]) -> Dict[str, Any]:
    transcript = str(case.get("transcript", ""))
    review = _normalise_review(case.get("review") or {}, transcript=transcript)
    issues: List[str] = []
    if review.get("schema_version") != "2.1":
        issues.append("schema_version")
    for skill in review.get("skill_diagnosis", []):
        if skill.get("skill_id") not in PM_SKILL_DIMENSIONS:
            issues.append("illegal_skill_id")
        if skill.get("score") is not None and (not isinstance(skill.get("score"), int) or not 1 <= skill["score"] <= 5):
            issues.append("skill_score_out_of_range")
        if not _grounded(skill.get("evidence"), transcript):
            issues.append("skill_evidence_not_grounded")
        for dimension in skill.get("dimensions", []):
            if dimension.get("score") is not None and not 1 <= dimension["score"] <= 5:
                issues.append("dimension_score_out_of_range")
            if not _grounded(dimension.get("evidence"), transcript):
                issues.append("dimension_evidence_not_grounded")
    for gap in review.get("gaps", []):
        if gap.get("canonical_gap_id") not in VALID_GAP_IDS:
            issues.append("illegal_gap_id")
        if not _grounded(gap.get("evidence"), transcript):
            issues.append("gap_evidence_not_grounded")
    for question in review.get("questions", []):
        if not _grounded(question.get("evidence"), transcript):
            issues.append("question_evidence_not_grounded")
    return {
        "id": str(case.get("id", "unknown")),
        "passed": not issues,
        "issues": sorted(set(issues)),
        "schema_version": review.get("schema_version"),
        "evidence_coverage": review.get("review_quality", {}).get("evidence_coverage", 0),
    }


def evaluate_review_fixtures(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        cases = json.load(handle)
    if not isinstance(cases, list):
        raise ValueError("评测 fixture 必须是数组。")
    results = [_check_case(case) for case in cases if isinstance(case, dict)]
    passed = len([item for item in results if item["passed"]])
    return {
        "suite_version": "review-normalisation-1.0",
        "fixture_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "cases": results,
    }


_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def _review_quality_metrics(review: Dict[str, Any]) -> Dict[str, Any]:
    evidence_values: List[str] = []
    for skill in review.get("skill_diagnosis", []):
        evidence_values.append(str(skill.get("evidence", "")))
        evidence_values.extend(str(item.get("evidence", "")) for item in skill.get("dimensions", []) if isinstance(item, dict))
        evidence_values.extend(str(item.get("evidence", "")) for item in skill.get("gaps", []) if isinstance(item, dict))
    for item in review.get("gaps", []) + review.get("strengths", []):
        if isinstance(item, dict):
            evidence_values.append(str(item.get("evidence", "")))
    for item in review.get("questions", []):
        if isinstance(item, dict):
            evidence_values.append(str(item.get("evidence", "")))
    verified_question_evidence = sum(
        1
        for item in review.get("questions", [])
        if isinstance(item, dict)
        and str(item.get("evidence", "")).strip()
        and str(item.get("evidence", "")).strip() != UNVERIFIED
    )
    verified = [value for value in evidence_values if value.strip() and value.strip() != UNVERIFIED]
    unverified = [value for value in evidence_values if value.strip() == UNVERIFIED]
    score_map = {
        str(skill.get("skill_id", "")): skill.get("score")
        for skill in review.get("skill_diagnosis", [])
        if isinstance(skill, dict)
    }
    gap_ids = {
        str(item.get("canonical_gap_id", ""))
        for item in review.get("gaps", [])
        if isinstance(item, dict)
    }
    executable_actions = 0
    for action in review.get("action_plan", []):
        if not isinstance(action, dict):
            continue
        criteria = action.get("success_criteria") if isinstance(action.get("success_criteria"), list) else []
        if str(action.get("action", "")).strip() and len([item for item in criteria if str(item).strip()]) >= 2 and str(action.get("next_validation", "")).strip():
            executable_actions += 1
    return {
        "score_by_skill": score_map,
        "gap_ids": sorted(gap_ids),
        "verified_evidence_count": len(verified),
        "unverified_evidence_count": len(unverified),
        "verified_question_evidence_count": verified_question_evidence,
        "executable_action_count": executable_actions,
        "review_confidence": str((review.get("review_quality") or {}).get("confidence", "low")),
        "coach_score": (review.get("score_summary") or {}).get("coach_score", 0),
        "scored_by": review.get("scored_by") or {},
    }


def _check_gold_output(case: Dict[str, Any], output: Dict[str, Any]) -> Dict[str, Any]:
    transcript = str(case.get("transcript", ""))
    review = _normalise_review(output.get("review") or {}, transcript=transcript)
    gold = case.get("gold") if isinstance(case.get("gold"), dict) else {}
    metrics = _review_quality_metrics(review)
    issues: List[str] = []
    unscored_skill_ids = {
        str(skill_id).strip()
        for skill_id in (gold.get("unscored_skill_ids") or [])
        if str(skill_id).strip()
    }
    for skill_id, score_range in (gold.get("score_ranges") or {}).items():
        actual = metrics["score_by_skill"].get(skill_id)
        if skill_id in unscored_skill_ids and actual is None:
            continue
        if not isinstance(score_range, list) or len(score_range) != 2 or actual is None or not score_range[0] <= actual <= score_range[1]:
            issues.append("score_anchor:%s" % skill_id)
    for skill_id in unscored_skill_ids:
        if metrics["score_by_skill"].get(skill_id) is not None:
            issues.append("unexpected_score:%s" % skill_id)
    for gap_id in gold.get("required_gap_ids", []):
        if gap_id not in metrics["gap_ids"]:
            issues.append("missing_gap:%s" % gap_id)
    for gap_id in gold.get("forbidden_gap_ids", []):
        if gap_id in metrics["gap_ids"]:
            issues.append("forbidden_gap:%s" % gap_id)
    if metrics["verified_evidence_count"] < int(gold.get("min_verified_evidence", 0) or 0):
        issues.append("evidence_coverage")
    if metrics["verified_question_evidence_count"] < int(gold.get("min_verified_question_evidence", 0) or 0):
        issues.append("follow_up_evidence")
    if metrics["executable_action_count"] < int(gold.get("min_executable_actions", 0) or 0):
        issues.append("action_not_executable")
    max_confidence = str(gold.get("max_review_confidence", "")).strip()
    if max_confidence and _CONFIDENCE_RANK.get(metrics["review_confidence"], 0) > _CONFIDENCE_RANK.get(max_confidence, 0):
        issues.append("confidence_overstated")
    if "max_coach_score" in gold and metrics["coach_score"] > int(gold["max_coach_score"]):
        issues.append("coach_score_overstated")
    if gold.get("require_scored_by"):
        scored_by = metrics["scored_by"]
        required = ("provider", "model", "prompt_version", "rubric_version", "scored_at")
        if any(not str(scored_by.get(key, "")).strip() or scored_by.get(key) == "legacy_unknown" for key in required):
            issues.append("missing_scored_by")
    actual_pass = not issues
    expected_pass = bool(output.get("expected_pass", True))
    return {
        "label": str(output.get("label", "unnamed")),
        "passed": actual_pass == expected_pass,
        "actual_pass": actual_pass,
        "expected_pass": expected_pass,
        "issues": sorted(set(issues)),
        "metrics": metrics,
    }


def _compare_gold_outputs(case: Dict[str, Any], outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    gold = case.get("gold") if isinstance(case.get("gold"), dict) else {}
    labels = [str(value) for value in gold.get("comparable_labels", [])]
    selected = [item for item in outputs if item.get("label") in labels and item.get("actual_pass")]
    drifts: Dict[str, int] = {}
    for left, right in combinations(selected, 2):
        left_scores = left.get("metrics", {}).get("score_by_skill", {})
        right_scores = right.get("metrics", {}).get("score_by_skill", {})
        for skill_id in set(left_scores) & set(right_scores):
            try:
                drift = abs(int(left_scores[skill_id]) - int(right_scores[skill_id]))
            except (TypeError, ValueError):
                continue
            drifts[skill_id] = max(drifts.get(skill_id, 0), drift)
    allowed = gold.get("max_score_drift")
    return {
        "labels": labels,
        "score_drift_by_skill": drifts,
        "max_score_drift": max(drifts.values()) if drifts else 0,
        "within_tolerance": allowed is None or not drifts or max(drifts.values()) <= int(allowed),
    }


def evaluate_quality_gold_fixtures(path: str) -> Dict[str, Any]:
    """Compare versioned human-labeled expectations with saved model outputs.

    This is a calibration aid, not an automatic truth oracle. The fixture's
    annotation describes acceptable score ranges and evidence/next-practice
    constraints; humans still decide whether the annotation itself is valid.
    """
    with open(path, "r", encoding="utf-8") as handle:
        cases = json.load(handle)
    if not isinstance(cases, list):
        raise ValueError("质量校准 fixture 必须是数组。")
    case_results = []
    output_passed = 0
    output_failed = 0
    comparison_failures = 0
    for case in cases:
        if not isinstance(case, dict):
            continue
        outputs = [item for item in case.get("outputs", []) if isinstance(item, dict)]
        results = [_check_gold_output(case, item) for item in outputs]
        output_passed += sum(1 for item in results if item["passed"])
        output_failed += sum(1 for item in results if not item["passed"])
        comparison = _compare_gold_outputs(case, results)
        if not comparison["within_tolerance"]:
            comparison_failures += 1
        case_results.append({
            "id": str(case.get("id", "unknown")),
            "annotation_version": str((case.get("gold") or {}).get("annotation_version", "unknown")),
            "outputs": results,
            "comparison": comparison,
        })
    return {
        "suite_version": "quality-gold-1.0",
        "fixture_count": len(case_results),
        "output_count": output_passed + output_failed,
        "passed": output_passed,
        "failed": output_failed,
        "comparison_failures": comparison_failures,
        "all_passed": output_failed == 0 and comparison_failures == 0,
        "cases": case_results,
        "interpretation": "这是人工标注约束下的回归信号，不是招聘预测，也不是自动生成的真值。",
    }


def _check_research_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Replay a bounded Agent case without network or model calls.

    The fixture controls search/fetch responses, while the real Agent loop still
    enforces URL allowlisting, canonical-URL deduplication, provenance status,
    and empty-result explanations. This is a safety regression suite, not a
    measure of search recall.
    """
    candidate = case.get("candidate")
    candidates = [candidate] if isinstance(candidate, dict) else case.get("candidates", [])
    candidates = copy.deepcopy(candidates) if isinstance(candidates, list) else []
    fetch_payload = copy.deepcopy(case.get("fetch")) if isinstance(case.get("fetch"), dict) else None
    issues: List[str] = []

    def plan(_context: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "search", "query": "fixture research query", "reasoning": "固定回放"}

    def search(_query: str) -> List[Dict[str, Any]]:
        return copy.deepcopy(candidates)

    def fetch(_url: str) -> Dict[str, Any]:
        return copy.deepcopy(fetch_payload) if fetch_payload is not None else {"fetch_status": "shell_only", "text": ""}

    def screen(_candidate: Dict[str, Any]) -> Dict[str, Any]:
        return {"recommendation": "needs_review", "relevance": 80, "reason": "固定回放"}

    result = run_research_agent(
        None,
        "示例公司",
        "产品经理",
        "一面",
        "指标与项目深挖",
        platform=str(case.get("platform", "xiaohongshu")),
        target=1,
        max_rounds=1,
        max_searches=1,
        plan_fn=plan,
        search_fn=search,
        screen_fn=screen,
        fetch_fn=fetch,
    )
    expected_stop = str(case.get("expected_stop_reason_contains", ""))
    if expected_stop and expected_stop not in str(result.get("stop_reason", "")):
        issues.append("stop_reason")
    expected_provenance = str(case.get("expected_provenance_status", ""))
    if expected_provenance:
        collected = result.get("collected") or []
        if not collected or collected[0].get("provenance_status") != expected_provenance:
            issues.append("provenance_status")
    expected_fetch = str(case.get("expected_fetch_status", ""))
    if expected_fetch:
        collected = result.get("collected") or []
        if not collected or collected[0].get("fetch_status") != expected_fetch:
            issues.append("fetch_status")
    if case.get("expected") == "candidate_text_is_untrusted":
        if UNTRUSTED_PUBLIC_TEXT_MARKER not in SCREEN_CANDIDATE_PROMPT or UNTRUSTED_PUBLIC_TEXT_MARKER not in AGENT_PLAN_PROMPT:
            issues.append("prompt_boundary")
    return {
        "id": str(case.get("id", "unknown")),
        "passed": not issues,
        "issues": sorted(set(issues)),
        "collected": len(result.get("collected") or []),
        "stop_reason": str(result.get("stop_reason", ""))[:300],
        "fetch_status_counts": result.get("search_meta", {}).get("fetch_status_counts", {}),
    }


def evaluate_research_fixtures(path: str) -> Dict[str, Any]:
    """Run deterministic replay cases for the public research Agent boundary."""
    with open(path, "r", encoding="utf-8") as handle:
        cases = json.load(handle)
    if not isinstance(cases, list):
        raise ValueError("研究 Agent fixture 必须是数组。")
    results = [_check_research_case(case) for case in cases if isinstance(case, dict)]
    passed = len([item for item in results if item["passed"]])
    return {
        "suite_version": "research-agent-replay-1.0",
        "fixture_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "cases": results,
    }


def _weighted_relevance(breakdown: Dict[str, Any]) -> int:
    """Recompute the production relevance score without a model call."""
    values = {}
    for dimension, _weight, _description in RELEVANCE_DIMENSIONS:
        try:
            values[dimension] = max(0, min(100, int((breakdown or {}).get(dimension, 0))))
        except (TypeError, ValueError):
            values[dimension] = 0
    return round(sum(values[dimension] * weight / 100 for dimension, weight, _ in RELEVANCE_DIMENSIONS))


def _dcg(relevances: List[int]) -> float:
    return sum((2 ** relevance - 1) / math.log2(index + 2) for index, relevance in enumerate(relevances))


def _check_relevance_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a versioned human relevance judgment against production ranking rules."""
    candidates = [item for item in case.get("candidates", []) if isinstance(item, dict)]
    scored = []
    for index, candidate in enumerate(candidates):
        try:
            label = max(0, min(2, int(candidate.get("relevance_label", 0) or 0)))
        except (TypeError, ValueError):
            label = 0
        score = _weighted_relevance((candidate.get("screening") or {}).get("relevance_breakdown", {}))
        scored.append({"id": str(candidate.get("id", index)), "label": label, "score": score, "index": index})
    ranked = sorted(scored, key=lambda item: (-item["score"], item["index"]))
    k = max(1, min(len(ranked) or 1, int(case.get("k", 3) or 3)))
    top = ranked[:k]
    relevant_ids = {item["id"] for item in scored if item["label"] >= 2}
    hits = sum(1 for item in top if item["id"] in relevant_ids)
    precision = round(hits / k, 3) if k else 0.0
    recall = round(hits / len(relevant_ids), 3) if relevant_ids else 1.0
    actual_dcg = _dcg([item["label"] for item in top])
    ideal = sorted((item["label"] for item in scored), reverse=True)[:k]
    ndcg = round(actual_dcg / _dcg(ideal), 3) if _dcg(ideal) else 1.0
    issues: List[str] = []
    context = case.get("query_context") if isinstance(case.get("query_context"), dict) else {}
    required_platform = str(context.get("platform", "all")).strip().lower()
    if required_platform in {"xiaohongshu", "nowcoder"}:
        for candidate in candidates:
            candidate_platform = str(candidate.get("platform_id", "")).strip().lower()
            if candidate_platform and candidate_platform != required_platform:
                issues.append("platform_constraint")
                break
    expected_top = [str(value) for value in case.get("expected_top_ids", [])]
    actual_top = [item["id"] for item in top]
    if expected_top and actual_top[:len(expected_top)] != expected_top:
        issues.append("ranking_order")
    gold = case.get("gold") if isinstance(case.get("gold"), dict) else {}
    if precision < float(gold.get("min_precision_at_k", 0) or 0):
        issues.append("precision_at_k")
    if recall < float(gold.get("min_recall_at_k", 0) or 0):
        issues.append("recall_at_k")
    if ndcg < float(gold.get("min_ndcg_at_k", 0) or 0):
        issues.append("ndcg_at_k")
    return {
        "id": str(case.get("id", "unknown")),
        "passed": not issues,
        "issues": sorted(set(issues)),
        "k": k,
        "ranking": [{"id": item["id"], "relevance": item["score"], "label": item["label"]} for item in ranked],
        "metrics": {"precision_at_k": precision, "recall_at_k": recall, "ndcg_at_k": ndcg},
    }


def evaluate_relevance_fixtures(path: str) -> Dict[str, Any]:
    """Replay human relevance judgments against the fixed production ranking formula.

    This measures retrieval ordering only. It does not establish that a source is
    authentic, usable, or safe to cite.
    """
    with open(path, "r", encoding="utf-8") as handle:
        fixture = json.load(handle)
    if isinstance(fixture, list):
        # Keep old local fixtures readable while making new judgment sets
        # versioned and self-describing.
        cases = fixture
        annotation_version = "legacy_unversioned"
        annotation_policy = {}
    elif isinstance(fixture, dict):
        cases = fixture.get("cases")
        annotation_version = str(fixture.get("dataset_version", "unversioned"))[:120]
        annotation_policy = fixture.get("annotation_policy") if isinstance(fixture.get("annotation_policy"), dict) else {}
    else:
        cases = None
        annotation_version = "unversioned"
        annotation_policy = {}
    if not isinstance(cases, list):
        raise ValueError("相关性 fixture 必须是数组或包含 cases 的版本化对象。")
    results = [_check_relevance_case(case) for case in cases if isinstance(case, dict)]
    passed = sum(1 for item in results if item["passed"])
    metrics = results and {
        key: round(sum(item["metrics"][key] for item in results) / len(results), 3)
        for key in ("precision_at_k", "recall_at_k", "ndcg_at_k")
    } or {"precision_at_k": 0.0, "recall_at_k": 0.0, "ndcg_at_k": 0.0}
    return {
        "suite_version": "relevance-judgment-1.0",
        "annotation_version": annotation_version,
        "annotation_policy": annotation_policy,
        "fixture_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "macro_metrics": metrics,
        "cases": results,
        "interpretation": "这是搜索排序的人工相关性回放，不是来源真实性、内容准确性或招聘预测。",
    }


def evaluate_all_fixtures(fixtures_root: str) -> Dict[str, Any]:
    """Run every offline quality suite from one reproducible entry point."""
    root = os.path.realpath(str(fixtures_root))
    paths = {
        "review_normalisation": os.path.join(root, "evaluation_cases.json"),
        "quality_gold": os.path.join(root, "quality_gold_cases.json"),
        "research_agent": os.path.join(root, "research_cases.json"),
        "relevance": os.path.join(root, "relevance_cases.json"),
    }
    missing = [path for path in paths.values() if not os.path.isfile(path)]
    if missing:
        raise FileNotFoundError("缺少评测 fixture：%s" % ", ".join(missing))
    reports = {
        "review_normalisation": evaluate_review_fixtures(paths["review_normalisation"]),
        "quality_gold": evaluate_quality_gold_fixtures(paths["quality_gold"]),
        "research_agent": evaluate_research_fixtures(paths["research_agent"]),
        "relevance": evaluate_relevance_fixtures(paths["relevance"]),
    }
    return {
        "suite_version": "pm-coach-evaluation-1.1",
        "fixtures_root": root,
        "all_passed": all(bool(report.get("all_passed")) for report in reports.values()),
        "reports": reports,
        "interpretation": "离线安全与质量回放，不调用模型、不联网，也不是招聘预测。",
    }


if __name__ == "__main__":
    default_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures"))
    root = sys.argv[1] if len(sys.argv) > 1 else default_root
    result = evaluate_all_fixtures(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["all_passed"] else 1)
