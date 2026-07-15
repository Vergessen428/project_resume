"""Unit tests for the interview assistant core logic.

Run: python3 -m unittest discover -s tests -v
These cover pure logic only; no network or model calls.
"""

import os
import json
import sys
import tempfile
import time
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from core.multipart import parse_multipart
from core.data_lifecycle import clear_recovery_marker, create_backup, inspect_startup_recovery, list_backups, mark_recovery_required, read_backup
from core.data_retention import apply_retention, preview_retention
from core.interview_review import _normalise_review, _normalise_growth_report, _parse_json, sample_reviewed_interview, generate_note_questions, _normalise_note_questions, generate_interview_review
from core.evaluation_harness import evaluate_all_fixtures, evaluate_quality_gold_fixtures, evaluate_relevance_fixtures, evaluate_research_fixtures, evaluate_review_fixtures
from core.growth_memory import build_candidate_memory
from core.interview_store import InterviewStore
from core.local_store import StoreDataError
from core.memory_override_store import MemoryOverrideStore
from core.operational_log import OperationalLog
from core.research_store import ResearchStore
from core.task_store import TaskFailure, TaskRegistry
from core.research_grounding import _AllowlistedRedirectHandler, build_search_query, build_search_queries, compute_recency, derive_research_topic, enrich_public_candidate, fetch_public_source, is_allowed_public_post_url, is_allowed_public_url, normalise_platform, run_research_agent, screen_candidate
from core.models import FailoverModelClient
from web_app import persist_agent_candidates, redact_company_for_model, validate_interview, validate_research, validate_research_candidate


class WebValidationTests(unittest.TestCase):
    def test_company_redaction_is_recursive_and_best_effort(self):
        value = {"transcript": "我在示例公司负责增长", "sources": [{"title": "示例公司面经"}], "count": 2}
        self.assertEqual(
            redact_company_for_model(value, "示例公司"),
            {"transcript": "我在[目标公司]负责增长", "sources": [{"title": "[目标公司]面经"}], "count": 2},
        )

    def test_short_post_interview_note_is_valid(self):
        self.assertIsNone(validate_interview({"company": "A", "role": "PM", "transcript": "答得还行"}))

    def test_blank_interview_note_is_rejected(self):
        self.assertEqual(
            validate_interview({"company": "A", "role": "PM", "transcript": "   "}),
            "请填写至少一段面试转写或面后速记。",
        )

    def test_search_candidate_can_be_stored_before_excerpt(self):
        self.assertIsNone(validate_research_candidate({"title": "候选", "url": "https://www.xiaohongshu.com/explore/demo"}))

    def test_search_candidate_rejects_non_whitelisted_host(self):
        self.assertIsNotNone(validate_research_candidate({"title": "候选", "url": "https://example.com/post"}))

    def test_manual_research_reuses_public_host_allowlist(self):
        valid = {"title": "公开面经", "url": "https://www.xiaohongshu.com/explore/demo", "source_text": "原帖正文 " * 30}
        self.assertIsNone(validate_research(valid))
        invalid = dict(valid, url="https://example.com/post")
        self.assertIn("白名单", validate_research(invalid))


class StoreIntegrityTests(unittest.TestCase):
    def test_corrupt_json_is_not_treated_as_empty_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "interviews.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{broken")
            with self.assertRaises(StoreDataError):
                InterviewStore(path).records()


class MultipartTests(unittest.TestCase):
    def test_parses_text_and_binary_file(self):
        body = (
            b"--B\r\n"
            b'Content-Disposition: form-data; name="consent"\r\n\r\n'
            b"true\r\n"
            b"--B\r\n"
            b'Content-Disposition: form-data; name="audio"; filename="c.mp3"\r\n'
            b"Content-Type: audio/mpeg\r\n\r\n"
            b"\x00\x01BYTES\x02\r\n"
            b"--B--\r\n"
        )
        fields = parse_multipart(body, "multipart/form-data; boundary=B")
        self.assertEqual(fields["consent"].text, "true")
        self.assertEqual(fields["audio"].filename, "c.mp3")
        self.assertEqual(fields["audio"].content_type, "audio/mpeg")
        self.assertEqual(fields["audio"].value, b"\x00\x01BYTES\x02")

    def test_missing_boundary_raises(self):
        with self.assertRaises(ValueError):
            parse_multipart(b"", "multipart/form-data")


