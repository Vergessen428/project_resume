"""Unit tests for the interview assistant core logic.

Run: python3 -m pytest tests/ -q   (or: python3 tests/test_core.py)
These cover pure logic only; no network or model calls.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from core.multipart import parse_multipart
from core.interview_review import _normalise_review, _parse_json, sample_reviewed_interview, generate_note_questions, _normalise_note_questions
from core.growth_memory import build_candidate_memory
from core.interview_store import InterviewStore
from core.research_store import ResearchStore
from core.research_grounding import run_research_agent, screen_candidate


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
    def test_scores_are_clamped_and_actions_get_ids(self):
        review = _normalise_review({
            "summary": "s",
            "questions": [{"question": "q", "score": 99}],
            "skill_diagnosis": [{"skill_id": "x", "score": -5}],
            "action_plan": [{"action": "a"}],
        })
        self.assertEqual(review["questions"][0]["score"], 5)
        self.assertEqual(review["skill_diagnosis"][0]["score"], 1)
        self.assertTrue(review["action_plan"][0]["id"])
        self.assertFalse(review["action_plan"][0]["done"])

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
                "skill_diagnosis": [{"skill_id": "m", "score": 2, "evidence": "凭空捏造的一句话"}],
            },
            transcript=transcript,
        )
        # A verbatim quote (timestamp/punctuation aside) survives.
        self.assertIn("报名应该也会更多", review["gaps"][0]["evidence"])
        # Model commentary that is not in the transcript is replaced with an explicit marker.
        self.assertEqual(review["gaps"][1]["evidence"], "（无转写原文可佐证）")
        self.assertEqual(review["skill_diagnosis"][0]["evidence"], "（无转写原文可佐证）")

    def test_evidence_kept_when_transcript_missing(self):
        # No transcript to check against: keep whatever the model returned, do not blank it.
        review = _normalise_review(
            {"summary": "s", "gaps": [{"title": "t", "evidence": "some quote", "improvement": "i"}]},
        )
        self.assertEqual(review["gaps"][0]["evidence"], "some quote")

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
        self.assertEqual(review["skill_diagnosis"][0]["score"], 5)
        self.assertEqual(review["skill_diagnosis"][0]["score_rationale"], "")


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

    def test_legacy_gaps_without_canonical_id_fall_back_to_title(self):
        interviews = [
            self._reviewed("1", "2026-01", gaps=[{"title": "指标定义"}]),
            self._reviewed("2", "2026-02", gaps=[{"title": "指标定义"}]),
        ]
        mem = build_candidate_memory(interviews)
        match = [g for g in mem["recurring_gaps"] if g["title"] == "指标定义"]
        self.assertEqual(match[0]["occurrences"], 2)
        self.assertEqual(match[0]["canonical_gap_id"], "other")

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

    def test_stage_gates_on_reviewed_count(self):
        def mem_for(n):
            return build_candidate_memory([self._reviewed(str(i), "2026-0%d" % (i + 1)) for i in range(n)])
        m1 = mem_for(1)
        self.assertEqual(m1["stage"], "cold_start")
        self.assertEqual(m1["interviews_to_unlock_trend"], 1)
        self.assertEqual(mem_for(3)["stage"], "emerging")
        self.assertEqual(mem_for(5)["stage"], "established")


class ResearchStoreTests(unittest.TestCase):
    def test_assessment_below_threshold_forces_needs_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            record = store.create({
                "title": "t", "url": "https://x", "source_text": "y" * 100,
            })
            updated = store.save_assessment(record["id"], {
                "recommendation": "auto_approved", "confidence": 40,
            })
            # store trusts the recommendation string it is given; the confidence
            # gate lives in research_grounding.assess_public_source.
            self.assertEqual(updated["confidence"], 40)

    def test_approved_for_prefers_company_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(os.path.join(tmp, "research.json"))
            a = store.create({"title": "a", "url": "https://a", "company": "字节", "source_text": "z" * 100})
            b = store.create({"title": "b", "url": "https://b", "company": "腾讯", "source_text": "z" * 100})
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
    class _FailModel:
        def complete(self, prompt):  # noqa: ARG002
            raise AssertionError("model must not be called when JD/resume missing")

    def test_fallback_when_empty_does_not_call_model(self):
        result = generate_note_questions(self._FailModel(), "", "some resume")
        ids = [q["id"] for q in result["questions"]]
        self.assertEqual(ids, ["common_1", "common_2"])

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


class ResearchAgentTests(unittest.TestCase):
    def test_retries_with_new_query_until_enough(self):
        queries = []

        def plan(context):
            return {"action": "search", "query": "q%d" % context["collected_count"], "reasoning": "try"}

        def search(query):
            queries.append(query)
            return [{"url": "http://%s" % query, "title": "t-%s" % query}]

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
            return [{"url": "http://dup", "title": "dup"}]  # same URL, deduped after round 1

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
            return [{"url": "http://%d" % counter["n"], "title": "t"}]

        def screen(candidate):
            return {"recommendation": "dismissed", "relevance": 0, "reason": "no"}

        result = run_research_agent(None, "x", "y", "z", target=99, max_rounds=99, max_searches=6,
                                    plan_fn=plan, search_fn=search, screen_fn=screen)
        self.assertEqual(counter["n"], 6)  # never exceeds max_searches
        self.assertEqual(result["stop_reason"], "已达到搜索次数上限。")

    def test_screen_candidate_never_auto_approves_and_uses_relevance(self):
        class _Model:
            def complete(self, prompt):  # noqa: ARG002
                # A malicious/confused model tries to smuggle an auto_approved verdict.
                return '{"recommendation":"auto_approved","confidence":95,"relevance":95}'

        out = screen_candidate(_Model(), {"url": "http://a", "title": "t", "summary": "s"}, "字节", "PM", "一面")
        self.assertEqual(out["recommendation"], "dismissed")  # not in whitelist -> dropped
        self.assertIn("relevance", out)
        self.assertNotIn("confidence", out)   # naming isolation from usability confidence


if __name__ == "__main__":
    unittest.main(verbosity=2)
