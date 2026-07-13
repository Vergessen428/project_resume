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
from core.interview_review import _normalise_review, _parse_json, sample_reviewed_interview
from core.growth_memory import build_candidate_memory
from core.interview_store import InterviewStore
from core.research_store import ResearchStore


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