class ReviewNormaliseTests(unittest.TestCase):
    def test_growth_report_structured_fields_are_grounded_in_deterministic_memory(self):
        memory = {
            "memory_version": "1.3",
            "reviewed_interviews": 2,
            "recurring_gaps": [{
                "canonical_gap_id": "metrics_experiment__attribution",
                "title": "归因意识",
                "occurrences": 2,
                "sources": [{"company": "示例公司", "round_name": "一面", "date": "2026-01-01", "evidence": "没有对照组。"}],
            }],
            "skill_summary": [{
                "skill_id": "metrics_experiment",
                "trend": "declining",
                "sources": [{"company": "示例公司", "round_name": "一面", "date": "2026-01-01", "evidence": "没有对照组。"}],
            }],
            "open_actions": [{
                "action": "重写指标归因",
                "reason": "重复缺口",
                "success_criteria": ["说明对照组"],
            }],
            "audit": {"algorithm_version": "growth-memory-1.3", "input_count": 2},
        }
        raw = {
            "summary": "模型声称发现了完全不同的新趋势。",
            "recurring_patterns": [{"skill": "fabricated", "occurrences": 99, "evidence": "伪造", "recommendation": "伪造行动"}],
            "growth_signals": [{"title": "fabricated", "evidence": "伪造", "interpretation": "伪造解释"}],
            "priority_training": [{"action": "模型擅自新增行动", "why_now": "", "success_criterion": ""}],
        }
        report = _normalise_growth_report(raw, memory=memory)
        self.assertEqual(report["recurring_patterns"][0]["skill"], "metrics_experiment__attribution")
        self.assertEqual(report["recurring_patterns"][0]["occurrences"], 2)
        self.assertEqual(report["priority_training"][0]["action"], "重写指标归因")
        self.assertTrue(report["report_grounding"]["grounded"])
        self.assertNotIn("fabricated", str(report["recurring_patterns"]))

    def test_growth_report_surfaces_mixed_scoring_warning(self):
        memory = {
            "memory_version": "1.3",
            "comparability": "mixed_model",
            "mixed_scoring": True,
            "skill_summary": [{
                "skill_id": "metrics_experiment",
                "trend": "improving",
                "sources": [{"company": "示例公司", "round_name": "一面", "date": "2026-01-01", "evidence": "有对照组。"}],
            }],
            "recurring_gaps": [],
            "open_actions": [],
            "audit": {"algorithm_version": "growth-memory-1.3", "input_count": 2},
        }
        report = _normalise_growth_report({"growth_signals": [{"skill": "metrics_experiment", "interpretation": "模型解释"}]}, memory=memory)
        self.assertEqual(report["report_grounding"]["comparability"], "mixed_model")
        self.assertIn("不应直接比较", report["growth_signals"][0]["interpretation"])
        self.assertIn("mixed_model", report["data_quality"])

    def test_evaluation_harness_reports_all_fixed_review_cases_as_safe(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "evaluation_cases.json")
        report = evaluate_review_fixtures(fixture_path)
        self.assertTrue(report["all_passed"])
        self.assertEqual(report["fixture_count"], 5)
        self.assertEqual(report["failed"], 0)

    def test_research_evaluation_harness_replays_all_boundary_cases(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "research_cases.json")
        report = evaluate_research_fixtures(fixture_path)
        self.assertTrue(report["all_passed"])
        self.assertEqual(report["fixture_count"], 5)
        self.assertEqual(report["failed"], 0)

    def test_quality_gold_harness_checks_model_outputs_and_score_drift(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "quality_gold_cases.json")
        report = evaluate_quality_gold_fixtures(fixture_path)
        self.assertTrue(report["all_passed"])
        self.assertEqual(report["output_count"], 15)
        self.assertEqual(report["comparison_failures"], 0)
        fabricated = report["cases"][0]["outputs"][2]
        self.assertFalse(fabricated["actual_pass"])
        self.assertIn("missing_scored_by", fabricated["issues"])

    def test_relevance_judgment_harness_replays_fixed_weighted_ranking(self):
        report = evaluate_relevance_fixtures(os.path.join(os.path.dirname(__file__), "fixtures", "relevance_cases.json"))
        self.assertTrue(report["all_passed"])
        self.assertEqual(report["fixture_count"], 6)
        self.assertEqual(report["annotation_version"], "relevance-judgments-2026-07-14-v3")
        self.assertGreaterEqual(report["macro_metrics"]["ndcg_at_k"], 0.95)

    def test_all_evaluation_suites_have_one_reproducible_entry_point(self):
        report = evaluate_all_fixtures(os.path.join(os.path.dirname(__file__), "fixtures"))
        self.assertTrue(report["all_passed"])
        self.assertEqual(set(report["reports"]), {"review_normalisation", "quality_gold", "research_agent", "relevance"})

    def test_fixed_evaluation_fixtures_are_normalised_without_trusting_missing_evidence(self):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "evaluation_cases.json")
        with open(fixture_path, "r", encoding="utf-8") as handle:
            cases = json.load(handle)
        self.assertGreaterEqual(len(cases), 5)
        for case in cases:
            review = _normalise_review(case["review"], transcript=case["transcript"])
            self.assertEqual(review["schema_version"], "2.1")
            for skill in review["skill_diagnosis"]:
                if skill["score"] is not None:
                    self.assertLessEqual(skill["score"], 5)
                self.assertIn(skill["skill_id"], {"product_sense", "story_ownership", "metrics_experiment", "execution_collaboration", "structured_communication", "business_context"})
            for gap in review["gaps"]:
                self.assertIn(gap["canonical_gap_id"], {"metrics_experiment__definition", "metrics_experiment__attribution", "other", "metrics_experiment__quantify"})
        fabricated = _normalise_review(cases[1]["review"], transcript=cases[1]["transcript"])
        self.assertEqual(fabricated["gaps"][0]["evidence"], "（无转写原文可佐证）")

    def test_review_metadata_is_normalised_and_legacy_is_explicit(self):
        review = _normalise_review({"summary": "s", "scored_by": {"provider": "openai", "model": "gpt-test", "prompt_version": "2.1", "rubric_version": "pm-rubric-2.0", "scored_at": "2026-01-01T00:00:00Z"}})
        self.assertEqual(review["schema_version"], "2.1")
        self.assertEqual(review["scored_by"]["provider"], "openai")
        legacy = _normalise_review({"summary": "old"})
        self.assertEqual(legacy["scored_by"]["provider"], "legacy_unknown")

    def test_v2_dimensions_use_fixed_weights(self):
        transcript = "定义转化率。拆成曝光到点击。需要做实验。"
        review = _normalise_review({
            "summary": "s",
            "skill_diagnosis": [{
                "skill_id": "metrics_experiment",
                "score": 1,
                "dimensions": [
                    {"id": "definition", "score": 5, "status": "observed", "evidence": "定义转化率。", "rationale": "口径明确"},
                    {"id": "decomposition", "score": 3, "status": "observed", "evidence": "拆成曝光到点击。", "rationale": "有链路"},
                    {"id": "attribution", "score": 1, "status": "observed", "evidence": "需要做实验。", "rationale": "验证方向"},
                    {"id": "experiment_quantify", "score": 3, "status": "observed", "evidence": "需要做实验。", "rationale": "尚无结果"},
                ],
            }],
        }, transcript=transcript)
        skill = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertEqual(skill["exact_score"], 2.9)
        self.assertEqual(skill["score"], 3)
        self.assertEqual(skill["confidence"], "high")
        self.assertEqual(skill["evidence_coverage"], 1.0)
        self.assertEqual(review["review_quality"]["evidence_coverage"], 0.17)

    def test_missing_dimension_score_is_discarded_from_weighted_result(self):
        review = _normalise_review({
            "skill_diagnosis": [{
                "skill_id": "business_context",
                "score": 5,
                "dimensions": [
                    {"id": "jd_link", "score": 5, "status": "missing", "evidence": "没有岗位对应回答。"},
                    {"id": "user_business", "score": 4, "status": "not_applicable", "evidence": ""},
                ],
            }],
        }, transcript="没有岗位对应回答。")
        skill = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "business_context")
        self.assertIsNone(skill["score"])
        self.assertIsNone(skill["exact_score"])
        self.assertIsNone(next(item for item in skill["dimensions"] if item["id"] == "jd_link")["score"])
        self.assertIsNone(next(item for item in skill["dimensions"] if item["id"] == "user_business")["score"])
        self.assertEqual(review["score_summary"]["coach_score"], 0)

    def test_review_emits_all_skills_without_trusting_unweighted_v2_score(self):
        review = _normalise_review({
            "summary": "sparse",
            "skill_diagnosis": [{
                "skill_id": "metrics_experiment",
                "score": 5,
                "dimensions": [],
            }],
        }, transcript="只有一句很短的记录")
        self.assertEqual(
            [item["skill_id"] for item in review["skill_diagnosis"]],
            ["product_sense", "story_ownership", "metrics_experiment", "execution_collaboration", "structured_communication", "business_context"],
        )
        metrics = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertIsNone(metrics["score"])
        self.assertIsNone(metrics["exact_score"])
        self.assertEqual(review["score_summary"]["coach_score"], 0)
        live_review = _normalise_review({
            "skill_diagnosis": [{"skill_id": "metrics_experiment", "score": 5}],
        }, allow_legacy_score=False)
        live_metrics = next(item for item in live_review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertIsNone(live_metrics["score"])
        self.assertIsNone(live_metrics["exact_score"])

    def test_missing_dimension_evidence_lowers_confidence(self):
        review = _normalise_review({
            "summary": "s",
            "skill_diagnosis": [{
                "skill_id": "metrics_experiment",
                "score": 5,
                "dimensions": [{"id": "attribution", "score": 5, "status": "observed", "evidence": "没有这句话", "rationale": "x"}],
            }],
        }, transcript="只有一句很短的记录")
        skill = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertEqual(skill["confidence"], "low")
        self.assertEqual(skill["evidence_coverage"], 0.0)
        self.assertIsNone(skill["exact_score"])
        self.assertIsNone(skill["score"])
        self.assertEqual(review["score_summary"]["training_band"], "证据不足")

    def test_legacy_review_keeps_string_practice_field(self):
        review = _normalise_review({
            "summary": "s",
            "skill_diagnosis": [{"skill_id": "metrics_experiment", "score": 2, "next_practice": "补充指标口径"}],
        })
        skill = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertEqual(skill["next_practice"], "补充指标口径")
        self.assertEqual(skill["practice_plan"]["action"], "补充指标口径")
    def test_scores_are_clamped_and_actions_get_ids(self):
        review = _normalise_review({
            "summary": "s",
            "questions": [{"question": "q", "score": 99}],
            "skill_diagnosis": [{"skill_id": "metrics_experiment", "score": -5}],
            "action_plan": [{"action": "a"}],
        })
        self.assertEqual(review["questions"][0]["score"], 5)
        self.assertEqual(next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")["score"], 1)
        self.assertTrue(review["action_plan"][0]["id"])
        self.assertFalse(review["action_plan"][0]["done"])
        self.assertEqual(review["action_plan"][0]["acceptance_status"], "pending")
        self.assertEqual(review["action_plan"][0]["success_criteria"], [])

    def test_question_evidence_distinguishes_missing_from_unverified(self):
        review = _normalise_review({
            "questions": [
                {"question": "没有给证据"},
                {"question": "伪造证据", "evidence": "转化率提升 30%"},
                {"question": "有原文证据", "evidence": "我把需求拆成两期。"},
            ],
        }, transcript="我把需求拆成两期。")
        self.assertEqual(
            [item["evidence_quality"] for item in review["questions"]],
            ["missing", "unverified", "verified"],
        )

    def test_parse_json_tolerates_code_fences(self):
        self.assertEqual(_parse_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_evidence_must_be_grounded_in_transcript(self):
        transcript = "[01:10] 我：因为用户多了，报名应该也会更多。"
        review = _normalise_review(
            {
                "summary": "s",
                "gaps": [
                    {"title": "真证据", "evidence": "因为用户多了，报名应该也会更多。", "improvement": "x"},
                    {"title": "假证据", "evidence": "候选人未能通过 STAR 原则系统性展示。", "improvement": "y"},
                ],
                "skill_diagnosis": [{"skill_id": "metrics_experiment", "score": 2, "evidence": "凭空捏造的一句话"}],
            },
            transcript=transcript,
        )
        # A verbatim quote (timestamp/punctuation aside) survives.
        self.assertIn("报名应该也会更多", review["gaps"][0]["evidence"])
        # Model commentary that is not in the transcript is replaced with an explicit marker.
        self.assertEqual(review["gaps"][1]["evidence"], "（无转写原文可佐证）")
        self.assertEqual(review["skill_diagnosis"][0]["evidence"], "（无转写原文可佐证）")

    def test_evidence_is_unverified_when_transcript_missing(self):
        # Without the original transcript, a model-provided quote cannot be trusted.
        review = _normalise_review(
            {"summary": "s", "gaps": [{"title": "t", "evidence": "some quote", "improvement": "i"}]},
        )
        self.assertEqual(review["gaps"][0]["evidence"], "（无转写原文可佐证）")

    def test_illegal_canonical_gap_id_falls_back_to_other(self):
        review = _normalise_review({
            "summary": "s",
            "gaps": [
                {"title": "合法标签", "canonical_gap_id": "metrics_experiment__attribution", "improvement": "x"},
                {"title": "非法标签", "canonical_gap_id": "made_up_id", "improvement": "y"},
            ],
        })
        self.assertEqual(review["gaps"][0]["canonical_gap_id"], "metrics_experiment__attribution")
        self.assertEqual(review["gaps"][1]["canonical_gap_id"], "other")

    def test_missing_score_rationale_is_tolerated(self):
        # Old model output without score_rationale must not raise; score still clamped.
        review = _normalise_review({
            "summary": "s",
            "skill_diagnosis": [{"skill_id": "metrics_experiment", "score": 9}],
        })
        skill = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertEqual(skill["score"], 5)
        self.assertEqual(skill["score_rationale"], "")


class ModelProvenanceTests(unittest.TestCase):
    class _FailingModel:
        model = "unavailable-model"

        def complete(self, _prompt):
            raise RuntimeError("quota")

    class _WorkingModel:
        model = "working-model"

        def complete(self, _prompt):
            return '{"summary":"ok","skill_diagnosis":[{"skill_id":"metrics_experiment","score":5}]}'

    class _PromptModel:
        model = "prompt-model"

        def __init__(self):
            self.prompt = ""

        def complete(self, prompt):
            self.prompt = prompt
            return '{"summary":"ok"}'

    def test_review_records_provider_that_actually_succeeded_after_failover(self):
        client = FailoverModelClient([
            ("first", self._FailingModel()),
            ("second", self._WorkingModel()),
        ])
        review = generate_interview_review(
            client,
            {"company": "示例", "role": "PM", "transcript": "我做了一个项目。"},
        )
        self.assertEqual(review["scored_by"]["provider"], "second")
        self.assertEqual(review["scored_by"]["model"], "working-model")
        self.assertIsNone(next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")["score"])

    def test_review_prompt_marks_unapproved_research_as_question_only(self):
        model = self._PromptModel()
        generate_interview_review(
            model,
            {"company": "示例", "role": "PM", "transcript": "我做了一个项目。"},
            [
                {"id": "candidate-1", "title": "待确认候选", "status": "candidate", "assessment": {"question_leads": []}},
                {"id": "auto-1", "title": "AI 预审候选", "status": "auto_approved", "assessment": {"question_leads": []}},
                {"id": "approved-1", "title": "已确认资料", "status": "approved", "assessment": {"question_leads": []}},
            ],
        )
        self.assertIn('"citation_allowed": false', model.prompt)
        self.assertIn('"source_role": "question_lead_only"', model.prompt)
        self.assertIn('"citation_allowed": true', model.prompt)
        self.assertIn('"source_role": "approved_context"', model.prompt)

    def test_unbound_approved_research_is_question_only(self):
        model = self._PromptModel()
        generate_interview_review(
            model,
            {"company": "示例", "role": "PM", "transcript": "我做了一个项目。"},
            [{"title": "伪造确认", "status": "approved", "assessment": {"question_leads": []}}],
        )
        self.assertIn('"citation_allowed": false', model.prompt)
        self.assertIn('"source_role": "question_lead_only"', model.prompt)


class GrowthMemoryTests(unittest.TestCase):
    def test_counts_only_reviewed_and_open_actions(self):
        interviews = [
            {"id": "1", "company": "A", "review": {
                "gaps": [{"title": "指标定义"}],
                "skill_diagnosis": [{"skill_id": "metrics", "score": 2}],
                "action_plan": [{"action": "练习", "done": False}, {"action": "done", "done": True}],
            }},
            {"id": "2", "company": "B"},  # no review
        ]
        mem = build_candidate_memory(interviews)
        self.assertEqual(mem["reviewed_interviews"], 1)
        self.assertEqual(mem["total_interviews"], 2)
        self.assertEqual(len(mem["open_actions"]), 1)
        self.assertEqual(mem["recurring_gaps"][0]["title"], "指标定义")
        self.assertTrue(mem["generated_at"])

    def _reviewed(self, iid, date, gaps=None, skills=None):
        return {"id": iid, "company": "C", "round_name": "一面", "date": date,
                "review": {"gaps": gaps or [], "skill_diagnosis": skills or [], "action_plan": []}}

    def test_semantically_same_gaps_aggregate_by_canonical_id(self):
        cid = "metrics_experiment__attribution"
        interviews = [
            self._reviewed("1", "2026-01", gaps=[{"title": "指标定义偏弱", "canonical_gap_id": cid}]),
            self._reviewed("2", "2026-02", gaps=[{"title": "缺乏归因意识", "canonical_gap_id": cid}]),
            self._reviewed("3", "2026-03", gaps=[{"title": "指标口径不清", "canonical_gap_id": cid}]),
        ]
        mem = build_candidate_memory(interviews)
        match = [g for g in mem["recurring_gaps"] if g["canonical_gap_id"] == cid]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["occurrences"], 3)
        self.assertEqual(len(match[0]["sources"]), 3)

    def test_memory_has_deterministic_replay_audit_without_transcript(self):
        interview = self._reviewed("i1", "2026-01", skills=[{"skill_id": "product_sense", "score": 3, "evidence": "用户问题"}])
        interview["updated_at"] = "2026-01-02T00:00:00+00:00"
        memory = build_candidate_memory([interview])
        self.assertEqual(memory["memory_version"], "1.3")
        self.assertTrue(memory["audit"]["replayable"])
        self.assertEqual(memory["audit"]["input_count"], 1)
        self.assertEqual(memory["audit"]["inputs"][0]["interview_id"], "i1")
        self.assertNotIn("transcript", json.dumps(memory["audit"], ensure_ascii=False))

    def test_legacy_gaps_without_canonical_id_fall_back_to_title(self):
        interviews = [
            self._reviewed("1", "2026-01", gaps=[{"title": "指标定义"}]),
            self._reviewed("2", "2026-02", gaps=[{"title": "指标定义"}]),
        ]
        mem = build_candidate_memory(interviews)
        match = [g for g in mem["recurring_gaps"] if g["title"] == "指标定义"]
        self.assertEqual(match[0]["occurrences"], 2)
        self.assertEqual(match[0]["canonical_gap_id"], "other")

    def test_gap_overrides_rename_and_ignore_deterministic_memory(self):
        interviews = [self._reviewed("1", "2026-01", gaps=[{"title": "指标定义", "canonical_gap_id": "metrics_experiment__attribution"}])]
        renamed = build_candidate_memory(interviews, {"metrics_experiment__attribution": {"title": "归因验证", "ignored": False}})
        self.assertEqual(renamed["recurring_gaps"][0]["title"], "归因验证")
        ignored = build_candidate_memory(interviews, {"metrics_experiment__attribution": {"ignored": True}})
        self.assertEqual(ignored["recurring_gaps"], [])

    def test_skill_trend_improving_and_insufficient(self):
        interviews = [
            self._reviewed("1", "2026-01", skills=[{"skill_id": "metrics_experiment", "score": 2}]),
            self._reviewed("2", "2026-02", skills=[{"skill_id": "metrics_experiment", "score": 2}]),
            self._reviewed("3", "2026-03", skills=[{"skill_id": "metrics_experiment", "score": 4}]),
        ]
        mem = build_candidate_memory(interviews)
        metrics = [s for s in mem["skill_summary"] if s["skill_id"] == "metrics_experiment"][0]
        self.assertEqual(metrics["trend"], "improving")
        # single observation -> insufficient_data
        single = build_candidate_memory([self._reviewed("1", "2026-01", skills=[{"skill_id": "product_sense", "score": 3}])])
        self.assertEqual(single["skill_summary"][0]["trend"], "insufficient_data")

    def test_skill_trend_prefers_exact_score_over_rounded_score(self):
        interviews = [
            self._reviewed("1", "2026-01", skills=[{"skill_id": "metrics_experiment", "score": 2, "exact_score": 2.4}]),
            self._reviewed("2", "2026-02", skills=[{"skill_id": "metrics_experiment", "score": 2, "exact_score": 2.4}]),
            self._reviewed("3", "2026-03", skills=[{"skill_id": "metrics_experiment", "score": 3, "exact_score": 2.8}]),
        ]
        memory = build_candidate_memory(interviews)
        metrics = next(item for item in memory["skill_summary"] if item["skill_id"] == "metrics_experiment")
        self.assertEqual(metrics["trend"], "stable")
        self.assertEqual(metrics["average_score"], 2.5)
        self.assertEqual(metrics["latest_score"], 2.8)
        self.assertEqual(metrics["sources"][-1]["exact_score"], 2.8)

    def test_stage_gates_on_reviewed_count(self):
        def mem_for(n):
            return build_candidate_memory([self._reviewed(str(i), "2026-0%d" % (i + 1)) for i in range(n)])
        m1 = mem_for(1)
        self.assertEqual(m1["stage"], "cold_start")
        self.assertEqual(m1["interviews_to_unlock_trend"], 1)
        self.assertEqual(mem_for(3)["stage"], "emerging")
        self.assertEqual(mem_for(5)["stage"], "established")

    def test_outcome_signal_is_descriptive_then_stable(self):
        scored_by = {"provider": "openai", "model": "gpt-test", "prompt_version": "2.1", "rubric_version": "pm-rubric-2.0"}
        interviews = []
        for index, (outcome, score) in enumerate([("passed", 76), ("passed", 72), ("failed", 58), ("failed", 61)]):
            item = self._reviewed(str(index), "2026-0%d" % (index + 1))
            item["outcome"] = outcome
            item["outcome_source"] = "self_reported"
            item["review"]["score_summary"] = {"coach_score": score}
            item["review"]["scored_by"] = scored_by
            interviews.append(item)
        descriptive = build_candidate_memory(interviews)["outcome_signal"]
        self.assertEqual(descriptive["status"], "descriptive")
        self.assertEqual(descriptive["sample_count"], 4)

        for index, (outcome, score) in enumerate([("passed", 70), ("passed", 75), ("failed", 55), ("failed", 60), ("passed", 73), ("failed", 57)]):
            item = self._reviewed("stable-%d" % index, "2026-%02d" % (index + 1))
            item["outcome"] = outcome
            item["outcome_source"] = "self_reported"
            item["review"]["score_summary"] = {"coach_score": score}
            item["review"]["scored_by"] = scored_by
            interviews.append(item)
        stable = build_candidate_memory(interviews)["outcome_signal"]
        self.assertEqual(stable["status"], "ready")
        self.assertEqual(stable["direction"], "passed_higher")

    def test_outcome_signal_falls_back_to_skill_average(self):
        interviews = []
        for index, outcome in enumerate(["passed", "passed", "failed", "failed"]):
            item = sample_reviewed_interview()
            item["id"] = str(index)
            item["outcome"] = outcome
            item["review"]["score_summary"].pop("coach_score", None)
            item["review"]["scored_by"] = {
                "provider": "openai",
                "model": "gpt-test",
                "prompt_version": "2.1",
                "rubric_version": "pm-rubric-2.0",
            }
            for skill in item["review"]["skill_diagnosis"]:
                skill["score"] = 4 if outcome == "passed" else 2
                skill["exact_score"] = float(skill["score"])
            interviews.append(item)
        signal = build_candidate_memory(interviews)["outcome_signal"]
        self.assertEqual(signal["status"], "descriptive")
        self.assertEqual(signal["passed"]["average_coach_score"], 80.0)
        self.assertEqual(signal["failed"]["average_coach_score"], 40.0)

    def test_outcome_signal_ignores_legacy_outcome_without_explicit_source(self):
        interviews = []
        for index, outcome in enumerate(["passed", "passed", "failed", "failed"]):
            item = self._reviewed(str(index), "2026-%02d" % (index + 1))
            item["outcome"] = outcome
            item["review"]["score_summary"] = {"coach_score": 70 if outcome == "passed" else 40}
            interviews.append(item)
        signal = build_candidate_memory(interviews)["outcome_signal"]
        self.assertEqual(signal["status"], "insufficient_data")
        self.assertEqual(signal["sample_count"], 0)

    def test_outcome_signal_ignores_evidence_empty_zero_scores(self):
        interviews = []
        for index, outcome in enumerate(["passed", "passed", "failed", "failed"]):
            item = self._reviewed(str(index), "2026-%02d" % (index + 1))
            item["outcome"] = outcome
            item["outcome_source"] = "self_reported"
            item["review"]["score_summary"] = {"coach_score": 0}
            interviews.append(item)
        signal = build_candidate_memory(interviews)["outcome_signal"]
        self.assertEqual(signal["status"], "insufficient_data")
        self.assertEqual(signal["sample_count"], 0)

    def test_mixed_scoring_is_never_marked_comparable(self):
        interviews = []
        for index, provider in enumerate(["openai", "gemini", "openai", "gemini", "openai", "gemini"]):
            item = self._reviewed(str(index), "2026-%02d" % (index + 1), skills=[{"skill_id": "metrics_experiment", "score": 3}])
            item["review"]["scored_by"] = {"provider": provider, "model": "model", "prompt_version": "2.1", "rubric_version": "pm-rubric-2.0"}
            interviews.append(item)
        memory = build_candidate_memory(interviews)
        self.assertTrue(memory["mixed_scoring"])
        self.assertEqual(memory["comparability"], "mixed_model")
        self.assertFalse(memory["skill_summary"][0]["trend_comparable"])

    def test_legacy_memory_aggregation_downgrades_invalid_skill_and_gap_ids(self):
        item = self._reviewed(
            "legacy-invalid",
            "2026-01-01",
            skills=[
                {"skill_id": "made_up_skill", "score": 5, "exact_score": 5},
                {"skill_id": "metrics_experiment", "score": 3, "exact_score": 3},
            ],
        )
        item["review"]["gaps"] = [{
            "canonical_gap_id": "made_up_gap",
            "title": "历史记录中的未知缺口",
            "evidence": "原文证据",
        }]
        memory = build_candidate_memory([item])
        self.assertNotIn("made_up_skill", {entry["skill_id"] for entry in memory["skill_summary"]})
        self.assertNotIn("made_up_gap", {entry["canonical_gap_id"] for entry in memory["recurring_gaps"]})


class InterviewStoreOutcomeTests(unittest.TestCase):
    def test_research_context_snapshot_keeps_jd_leads_without_raw_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({
                "company": "示例公司",
                "role": "产品经理",
                "research_context": [{
                    "title": "公开候选面经",
                    "url": "https://www.xiaohongshu.com/explore/demo",
                    "platform": "小红书",
                    "summary": "岗位相关公开线索",
                    "source_text": "不应复制到面试快照的原帖正文" * 20,
                    "status": "needs_review",
                    "screening": {
                        "relevance": 82,
                        "relevance_breakdown": {"company_match": 100, "topic_match": 80},
                    },
                    "assessment": {
                        "recommendation": "needs_review",
                        "confidence": 72,
                        "claims": ["指标追问"],
                        "question_leads": [{"question": "如何证明指标增长由方案带来？", "topic": "归因", "evidence_status": "verified"}],
                    },
                }],
            })
            saved = store.get(record["id"])
            source = saved["research_context"][0]
            self.assertEqual(source["screening"]["relevance"], 93)
            self.assertEqual(source["assessment"]["question_leads"][0]["topic"], "归因")
            self.assertEqual(source["status"], "needs_review")
            self.assertNotIn("source_text", source)

    def test_research_context_snapshot_keeps_source_identity_without_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({
                "company": "示例公司",
                "role": "产品经理",
                "transcript": "面试记录：我负责拆解需求并推进上线。",
                "research_context": [{"id": "research-123", "title": "候选", "status": "approved"}],
            })
            source = record["research_context"][0]
            self.assertEqual(source["research_id"], "research-123")
            self.assertNotIn("source_text", source)

    def test_outcome_is_whitelisted_and_legacy_defaults_are_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({"company": "A", "role": "PM", "transcript": "note", "outcome": "not-a-result", "outcome_source": "self_reported"})
            self.assertEqual(record["outcome"], "")
            self.assertEqual(record["outcome_source"], "")
            updated = store.update(record["id"], {"outcome": "passed"})
            self.assertEqual(updated["outcome"], "passed")
            self.assertEqual(updated["outcome_source"], "")
            explicit = store.update(record["id"], {"outcome": "passed", "outcome_source": "self_reported"})
            self.assertEqual(explicit["outcome_source"], "self_reported")
            self.assertTrue(store.delete(record["id"]))
            self.assertIsNone(store.get(record["id"]))
            self.assertFalse(store.delete(record["id"]))

    def test_action_completion_records_acceptance_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({"company": "A", "role": "PM", "transcript": "note"})
            store.save_review(record["id"], {"action_plan": [{"id": "a1", "action": "练习", "done": False}]})
            with self.assertRaises(ValueError):
                store.set_action_done(record["id"], "a1", True, "passed", "没有后测不应通过")
            store.add_action_attempt(record["id"], "a1", "pre_test", "前测答案")
            store.add_action_attempt(record["id"], "a1", "rewrite", "重写答案")
            store.add_action_attempt(record["id"], "a1", "post_test", "后测答案")
            updated = store.set_action_done(record["id"], "a1", True, "passed", "已经能说清核心指标和护栏指标")
            action = updated["review"]["action_plan"][0]
            self.assertTrue(action["done"])
            self.assertTrue(action["completed_at"])
            self.assertEqual(action["acceptance_status"], "passed")
            self.assertIn("护栏指标", action["acceptance_note"])

    def test_saved_training_action_keeps_source_interview_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({"company": "A", "role": "PM", "round_name": "二面", "date": "2026-01-02", "transcript": "note"})
            saved = store.save_review(record["id"], {"action_plan": [{"id": "a1", "action": "练习"}]})
            action = saved["review"]["action_plan"][0]
            self.assertEqual(action["source_interview_id"], record["id"])
            self.assertEqual(action["source_interview_date"], "2026-01-02")
            self.assertEqual(action["source_company"], "A")

    def test_regenerating_review_preserves_training_attempts_and_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({"company": "A", "role": "PM", "transcript": "note"})
            first = store.save_review(record["id"], {"action_plan": [{"action": "重写指标故事", "priority": "高", "success_criteria": ["定义核心指标", "说明验证方法"], "next_validation": "下一场先讲指标。"}]})
            first_action = first["review"]["action_plan"][0]
            store.add_action_attempt(record["id"], first_action["id"], "pre_test", "前测答案")
            store.add_action_attempt(record["id"], first_action["id"], "rewrite", "重写答案")
            store.add_action_attempt(record["id"], first_action["id"], "post_test", "后测答案")
            completed = store.set_action_done(record["id"], first_action["id"], True, "passed", "后测已通过")
            completed_at = completed["review"]["action_plan"][0]["completed_at"]
            regenerated = store.save_review(record["id"], {"summary": "模型重新生成", "action_plan": [{"action": "重写指标故事", "priority": "高", "success_criteria": ["定义核心指标", "说明验证方法"], "next_validation": "下一场先讲指标。", "source_gap_ids": ["metrics_experiment__attribution"]}]})
            action = regenerated["review"]["action_plan"][0]
            self.assertEqual(action["id"], first_action["id"])
            self.assertEqual(action["action_key"], first_action["action_key"])
            self.assertEqual([item["phase"] for item in action["attempts"]], ["pre_test", "rewrite", "post_test"])
            self.assertTrue(action["done"])
            self.assertEqual(action["acceptance_status"], "passed")
            self.assertEqual(action["completed_at"], completed_at)

    def test_training_attempts_require_order_and_keep_a_replayable_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({"company": "A", "role": "PM", "transcript": "note"})
            store.save_review(record["id"], {"action_plan": [{"id": "a1", "action": "练习", "done": False}]})
            with self.assertRaises(ValueError):
                store.add_action_attempt(record["id"], "a1", "rewrite", "重写答案")
            store.add_action_attempt(record["id"], "a1", "pre_test", "原始答案", score=30)
            store.add_action_attempt(record["id"], "a1", "rewrite", "结构化重写", criteria_met=["先说结论"])
            updated = store.add_action_attempt(record["id"], "a1", "post_test", "后测答案", score=80)
            action = updated["review"]["action_plan"][0]
            self.assertEqual([item["phase"] for item in action["attempts"]], ["pre_test", "rewrite", "post_test"])
            self.assertEqual(action["training_progress"]["attempt_count"], 3)
            self.assertTrue(action["training_progress"]["post_test"])

    def test_transcript_cleanup_keeps_structured_review_and_marks_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            record = store.create({"company": "A", "role": "PM", "date": "2026-01-01", "transcript": "原始记录"})
            store.save_review(record["id"], {"review_quality": {"data_quality": "原始复盘"}})
            self.assertEqual(store.clear_transcripts("2026-02-01"), 1)
            updated = store.get(record["id"])
            self.assertEqual(updated["transcript"], "")
            self.assertTrue(updated["transcript_cleared"])
            self.assertIn("原始转写已由用户清除", updated["review"]["review_quality"]["data_quality"])


class MemoryOverrideStoreTests(unittest.TestCase):
    def test_override_store_round_trips_and_deletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryOverrideStore(os.path.join(tmp, "memory_overrides.json"))
            record = store.upsert("metrics_experiment__attribution", "归因验证", False)
            self.assertEqual(store.list()[record["gap_key"]]["title"], "归因验证")
            store.upsert(record["gap_key"], "归因验证（已忽略）", True)
            self.assertTrue(store.delete(record["gap_key"]))
            self.assertFalse(store.delete(record["gap_key"]))
            events = store.events()
            self.assertEqual([item["action"] for item in events], ["delete", "upsert", "upsert"])
            self.assertEqual(events[0]["previous"]["title"], "归因验证（已忽略）")
            self.assertEqual(events[0]["actor"], "local_user")

    def test_override_events_can_be_restored_without_transcript_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryOverrideStore(os.path.join(tmp, "memory_overrides.json"))
            store.upsert("gap", "标签", False)
            chronological = list(reversed(store.events()))
            replacement = MemoryOverrideStore(os.path.join(tmp, "replacement.json"))
            replacement.replace_all({"gap": {"gap_key": "gap", "title": "标签", "ignored": False}})
            replacement.replace_events(chronological)
            self.assertEqual(replacement.events()[0]["gap_key"], "gap")

    def test_revert_event_restores_previous_state_and_logs_revert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryOverrideStore(os.path.join(tmp, "memory_overrides.json"))
            store.upsert("gap", "第一次标签", False)
            store.upsert("gap", "第二次标签", True)
            target = store.events()[0]
            reverted = store.revert_event(target["id"])
            restored = store.list()["gap"]
            self.assertEqual(restored["title"], "第一次标签")
            self.assertFalse(restored["ignored"])
            self.assertEqual(reverted["action"], "revert")
            self.assertEqual(reverted["reverted_event_id"], target["id"])
            self.assertEqual(store.events()[0]["id"], reverted["id"])
            with self.assertRaises(ValueError):
                store.revert_event(reverted["id"])


class DataLifecycleTests(unittest.TestCase):
    def test_versioned_backup_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = {"interviews": [{"id": "i1"}], "resumes": [], "research": [], "memory_overrides": {}}
            summary = create_backup(tmp, bundle)
            self.assertEqual(summary["counts"]["interviews"], 1)
            self.assertEqual(len(list_backups(tmp)), 1)
            self.assertEqual(read_backup(tmp, summary["backup_id"])["interviews"][0]["id"], "i1")
            self.assertEqual(summary["integrity_status"], "verified")

    def test_backup_integrity_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = create_backup(tmp, {"interviews": [{"id": "i1"}], "resumes": [], "research": [], "memory_overrides": {}})
            with open(summary["path"], "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            payload["interviews"][0]["id"] = "tampered"
            with open(summary["path"], "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            listed = list_backups(tmp)
            self.assertEqual(listed[0]["integrity_status"], "corrupt")
            with self.assertRaises(ValueError):
                read_backup(tmp, summary["backup_id"])

    def test_legacy_backup_without_override_events_remains_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup_dir = os.path.join(tmp, "backups")
            os.makedirs(backup_dir)
            path = os.path.join(backup_dir, "legacy.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({
                    "backup_version": "1.0",
                    "backup_id": "legacy",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "interviews": [],
                    "resumes": [],
                    "research": [],
                    "memory_overrides": {},
                }, handle)
            backup = read_backup(tmp, "legacy")
            self.assertEqual(backup["memory_override_events"], [])

    def test_backup_rotation_keeps_verified_tail_and_preserves_uncertain_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(3):
                create_backup(
                    tmp,
                    {"interviews": [{"id": str(index)}], "resumes": [], "research": [], "memory_overrides": {}},
                    keep_last=2,
                )
            self.assertEqual(len([item for item in list_backups(tmp) if item["integrity_status"] == "verified"]), 2)
            corrupt_path = os.path.join(tmp, "backups", "manual-uncertain.json")
            with open(corrupt_path, "w", encoding="utf-8") as handle:
                handle.write("{broken")
            create_backup(
                tmp,
                {"interviews": [{"id": "latest"}], "resumes": [], "research": [], "memory_overrides": {}},
                keep_last=2,
            )
            entries = {item["backup_id"]: item for item in list_backups(tmp)}
            self.assertIn("manual-uncertain", entries)
            self.assertEqual(entries["manual-uncertain"]["integrity_status"], "unreadable")

    def test_startup_recovery_check_surfaces_marker_corruption_and_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {"interviews": os.path.join(tmp, "interviews.json"), "memory_overrides": os.path.join(tmp, "memory_overrides.json")}
            with open(paths["interviews"], "w", encoding="utf-8") as handle:
                handle.write("{broken")
            with open(paths["memory_overrides"] + ".tmp", "w", encoding="utf-8") as handle:
                handle.write("{}")
            status = inspect_startup_recovery(tmp, paths)
            self.assertEqual(status["status"], "recovery_required")
            self.assertEqual({item["kind"] for item in status["issues"]}, {"unreadable_store", "orphaned_temp_file"})
            mark_recovery_required(tmp, "test", "回滚没有完成", ["research: RuntimeError"])
            status = inspect_startup_recovery(tmp, {})
            self.assertTrue(status["recovery_required"])
            self.assertEqual(status["marker"]["operation"], "test")
            self.assertTrue(clear_recovery_marker(tmp))

    def test_retention_preview_is_explicit_and_apply_keeps_structured_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            interviews = InterviewStore(os.path.join(tmp, "interviews.json"))
            research = ResearchStore(os.path.join(tmp, "research.json"))
            interview = interviews.create({"company": "A", "role": "PM", "date": "2020-01-01", "transcript": "原始转写"})
            interviews.save_review(interview["id"], {"summary": "结构化结果"})
            source = research.create({"title": "资料", "url": "https://www.nowcoder.com/demo", "published_date": "2020-01-01", "source_text": "原始面经"})
            preview = preview_retention(
                interviews.records(), research.list(), 30,
                now=datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
            self.assertEqual(preview["eligible_records"]["transcripts"], 1)
            self.assertEqual(preview["eligible_records"]["research_excerpts"], 1)
            self.assertFalse(preview["automatic"])
            applied = apply_retention(interviews, research, 30)
            self.assertEqual(applied["cleared"], {"transcripts": 1, "research_excerpts": 1})
            self.assertEqual(interviews.get(interview["id"])["transcript"], "")
            self.assertEqual(interviews.get(interview["id"])["review"]["summary"], "结构化结果")
            self.assertEqual(research.get(source["id"])["source_text"], "")


class ResearchIngestionTests(unittest.TestCase):
    class _AssessmentModel:
        def complete(self, _prompt):
            return '{"recommendation":"auto_approved","confidence":90,"summary":"有具体题目","claims":["记录了面试题"],"question_leads":[{"question":"如何证明提醒带来报名增长？","topic":"指标归因","evidence":"具体题目和项目追问"}],"credibility_signals":["正文具体"],"concerns":[],"review_reason":"正文足够"}'

    def test_agent_candidates_are_persisted_and_pre_assessed_by_server_helper(self):
        with tempfile.TemporaryDirectory() as tmp, patch("web_app.RESEARCH_STORE", ResearchStore(os.path.join(tmp, "research.json"))):
            result = persist_agent_candidates(self._AssessmentModel(), [{
                "title": "公开面经",
                "url": "https://www.xiaohongshu.com/explore/demo",
                "platform": "小红书",
                "source_text": "具体题目和项目追问 " * 20,
                "provenance_status": "auto_fetched_unverified",
            }])
            self.assertEqual(len(result["persisted"]), 1)
            self.assertEqual(len(result["assessed"]), 1)
            self.assertEqual(result["persisted"][0]["status"], "auto_approved")
            self.assertFalse(result["persisted"][0]["citation_allowed"])
            self.assertEqual(result["persisted"][0]["source_role"], "question_lead_only")
            self.assertEqual(result["persisted"][0]["assessment"]["question_leads"][0]["evidence_status"], "verified")

    def test_server_helper_skips_invalid_candidate_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp, patch("web_app.RESEARCH_STORE", ResearchStore(os.path.join(tmp, "research.json"))):
            result = persist_agent_candidates(self._AssessmentModel(), [{"title": "诱导", "url": "https://example.com/post"}])
            self.assertEqual(result["persisted"], [])
            self.assertEqual(len(result["skipped"]), 1)


class ResearchStoreTests(unittest.TestCase):
    def test_candidate_metadata_survives_storage_without_excerpt(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(os.path.join(directory, "research.json"))
            record = store.create({"title": "候选", "url": "https://www.xiaohongshu.com/explore/demo", "status": "candidate", "platform_id": "xiaohongshu", "search_query": "site:xiaohongshu.com/explore 候选", "provenance_status": "manual_check_required"})
            self.assertEqual(record["platform_id"], "xiaohongshu")
            self.assertEqual(record["provenance_status"], "manual_check_required")
            self.assertEqual(record["source_text"], "")

    def test_research_confidence_invalid_input_is_normalised(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(os.path.join(directory, "research.json"))
            record = store.create({"title": "候选", "url": "https://www.nowcoder.com/demo", "confidence": "not-a-number"})
            self.assertEqual(record["confidence"], 0)

    def test_screening_breakdown_survives_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(os.path.join(directory, "research.json"))
            record = store.create({
                "title": "候选",
                "url": "https://www.xiaohongshu.com/explore/demo",
                "screening": {"recommendation": "needs_review", "relevance": 72, "relevance_breakdown": {"company_match": 90}, "reason": "相关"},
            })
            self.assertEqual(record["screening"]["relevance"], 90)
            self.assertEqual(record["screening"]["relevance_breakdown"]["company_match"], 90)
            self.assertEqual(store.get(record["id"])["screening"]["reason"], "相关")

    def test_research_excerpt_cleanup_keeps_source_record(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(os.path.join(directory, "research.json"))
            record = store.create({"title": "候选", "url": "https://www.nowcoder.com/demo", "published_date": "2026-01-01", "source_text": "原帖正文", "comments_text": "评论补充"})
            self.assertEqual(store.clear_excerpts("2026-02-01"), 1)
            updated = store.get(record["id"])
            self.assertEqual(updated["source_text"], "")
            self.assertTrue(updated["excerpt_cleared"])

    def test_research_excerpt_cleanup_downgrades_approved_status(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(os.path.join(directory, "research.json"))
            record = store.create({
                "title": "候选",
                "url": "https://www.xiaohongshu.com/explore/approved",
                "published_date": "2026-01-01",
                "source_text": "原帖正文 " * 30,
            })
            store.set_status(record["id"], "approved")
            self.assertEqual(store.clear_excerpts("2026-02-01"), 1)
            updated = store.get(record["id"])
            self.assertEqual(updated["status"], "candidate")
            self.assertIsNone(updated["approval"])
            self.assertEqual(store.stats()["usable"], 0)

    def test_assessment_below_threshold_forces_needs_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({
                "title": "t", "url": "https://x", "source_text": "y" * 100,
            })
            updated = store.save_assessment(record["id"], {
                "recommendation": "auto_approved", "confidence": 40,
            })
            # The storage layer also enforces the gate so a route cannot bypass it.
            self.assertEqual(updated["confidence"], 40)
            self.assertEqual(updated["status"], "needs_review")
            self.assertEqual(updated["assessment_gate"]["deterministic_status"], "needs_review")

    def test_manual_status_cannot_bypass_ai_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({"title": "t", "url": "https://x"})
            self.assertIsNone(store.set_status(record["id"], "auto_approved"))
            self.assertEqual(store.get(record["id"])["status"], "candidate")

    def test_manual_approval_requires_allowlisted_url_and_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            short = store.create({"title": "短候选", "url": "https://www.xiaohongshu.com/explore/short"})
            self.assertIsNone(store.set_status(short["id"], "approved"))
            valid = store.create({
                "title": "完整候选",
                "url": "https://www.xiaohongshu.com/explore/valid",
                "source_text": "原帖正文 " * 30,
            })
            approved = store.set_status(valid["id"], "approved")
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["approval"]["mode"], "human_confirmed")
            self.assertEqual(approved["approval"]["actor"], "local_user")
            self.assertGreaterEqual(approved["approval"]["excerpt_chars"], 80)
            invalid = store.create({
                "title": "错误来源",
                "url": "https://example.com/post",
                "source_text": "原帖正文 " * 30,
            })
            self.assertIsNone(store.set_status(invalid["id"], "approved"))

    def test_approved_for_and_stats_recheck_legacy_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "research.json")
            store = ResearchStore(path)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([
                    {"id": "legacy-short", "status": "approved", "url": "https://www.xiaohongshu.com/explore/short", "source_text": ""},
                    {"id": "legacy-good", "status": "approved", "url": "https://www.xiaohongshu.com/explore/good", "source_text": "正文 " * 30, "company": "示例公司"},
                ], handle)
            self.assertEqual([item["id"] for item in store.approved_for("示例公司", "产品经理")], ["legacy-good"])
            self.assertEqual(store.stats()["usable"], 1)

    def test_editing_approved_evidence_requires_reassessment(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({
                "title": "候选",
                "url": "https://www.xiaohongshu.com/explore/edit",
                "source_text": "原帖正文 " * 30,
            })
            store.set_status(record["id"], "approved")
            updated = store.update(record["id"], {"source_text": "替换后的正文 " * 30})
            self.assertEqual(updated["status"], "candidate")
            self.assertIsNone(updated["assessment"])
            self.assertIsNone(updated["approval"])
            self.assertEqual(store.approved_for("", ""), [])

    def test_assessment_is_normalised_before_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({"title": "t", "url": "https://www.xiaohongshu.com/explore/assessment", "source_text": "z" * 100})
            updated = store.save_assessment(record["id"], {
                "recommendation": "auto_approved",
                "confidence": 95,
                "summary": "s" * 1000,
                "claims": ["claim"] * 10,
                "unknown": "should not persist",
            })
            self.assertEqual(updated["status"], "auto_approved")
            self.assertFalse(updated["citation_allowed"])
            self.assertEqual(updated["source_role"], "question_lead_only")
            self.assertEqual(len(updated["assessment"]["claims"]), 4)
            self.assertLessEqual(len(updated["assessment"]["summary"]), 500)
            self.assertNotIn("unknown", updated["assessment"])

    def test_auto_approval_requires_concrete_public_post_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({"title": "t", "url": "https://www.xiaohongshu.com", "source_text": "z" * 100})
            updated = store.save_assessment(record["id"], {"recommendation": "auto_approved", "confidence": 95})
            self.assertEqual(updated["status"], "needs_review")
            self.assertFalse(updated["assessment_gate"]["allowed_post_url"])

    def test_auto_approved_is_question_only_until_human_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({
                "title": "自动预审资料",
                "url": "https://www.xiaohongshu.com/explore/gate",
                "source_text": "原帖正文 " * 30,
                "company": "示例公司",
            })
            assessed = store.save_assessment(record["id"], {
                "recommendation": "auto_approved", "confidence": 95,
                "question_leads": [{"question": "如何证明结果？", "evidence": "原帖正文"}],
            })
            self.assertEqual(assessed["status"], "auto_approved")
            self.assertFalse(store.is_usable_record(assessed))
            self.assertIsNone(assessed["approval"])
            self.assertEqual(store.approved_for("示例公司", "产品经理"), [])
            approved = store.set_status(record["id"], "approved")
            self.assertTrue(approved["citation_allowed"])
            self.assertEqual(approved["source_role"], "approved_context")
            self.assertEqual(approved["approval"]["mode"], "human_confirmed")
            self.assertTrue(store.is_usable_record(approved))
            self.assertEqual([item["id"] for item in store.approved_for("示例公司", "产品经理")], [record["id"]])

    def test_question_lead_evidence_is_verified_against_source_excerpt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({"title": "t", "url": "https://x", "source_text": "原帖包含具体题目和项目追问"})
            updated = store.save_assessment(record["id"], {
                "question_leads": [
                    {"question": "如何证明结果？", "topic": "指标", "evidence": "不存在于原帖"},
                    {"question": "项目中你做了什么？", "topic": "主导力", "evidence": "具体题目和项目追问"},
                ],
            })
            leads = updated["assessment"]["question_leads"]
            self.assertEqual(leads[0]["evidence_status"], "unverified")
            self.assertEqual(leads[0]["evidence"], "")
            self.assertEqual(leads[1]["evidence_status"], "verified")

    def test_approved_for_prefers_company_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            a = store.create({"title": "a", "url": "https://www.xiaohongshu.com/explore/a", "company": "字节", "source_text": "z" * 100})
            b = store.create({"title": "b", "url": "https://www.nowcoder.com/discuss/b", "company": "腾讯", "source_text": "z" * 100})
            store.set_status(a["id"], "approved")
            store.set_status(b["id"], "approved")
            matched = store.approved_for("字节", "产品经理")
            self.assertEqual([m["company"] for m in matched], ["字节"])


class DemoSeedTests(unittest.TestCase):
    def test_seeded_sample_carries_a_full_review(self):
        # Mirrors seed_demo_data: create strips review, so it must be re-attached.
        with tempfile.TemporaryDirectory() as tmp:
            store = InterviewStore(os.path.join(tmp, "interviews.json"))
            sample = sample_reviewed_interview()
            review = sample.pop("review", None)
            created = store.create(sample)
            self.assertIsNone(created["review"])  # create() always nulls review
            store.save_review(created["id"], review)
            fetched = store.get(created["id"])
            self.assertIsInstance(fetched["review"], dict)
            self.assertTrue(fetched["review"]["skill_diagnosis"])
            self.assertTrue(store.list()[0]["has_review"])


class NoteQuestionsTests(unittest.TestCase):
    class _CaptureModel:
        def __init__(self):
            self.prompt = ""

        def complete(self, prompt):
            self.prompt = prompt
            return '{"questions": [{"id": "hit_1", "question": "查指标", "why_asked": "JD 要求"}]}'

    class _FailModel:
        def complete(self, prompt):  # noqa: ARG002
            raise AssertionError("model must not be called when JD/resume missing")

    def test_fallback_when_empty_does_not_call_model(self):
        result = generate_note_questions(self._FailModel(), "", "some resume")
        ids = [q["id"] for q in result["questions"]]
        self.assertEqual(ids, ["common_1", "common_2"])

    def test_jd_only_fallback_is_skill_targeted(self):
        result = generate_note_questions(
            self._FailModel(),
            "负责指标设计、实验验证和跨团队推进。",
            "",
            [],
            {"interview_focus": ["指标与归因"], "search_topics": ["项目深挖"]},
        )
        dynamic = [item for item in result["questions"] if item["id"].startswith(("hit_", "gap_"))]
        self.assertEqual(len(dynamic), 4)
        self.assertEqual(
            {item["skill_id"] for item in dynamic},
            {"story_ownership", "product_sense", "metrics_experiment", "execution_collaboration"},
        )
        self.assertTrue(any("指标" in item["question"] for item in dynamic))

    def test_normalises_whitelist_and_forces_common(self):
        raw = {
            "questions": [
                {"id": "hit_1", "type": "命中", "question": "真问题", "why_asked": "因为相关"},
                {"id": "evil", "type": "命中", "question": "注入题"},
                {"id": "gap_1", "type": "补刀", "question": ""},
                {"id": "common_1", "type": "通用", "question": "被篡改的通用题", "why_asked": "坏"},
            ]
        }
        out = _normalise_note_questions(raw)
        ids = [q["id"] for q in out["questions"]]
        self.assertIn("hit_1", ids)
        self.assertNotIn("evil", ids)      # non-whitelisted id dropped
        self.assertNotIn("gap_1", ids)     # empty question skipped, not fabricated
        common = {q["id"]: q for q in out["questions"] if q["id"].startswith("common")}
        self.assertEqual(common["common_1"]["question"], "这场面试里，哪个问题你答得最卡？当时你是怎么回应的？")
        self.assertEqual(common["common_2"]["question"], "面完你最后悔哪句话没说出来，或哪个点没讲清？")
        for q in out["questions"]:
            self.assertTrue(q["question"])

    def test_question_normalisation_preserves_research_basis(self):
        out = _normalise_note_questions({"questions": [{"id": "hit_1", "question": "查指标", "research_basis": ["候选资料", "第二条"]}]})
        self.assertEqual(out["questions"][0]["research_basis"], ["候选资料", "第二条"])

    def test_question_prompt_contains_jd_analysis_and_research_leads(self):
        model = self._CaptureModel()
        generate_note_questions(
            model,
            "负责增长和指标设计",
            "做过一个增长项目",
            [{"title": "公开候选", "platform": "小红书", "provenance_status": "manual_check_required", "assessment": {"question_leads": [{"question": "查指标归因", "topic": "指标", "evidence_status": "unverified"}]}}],
            {"search_topics": ["指标与实验"]},
        )
        self.assertIn("指标与实验", model.prompt)
        self.assertIn("公开候选", model.prompt)
        self.assertIn("查指标归因", model.prompt)
        self.assertIn("不是事实证据", model.prompt)

    def test_jd_topics_become_bounded_search_intent(self):
        topic = derive_research_topic("", {"search_topics": ["指标设计", "项目深挖"], "search_synonyms": ["增长实验"], "keywords": ["实验"]})
        self.assertIn("指标设计", topic)
        self.assertIn("项目深挖", topic)
        self.assertIn("增长实验", topic)


class ResearchAgentTests(unittest.TestCase):
    def test_recent_research_cache_reuses_only_fresh_matching_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            query = "site:xiaohongshu.com/explore 示例公司 产品经理 一面 指标 面经"
            now = datetime(2026, 1, 2, tzinfo=timezone.utc)
            for index in range(3):
                store.create({
                    "title": "候选 %s" % index,
                    "url": "https://www.xiaohongshu.com/explore/cache-%s" % index,
                    "platform_id": "xiaohongshu",
                    "search_query": query,
                    "retrieved_at": "2026-01-02T00:00:00+00:00",
                })
            cached = store.recent_candidates_for_queries([query], "xiaohongshu", ttl_seconds=3600, now=now, limit=3)
            self.assertEqual(len(cached), 3)
            stale = store.recent_candidates_for_queries(
                [query], "xiaohongshu", ttl_seconds=60,
                now=datetime(2026, 1, 2, 0, 2, tzinfo=timezone.utc), limit=3,
            )
            self.assertEqual(stale, [])

    def test_query_plan_has_bounded_variants(self):
        queries = build_search_queries("示例公司", "产品经理", "一面", "指标与实验", "xiaohongshu")
        self.assertEqual(len(queries), 3)
        self.assertTrue(all("site:xiaohongshu.com/explore" in query for query in queries))

    def test_public_fetch_rejects_non_platform_hosts(self):
        result = fetch_public_source("http://127.0.0.1:8765/private")
        self.assertEqual(result["fetch_status"], "unsupported_host")

    def test_public_url_boundary_rejects_userinfo_and_arbitrary_ports(self):
        self.assertFalse(is_allowed_public_url("https://user:password@www.xiaohongshu.com/explore/demo"))
        self.assertFalse(is_allowed_public_url("https://www.xiaohongshu.com:8080/explore/demo"))
        self.assertFalse(is_allowed_public_url("https://www.xiaohongshu.com:bad/explore/demo"))

    def test_public_candidate_url_must_point_to_a_concrete_post(self):
        self.assertTrue(is_allowed_public_post_url("https://www.xiaohongshu.com/explore/demo"))
        self.assertTrue(is_allowed_public_post_url("https://www.nowcoder.com/discuss/demo"))
        self.assertFalse(is_allowed_public_post_url("https://www.xiaohongshu.com/"))
        self.assertFalse(is_allowed_public_post_url("https://www.nowcoder.com/"))

    def test_public_fetch_extracts_metadata_and_visible_text(self):
        class Headers(dict):
            def get_content_charset(self):
                return "utf-8"

        class Response:
            headers = Headers({"Content-Type": "text/html; charset=utf-8"})

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return ('<html><head><title>公开面经</title><meta name="description" content="具体面试摘要"></head><body><script>ignore()</script><p>%s</p></body></html>' % ("指标定义和项目复盘 " * 12)).encode("utf-8")

            def geturl(self):
                return "https://www.xiaohongshu.com/explore/canonical"

            def getheader(self, *_args):
                return None

        class Opener:
            def open(self, *_args, **_kwargs):
                return Response()

        with patch("core.research_grounding.urllib.request.build_opener", return_value=Opener()):
            result = fetch_public_source("https://www.xiaohongshu.com/explore/demo")
        self.assertEqual(result["fetch_status"], "fetched_metadata")
        self.assertEqual(result["canonical_url"], "https://www.xiaohongshu.com/explore/canonical")
        self.assertIn("公开面经", result["title"])
        self.assertIn("指标定义", result["text"])
        self.assertNotIn("ignore", result["text"])

    def test_public_fetch_rejects_redirect_to_unapproved_host(self):
        class Headers(dict):
            def get_content_charset(self):
                return "utf-8"

        class Response:
            headers = Headers({"Content-Type": "text/html; charset=utf-8"})

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return b"<html><body>not used</body></html>"

            def geturl(self):
                return "https://example.com/private"

        class Opener:
            def open(self, *_args, **_kwargs):
                return Response()

        with patch("core.research_grounding.urllib.request.build_opener", return_value=Opener()):
            result = fetch_public_source("https://www.xiaohongshu.com/explore/demo")
        self.assertEqual(result["fetch_status"], "redirect_blocked")

    def test_redirect_handler_blocks_before_following_unapproved_target(self):
        request = type("Request", (), {"full_url": "https://www.xiaohongshu.com/explore/demo"})()
        handler = _AllowlistedRedirectHandler("xiaohongshu")
        with self.assertRaises(RuntimeError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://example.com/private")

    def test_redirect_handler_keeps_platform_route(self):
        request = type("Request", (), {"full_url": "https://www.xiaohongshu.com/explore/demo"})()
        handler = _AllowlistedRedirectHandler("xiaohongshu")
        with self.assertRaises(RuntimeError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://www.nowcoder.com/discuss/demo")

    def test_agent_attaches_public_fetch_status_before_screening(self):
        seen = []

        def plan(_context):
            return {"action": "search", "query": "q", "reasoning": "test"}

        def screen(candidate):
            seen.append(candidate)
            return {"recommendation": "needs_review", "relevance": 80}

        result = run_research_agent(
            None, "公司", "岗位", "一面", target=1, max_rounds=1,
            plan_fn=plan,
            search_fn=lambda _query: [{"url": "https://www.xiaohongshu.com/explore/demo", "title": "搜索标题"}],
            screen_fn=screen,
            fetch_fn=lambda _url: {"fetch_status": "fetched_metadata", "canonical_url": "https://www.xiaohongshu.com/explore/demo", "title": "原帖标题", "text": "原帖正文 " * 30},
        )
        self.assertTrue(result["found_enough"])
        self.assertEqual(seen[0]["title"], "原帖标题")
        self.assertEqual(seen[0]["provenance_status"], "auto_fetched_unverified")
        self.assertEqual(seen[0]["fetch_status"], "fetched_metadata")
        self.assertEqual(result["collected"][0]["query_source"], "agent_planned")

    def test_agent_drops_non_whitelisted_search_results_before_screening(self):
        seen = []
        result = run_research_agent(
            None, "公司", "岗位", "一面", target=1, max_rounds=1,
            plan_fn=lambda _context: {"action": "search", "query": "q", "reasoning": "test"},
            search_fn=lambda _query: [{"url": "https://example.com/injected", "title": "诱导内容"}],
            screen_fn=lambda candidate: seen.append(candidate) or {"recommendation": "needs_review"},
        )
        self.assertFalse(result["found_enough"])
        self.assertEqual(seen, [])

    def test_agent_drops_platform_homepage_before_screening(self):
        seen = []
        result = run_research_agent(
            None, "公司", "岗位", "一面", platform="xiaohongshu", target=1, max_rounds=1,
            plan_fn=lambda _context: {"action": "search", "query": "公司 岗位", "reasoning": "test"},
            search_fn=lambda _query: [{"url": "https://www.xiaohongshu.com/", "title": "平台首页"}],
            screen_fn=lambda candidate: seen.append(candidate) or {"recommendation": "needs_review"},
        )
        self.assertFalse(result["found_enough"])
        self.assertEqual(seen, [])

    def test_platform_query_uses_public_xiaohongshu_scope(self):
        query = build_search_query("示例公司", "产品经理", "一面", "指标", "xiaohongshu")
        self.assertIn("site:xiaohongshu.com/explore", query)
        self.assertEqual(normalise_platform("xiaohongshu"), "xiaohongshu")
        self.assertEqual(normalise_platform("unsupported"), "all")

    def test_agent_records_platform_scoped_query(self):
        calls = []

        def plan(context):
            return {"action": "search", "query": "公司 岗位", "reasoning": "平台限定"}

        def search(query):
            calls.append(query)
            return []

        result = run_research_agent(
            object(), "公司", "岗位", "一面", platform="xiaohongshu", target=1, max_rounds=1,
            plan_fn=plan, search_fn=search, screen_fn=lambda candidate: {"recommendation": "needs_review"},
        )
        self.assertIn("site:xiaohongshu.com/explore", calls[0])
        self.assertEqual(result["search_meta"]["platform"], "xiaohongshu")
        self.assertEqual(result["search_meta"]["result_count"], 0)
        self.assertTrue(result["search_meta"]["empty_reason"])
        self.assertIn("failure_reasons", result["search_meta"])

    def test_agent_cannot_widen_platform_scope_from_planner_query(self):
        calls = []

        def search(query):
            calls.append(query)
            return []

        run_research_agent(
            object(), "公司", "岗位", "一面", platform="xiaohongshu", target=1, max_rounds=1,
            plan_fn=lambda _context: {"action": "search", "query": "site:example.com 岗位", "reasoning": "错误平台"},
            search_fn=search,
        )
        self.assertIn("site:xiaohongshu.com/explore", calls[0])
        self.assertNotIn("site:example.com", calls[0])

    def test_agent_deduplicates_candidates_after_canonical_redirect(self):
        result = run_research_agent(
            None, "公司", "岗位", "一面", platform="xiaohongshu", target=3, max_rounds=1,
            plan_fn=lambda _context: {"action": "search", "query": "q", "reasoning": "test"},
            search_fn=lambda _query: [
                {"url": "https://www.xiaohongshu.com/explore/one", "title": "一"},
                {"url": "https://www.xiaohongshu.com/explore/two", "title": "二"},
            ],
            fetch_fn=lambda _url: {"fetch_status": "fetched_metadata", "canonical_url": "https://www.xiaohongshu.com/explore/same", "text": "正文 " * 30},
            screen_fn=lambda _candidate: {"recommendation": "needs_review", "relevance": 80},
        )
        self.assertEqual(len(result["collected"]), 1)
        self.assertEqual(result["trace"][0]["skipped"], 1)

    def test_retries_with_new_query_until_enough(self):
        queries = []

        def plan(context):
            return {"action": "search", "query": "q%d" % context["collected_count"], "reasoning": "try"}

        def search(query):
            queries.append(query)
            return [{"url": "https://www.xiaohongshu.com/explore/%s" % len(queries), "title": "t-%s" % query}]

        def screen(candidate):
            return {"recommendation": "needs_review", "relevance": 70, "reason": "ok"}

        result = run_research_agent(None, "字节", "PM", "一面", target=2, max_rounds=5, max_searches=6,
                                    plan_fn=plan, search_fn=search, screen_fn=screen)
        self.assertTrue(result["found_enough"])
        self.assertEqual(len(result["collected"]), 2)
        # found_enough is orthogonal to stop_reason: it only reflects the count.
        self.assertEqual(result["found_enough"], len(result["collected"]) >= 2)
        self.assertGreaterEqual(len(queries), 2)
        self.assertNotEqual(queries[0], queries[1])  # different wording each round

    def test_stops_without_progress_and_reports_not_enough(self):
        def plan(context):
            return {"action": "search", "query": "q%d" % context["collected_count"], "reasoning": "try"}

        def search(query):
            return [{"url": "https://www.xiaohongshu.com/explore/dup", "title": "dup"}]  # same URL, deduped after round 1

        def screen(candidate):
            return {"recommendation": "dismissed", "relevance": 5, "reason": "off-topic"}

        result = run_research_agent(None, "x", "y", "z", target=3, max_rounds=10, max_searches=6,
                                    plan_fn=plan, search_fn=search, screen_fn=screen)
        self.assertFalse(result["found_enough"])
        self.assertEqual(result["collected"], [])

    def test_search_call_hard_cap(self):
        counter = {"n": 0}

        def plan(context):
            return {"action": "search", "query": "q%d" % counter["n"], "reasoning": "try"}

        def search(query):
            counter["n"] += 1
            return [{"url": "https://www.xiaohongshu.com/explore/%d" % counter["n"], "title": "t"}]

        def screen(candidate):
            return {"recommendation": "dismissed", "relevance": 0, "reason": "no"}

        result = run_research_agent(None, "x", "y", "z", target=99, max_rounds=99, max_searches=6,
                                    plan_fn=plan, search_fn=search, screen_fn=screen)
        self.assertEqual(counter["n"], 3)  # never exceeds the lightweight search budget
        self.assertIn("已尝试 3 条查询", result["stop_reason"])
        self.assertIn("未发现", result["stop_reason"])

    def test_screen_candidate_is_deterministic_and_explains_matches(self):
        candidate = {
            "url": "http://a",
            "title": "示例公司 产品经理一面面经：指标与实验项目深挖",
            "summary": "面试官追问项目取舍、指标定义和复盘。",
            "published_date": "2025-12-01",
        }
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        first = screen_candidate(object(), candidate, "示例公司", "产品经理", "一面", "指标与实验", now=now)
        second = screen_candidate(object(), candidate, "示例公司", "产品经理", "一面", "指标与实验", now=now)
        self.assertEqual(first, second)
        self.assertEqual(first["relevance_method"], "deterministic_v1")
        self.assertEqual(first["recommendation"], "needs_review")
        self.assertIn("命中目标公司", first["match_reasons"])
        self.assertEqual(first["relevance_breakdown"]["recency"], 100)

    def test_screen_candidate_excludes_unfilled_dimensions(self):
        out = screen_candidate(
            object(),
            {"title": "产品经理面经：指标项目深挖", "summary": "记录面试官追问和复盘。"},
            "",
            "产品经理",
            "",
            "指标与实验",
            now=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        self.assertIsNone(out["relevance_breakdown"]["company_match"])
        self.assertIsNone(out["relevance_breakdown"]["round_match"])
        self.assertIsNone(out["relevance_breakdown"]["recency"])
        self.assertIn("company_match", out["not_applicable_dimensions"])
        self.assertGreaterEqual(out["relevance"], 45)

    def test_recency_is_deterministic_and_unknown_dates_are_not_guessed(self):
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(compute_recency("2026-01-01", now), 100)
        self.assertEqual(compute_recency("2025-01-02", now), 60)
        self.assertEqual(compute_recency("2023-01-01", now), 20)
        self.assertIsNone(compute_recency("", now))
        self.assertIsNone(compute_recency("not-a-date", now))


class ResearchFixtureTests(unittest.TestCase):
    def test_research_fixture_cases_are_policy_bounded(self):
        with open(os.path.join(os.path.dirname(__file__), "fixtures", "research_cases.json"), "r", encoding="utf-8") as handle:
            cases = json.load(handle)
        self.assertEqual({case["id"] for case in cases}, {
            "empty_xiaohongshu_search",
            "shell_only_public_page",
            "public_body_auto_fetched_unverified",
            "redirect_outside_allowlist",
            "web_prompt_injection_candidate",
        })
        shell = next(case for case in cases if case["id"] == "shell_only_public_page")
        enriched = enrich_public_candidate(shell["candidate"], fetch_fn=lambda _url: shell["fetch"])
        self.assertEqual(enriched["provenance_status"], shell["expected_provenance_status"])
        body = next(case for case in cases if case["id"] == "public_body_auto_fetched_unverified")
        enriched_body = enrich_public_candidate(body["candidate"], fetch_fn=lambda _url: body["fetch"])
        self.assertEqual(enriched_body["provenance_status"], body["expected_provenance_status"])
        self.assertEqual(enriched_body["fetch_status"], body["expected_fetch_status"])
        redirect = next(case for case in cases if case["id"] == "redirect_outside_allowlist")
        self.assertEqual(redirect["fetch"]["fetch_status"], redirect["expected_fetch_status"])
        injection = next(case for case in cases if case["id"] == "web_prompt_injection_candidate")
        self.assertTrue(is_allowed_public_url(injection["candidate"]["url"]))
        self.assertEqual(injection["expected"], "candidate_text_is_untrusted")


class TaskRegistryTests(unittest.TestCase):
    def test_task_runs_and_exposes_result_without_input_payload(self):
        registry = TaskRegistry(max_workers=1, max_attempts=2)
        task = registry.submit("demo", lambda: {"value": 42})
        for _ in range(50):
            current = registry.get(task["id"])
            if current["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertEqual(current["status"], "succeeded")
        self.assertEqual(current["result"], {"value": 42})
        self.assertNotIn("runner", current)

    def test_failed_task_can_retry_once_and_then_is_bounded(self):
        state = {"calls": 0}

        def runner():
            state["calls"] += 1
            if state["calls"] == 1:
                raise RuntimeError("temporary failure")
            return {"ok": True}

        registry = TaskRegistry(max_workers=1, max_attempts=2)
        task = registry.submit("retryable", runner)
        for _ in range(50):
            current = registry.get(task["id"])
            if current["status"] == "failed":
                break
            time.sleep(0.01)
        retried = registry.retry(task["id"])
        self.assertEqual(retried["status"], "queued")
        for _ in range(50):
            current = registry.get(task["id"])
            if current["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertEqual(current["status"], "succeeded")
        self.assertEqual(current["attempt"], 2)
        with self.assertRaises(ValueError):
            registry.retry(task["id"])

    def test_unwrapped_task_exception_does_not_leak_internal_message(self):
        registry = TaskRegistry(max_workers=1)
        task = registry.submit("unsafe", lambda: (_ for _ in ()).throw(RuntimeError("secret transcript")))
        for _ in range(50):
            current = registry.get(task["id"])
            if current["status"] == "failed":
                break
            time.sleep(0.01)
        self.assertEqual(current["error"], "任务执行失败，请稍后重试。")

    def test_task_failure_preserves_explicit_safe_message(self):
        registry = TaskRegistry(max_workers=1)
        task = registry.submit("safe", lambda: (_ for _ in ()).throw(TaskFailure("模型配额不足，请稍后重试。")))
        for _ in range(50):
            current = registry.get(task["id"])
            if current["status"] == "failed":
                break
            time.sleep(0.01)
        self.assertEqual(current["error"], "模型配额不足，请稍后重试。")

    def test_persisted_metadata_excludes_result_and_marks_unfinished_work_abandoned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tasks.json")
            registry = TaskRegistry(max_workers=1, path=path)
            task = registry.submit("review", lambda: {"transcript": "secret result"})
            for _ in range(50):
                current = registry.get(task["id"])
                if current["status"] == "succeeded":
                    break
                time.sleep(0.01)
            with open(path, "r", encoding="utf-8") as handle:
                persisted = handle.read()
            self.assertNotIn("secret result", persisted)
            restored = TaskRegistry(max_workers=1, path=path)
            self.assertEqual(restored.get(task["id"])["status"], "succeeded")
            self.assertIsNone(restored.get(task["id"])["result"])

            interrupted_path = os.path.join(tmp, "interrupted.json")
            with open(interrupted_path, "w", encoding="utf-8") as handle:
                json.dump({"task_store_version": "1.0", "tasks": [{
                    "id": "task_interrupted", "kind": "review", "status": "running", "attempt": 1,
                    "max_attempts": 2, "created_at": "x", "updated_at": "x", "error": "",
                }]}, handle)
            interrupted = TaskRegistry(max_workers=1, path=interrupted_path)
            loaded = interrupted.get("task_interrupted")
            self.assertEqual(loaded["status"], "abandoned")
            self.assertIn("重新提交", loaded["error"])

    def test_timeout_is_terminal_and_late_runner_result_is_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = TaskRegistry(max_workers=1, timeout_seconds=0.03, path=os.path.join(tmp, "tasks.json"))
            task = registry.submit("slow", lambda: (time.sleep(0.08), {"late": True})[1])
            for _ in range(50):
                current = registry.get(task["id"])
                if current["status"] == "timed_out":
                    break
                time.sleep(0.01)
            self.assertEqual(current["status"], "timed_out")
            time.sleep(0.08)
            self.assertEqual(registry.get(task["id"])["status"], "timed_out")
            self.assertIsNone(registry.get(task["id"])["result"])

    def test_queued_task_can_be_cancelled_before_runner_starts(self):
        started = threading.Event()
        release = threading.Event()
        called = {"queued": False}
        registry = TaskRegistry(max_workers=1)
        blocker = registry.submit("blocker", lambda: (started.set(), release.wait(1), {})[2])
        self.assertTrue(started.wait(1))
        queued = registry.submit("queued", lambda: (called.__setitem__("queued", True), {})[1])
        cancelled = registry.cancel(queued["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        release.set()
        for _ in range(50):
            if registry.get(blocker["id"])["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertFalse(called["queued"])

    def test_running_task_cancel_discards_late_result(self):
        started = threading.Event()
        release = threading.Event()
        registry = TaskRegistry(max_workers=1)

        def runner():
            started.set()
            release.wait(1)
            return {"late": True}

        task = registry.submit("running", runner)
        self.assertTrue(started.wait(1))
        for _ in range(50):
            if registry.get(task["id"])["status"] == "running":
                break
            time.sleep(0.01)
        self.assertEqual(registry.cancel(task["id"])["status"], "cancel_requested")
        release.set()
        for _ in range(50):
            current = registry.get(task["id"])
            if current["status"] == "cancelled":
                break
            time.sleep(0.01)
        self.assertEqual(current["status"], "cancelled")
        self.assertIsNone(current["result"])


class OperationalLogTests(unittest.TestCase):
    def test_log_allowlist_redacts_sensitive_values_and_rotates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "operations.jsonl")
            log = OperationalLog(path, max_bytes=4096, keep_rotated=1)
            log.emit("task_failed", {
                "task_id": "task_1",
                "error_code": "RuntimeError",
                "route": "/api/interviews/i1/review",
                "message": "secret transcript should not be recorded",
                "model": "model-x",
                "provider": "provider-x",
                "route_with_email": "person@example.com",
            })
            first = log.list()
            self.assertEqual(first[0]["event"], "task_failed")
            self.assertNotIn("message", first[0])
            self.assertNotIn("secret transcript", json.dumps(first, ensure_ascii=False))
            for index in range(80):
                log.emit("task_failed", {"task_id": "task_%s" % index, "error_code": "X" * 120})
            self.assertTrue(os.path.exists(path + ".1"))
            self.assertLessEqual(os.path.getsize(path), 4096)

    def test_task_lifecycle_events_are_safe_and_queryable(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = OperationalLog(os.path.join(tmp, "operations.jsonl"))
            registry = TaskRegistry(max_workers=1, event_sink=log.emit)
            task = registry.submit("review", lambda: {"transcript": "not an event field"})
            for _ in range(50):
                current = registry.get(task["id"])
                if current["status"] == "succeeded":
                    break
                time.sleep(0.01)
            events = log.list()
            self.assertIn("task_submitted", [item["event"] for item in events])
            self.assertIn("task_succeeded", [item["event"] for item in events])
            self.assertNotIn("not an event field", json.dumps(events, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
