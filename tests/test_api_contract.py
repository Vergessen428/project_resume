"""HTTP-level contract tests for the local single-user API."""

import json
import os
import sys
import tempfile
import time
import threading
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))

import web_app
from core.interview_store import InterviewStore
from core.memory_override_store import MemoryOverrideStore
from core.research_store import ResearchStore
from core.resume_store import ResumeStore
from core.data_lifecycle import RECOVERY_MARKER_NAME, create_backup
from core.task_store import TaskRegistry


class ApiContractTests(unittest.TestCase):
    class ProbeHandler(web_app.AssistantHandler):
        """Call the production route methods without binding a socket."""

        def __init__(self, path, payload=None):
            self.path = path
            self.payload = payload
            self.responses = []

        def has_api_access(self):
            return True

        def require_write(self):
            return True

        def read_json_body(self):
            return self.payload

        def send_json(self, payload, status=200):
            self.responses.append((status, payload))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.interviews = InterviewStore(os.path.join(self.tmp.name, "interviews.json"))
        self.resumes = ResumeStore(os.path.join(self.tmp.name, "resumes.json"))
        self.research = ResearchStore(os.path.join(self.tmp.name, "research.json"))
        self.overrides = MemoryOverrideStore(os.path.join(self.tmp.name, "memory_overrides.json"))
        self.interview = self.interviews.create({
            "company": "示例公司",
            "role": "产品经理",
            "transcript": "面试记录：我负责拆解需求并推进上线。",
        })
        self.source = self.research.create({
            "title": "公开候选",
            "url": "https://www.xiaohongshu.com/explore/demo",
            "status": "candidate",
        })
        self.patches = [
            patch.object(web_app, "STORE", self.interviews),
            patch.object(web_app, "RESUME_STORE", self.resumes),
            patch.object(web_app, "RESEARCH_STORE", self.research),
            patch.object(web_app, "MEMORY_OVERRIDES", self.overrides),
            patch.object(web_app, "DATA_ROOT", self.tmp.name),
            patch.object(web_app, "TASKS", TaskRegistry(max_workers=1, max_attempts=2)),
            patch.dict(os.environ, {"APP_ACCESS_TOKEN": ""}, clear=False),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_public_bind_requires_access_token_outside_demo_mode(self):
        with patch.object(web_app, "DEMO_MODE", False), patch.dict(os.environ, {"APP_ACCESS_TOKEN": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                web_app.validate_bind_security("0.0.0.0")

    def test_public_bind_is_allowed_with_token_or_demo_mode(self):
        with patch.object(web_app, "DEMO_MODE", False), patch.dict(os.environ, {"APP_ACCESS_TOKEN": "local-secret"}, clear=False):
            web_app.validate_bind_security("0.0.0.0")
        with patch.object(web_app, "DEMO_MODE", True), patch.dict(os.environ, {"APP_ACCESS_TOKEN": ""}, clear=False):
            web_app.validate_bind_security("0.0.0.0")

    def test_loopback_bind_does_not_require_access_token(self):
        with patch.object(web_app, "DEMO_MODE", False), patch.dict(os.environ, {"APP_ACCESS_TOKEN": ""}, clear=False):
            web_app.validate_bind_security("127.0.0.1")

    def request(self, method, path, payload=None):
        handler = self.ProbeHandler(path, payload)
        if method == "GET":
            web_app.AssistantHandler.do_GET(handler)
        elif method == "POST":
            web_app.AssistantHandler.do_POST(handler)
        elif method == "PATCH":
            web_app.AssistantHandler.do_PATCH(handler)
        elif method == "PUT":
            web_app.AssistantHandler.do_PUT(handler)
        else:
            raise AssertionError("unsupported test method")
        self.assertEqual(len(handler.responses), 1, path)
        return handler.responses[0]

    def test_read_contracts_expose_structured_memory_and_retention(self):
        for path, required in (
            ("/api/interviews", {"ok", "interviews"}),
            ("/api/research", {"ok", "research", "stats"}),
            ("/api/operations", {"ok", "events", "summary"}),
            ("/api/growth-memory", {"ok", "memory"}),
            ("/api/growth-memory/replay", {"ok", "memory", "replay"}),
            ("/api/memory/overrides/audit", {"ok", "events"}),
            ("/api/data/retention", {"ok", "policy"}),
            ("/api/export", {"ok", "export_version", "interviews", "resumes", "research", "memory_overrides", "memory_override_events"}),
            ("/api/recovery", {"ok", "recovery"}),
        ):
            status, body = self.request("GET", path)
            self.assertEqual(status, 200, path)
            self.assertTrue(required.issubset(body), path)
        status, body = self.request("GET", "/api/data/retention")
        self.assertEqual(status, 200)
        self.assertIn("automatic", body["policy"])
        self.assertFalse(body["policy"]["automatic"])

    def test_demo_interview_route_creates_a_complete_reviewed_record(self):
        status, body = self.request("POST", "/api/interviews/demo", {})
        self.assertEqual(status, 201)
        self.assertTrue(body["ok"])
        self.assertIn("review", body["interview"])
        self.assertEqual(body["interview"]["review"]["schema_version"], "2.1")
        self.assertEqual(body["interview"]["review"]["score_summary"]["coach_score"], 60)

    def test_status_and_retention_contracts_require_their_gates(self):
        status, body = self.request("POST", "/api/research/%s/status" % self.source["id"], {"status": "auto_approved"})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        status, body = self.request("POST", "/api/research/%s/status" % self.source["id"], {"status": "approved"})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

        status, body = self.request("POST", "/api/data/retention", {"retention_days": 30})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])

        status, body = self.request("POST", "/api/data/retention", {"retention_days": 30, "confirm": True})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIn("cleared", body["retention"])

    def test_memory_governance_revert_requires_confirmation_and_restores_previous_label(self):
        self.overrides.upsert("gap", "旧标签", False)
        self.overrides.upsert("gap", "新标签", True)
        target = self.overrides.events()[0]
        status, body = self.request("POST", "/api/memory/overrides/audit/%s/revert" % target["id"], {})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        status, body = self.request("POST", "/api/memory/overrides/audit/%s/revert" % target["id"], {"confirm": True})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["event"]["action"], "revert")
        self.assertEqual(self.overrides.list()["gap"]["title"], "旧标签")
        self.assertFalse(self.overrides.list()["gap"]["ignored"])

    def test_public_health_and_backup_contracts_do_not_leak_local_paths(self):
        backup = create_backup(self.tmp.name, {
            "interviews": [],
            "resumes": [],
            "research": [],
            "memory_overrides": {},
        })
        status, body = self.request("GET", "/api/backups")
        self.assertEqual(status, 200)
        self.assertNotIn("path", body["backups"][0])
        status, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertNotIn(self.tmp.name, json.dumps(body, ensure_ascii=False))
        self.assertIn("tasks", body)
        self.assertIn("operations", body)
        status, body = self.request("POST", "/api/backup", {})
        self.assertEqual(status, 201)
        self.assertNotIn("path", body["backup"])
        self.assertNotEqual(backup["backup_id"], "")

    def test_api_rate_limit_is_bounded_and_health_probe_is_exempt(self):
        with patch.dict(os.environ, {"APP_RATE_LIMIT_PER_MINUTE": "1"}, clear=False):
            web_app._request_buckets.clear()
            status, body = self.request("GET", "/api/recovery")
            self.assertEqual(status, 200)
            self.assertTrue(body["ok"])
            status, body = self.request("GET", "/api/recovery")
            self.assertEqual(status, 429)
            self.assertFalse(body["ok"])
            status, body = self.request("GET", "/healthz")
            self.assertEqual(status, 200)
            self.assertTrue(body["ok"])
        web_app._request_buckets.clear()

    def test_manual_research_route_rejects_non_public_host(self):
        status, body = self.request("POST", "/api/research", {
            "title": "外部候选",
            "url": "https://example.com/post",
            "source_text": "原帖正文 " * 30,
        })
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertEqual(self.research.list()[0]["id"], self.source["id"])

    def test_discovery_route_exposes_bounded_fetch_boundary_and_query_path(self):
        candidates = [{
            "url": "https://www.xiaohongshu.com/explore/demo",
            "title": "公开候选",
            "search_query": "site:xiaohongshu.com/explore 示例公司 产品经理 面经",
            "fetch_status": "not_attempted",
        }]
        with patch.object(web_app, "build_model", return_value=object()), patch.object(
            web_app, "discover_public_sources", return_value=candidates
        ):
            status, body = self.request("POST", "/api/research/discover", {
                "company": "示例公司",
                "role": "产品经理",
                "round_name": "一面",
                "topic": "指标",
                "platform": "xiaohongshu",
            })
        self.assertEqual(status, 200)
        meta = body["search_meta"]
        self.assertEqual(meta["mode"], "public_discovery_with_bounded_fetch")
        self.assertTrue(meta["auto_fetch"])
        self.assertEqual(meta["fetch_status_counts"], {"not_attempted": 1})
        self.assertIn("site:xiaohongshu.com/explore", meta["queries_tried"][0])

    def test_note_questions_report_research_context_boundary(self):
        with patch.object(web_app, "build_model", return_value=object()), patch.object(
            web_app, "generate_note_questions", return_value={"questions": [{"id": "common_1", "question": "问题"}]}
        ):
            status, body = self.request("POST", "/api/note-questions", {
                "job_description": "负责指标设计和跨团队推进，要求根据数据验证方案。",
                "resume_context": "做过一个增长项目，负责需求拆解和上线复盘。",
                "research_context": [{"title": "公开候选", "research_id": "unbound-demo"}],
            })
        self.assertEqual(status, 200)
        self.assertEqual(body["research_meta"]["provided_count"], 1)
        self.assertEqual(body["research_meta"]["approved_count"], 0)
        self.assertEqual(body["research_meta"]["mode"], "jd_and_research")
        self.assertIn("不进入本场表现证据", body["research_meta"]["note"])

    def test_agent_route_can_reuse_recent_local_candidates_without_model_call(self):
        query = "site:xiaohongshu.com/explore 示例公司 产品经理 一面 指标 面经"
        for index in range(3):
            self.research.create({
                "title": "缓存候选 %s" % index,
                "url": "https://www.xiaohongshu.com/explore/cached-%s" % index,
                "platform_id": "xiaohongshu",
                "search_query": query,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            })
        with patch.object(web_app, "build_model", side_effect=AssertionError("cache should avoid model")):
            status, body = self.request("POST", "/api/research/agent", {
                "company": "示例公司",
                "role": "产品经理",
                "round_name": "一面",
                "topic": "指标",
                "platform": "xiaohongshu",
            })
        self.assertEqual(status, 200)
        self.assertTrue(body["search_meta"]["cache_hit"])
        self.assertEqual(body["trace"][0]["action"], "cache")

    def test_agent_request_derives_search_topic_from_jd_analysis(self):
        result = {
            "collected": [],
            "trace": [],
            "stop_reason": "测试",
            "found_enough": False,
            "search_meta": {},
        }
        with patch.object(web_app, "build_model", return_value=object()), patch.object(
            web_app, "run_research_agent", return_value=result
        ) as run_agent, patch.object(
            web_app, "persist_agent_candidates", return_value={"persisted": [], "assessed": [], "skipped": []}
        ):
            web_app.run_research_agent_request({
                "company": "示例公司",
                "role": "产品经理",
                "round_name": "一面",
                "topic": "",
                "job_description": "负责增长指标和实验设计的产品经理岗位。",
                "jd_analysis": {"search_topics": ["增长指标"], "interview_focus": ["归因验证"]},
                "platform": "xiaohongshu",
            })
        self.assertIn("增长指标", run_agent.call_args.args[4])
        self.assertIn("归因验证", run_agent.call_args.args[4])

    def test_persist_agent_candidates_upgrades_empty_shell_record_and_reassesses(self):
        fetched_text = "自动读取到的公开正文，包含具体轮次、指标追问和项目取舍。" * 20
        assessment = {
            "recommendation": "needs_review",
            "confidence": 72,
            "summary": "正文已读取，仍需确认来源真实性。",
            "claims": [],
            "question_leads": [],
            "credibility_signals": [],
            "concerns": ["自动读取未人工确认"],
            "review_reason": "测试",
        }
        with patch.object(web_app, "assess_public_source", return_value=assessment) as assess:
            result = web_app.persist_agent_candidates(object(), [{
                "url": self.source["url"],
                "title": "更新后的公开候选",
                "source_text": fetched_text,
                "provenance_status": "auto_fetched_unverified",
                "fetch_status": "fetched_metadata",
            }])
        stored = self.research.get(self.source["id"])
        self.assertEqual(stored["status"], "needs_review")
        self.assertEqual(stored["source_text"], fetched_text[:18000])
        self.assertEqual(len(result["assessed"]), 1)
        assess.assert_called_once()

    def test_persist_agent_candidates_never_overwrites_existing_manual_excerpt(self):
        manual = self.research.create({
            "title": "人工摘录",
            "url": "https://www.xiaohongshu.com/explore/manual",
            "source_text": "人工摘录正文 " * 30,
        })
        original = self.research.get(manual["id"])["source_text"]
        result = web_app.persist_agent_candidates(object(), [{
            "url": manual["url"],
            "title": "自动读取版本",
            "source_text": "自动正文 " * 40,
            "provenance_status": "auto_fetched_unverified",
        }])
        self.assertEqual(self.research.get(manual["id"])["source_text"], original)
        self.assertEqual(result["assessed"], [])

    def test_async_agent_exposes_status_and_result(self):
        result = {
            "collected": [],
            "persisted": [],
            "assessed": [],
            "skipped": [],
            "trace": [],
            "stop_reason": "测试完成",
            "found_enough": False,
            "search_meta": {"cache_hit": False},
        }
        with patch.object(web_app, "run_research_agent_request", return_value=result):
            status, body = self.request("POST", "/api/research/agent", {
                "company": "示例公司",
                "role": "产品经理",
                "async": True,
            })
        self.assertEqual(status, 202)
        task_id = body["task"]["id"]
        for _ in range(50):
            status, task_body = self.request("GET", "/api/tasks/%s" % task_id)
            self.assertEqual(status, 200)
            if task_body["task"]["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertEqual(task_body["task"]["status"], "succeeded")
        self.assertEqual(task_body["task"]["result"]["stop_reason"], "测试完成")
        self.assertNotIn("company", json.dumps(task_body, ensure_ascii=False))

    def test_async_review_exposes_status_and_result(self):
        result = {"interview": {"id": self.interview["id"], "review": {"schema_version": "2.1"}}}
        with patch.object(web_app, "run_review_request", return_value=result):
            status, body = self.request("POST", "/api/interviews/%s/review" % self.interview["id"], {"async": True})
        self.assertEqual(status, 202)
        task_id = body["task"]["id"]
        for _ in range(50):
            status, task_body = self.request("GET", "/api/tasks/%s" % task_id)
            if task_body["task"]["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertEqual(task_body["task"]["status"], "succeeded")
        self.assertEqual(task_body["task"]["result"]["interview"]["id"], self.interview["id"])

    def test_async_transcription_owns_temporary_file_until_worker_finishes(self):
        class MultipartHandler(self.ProbeHandler):
            def read_multipart(self, *_args):
                return {
                    "consent": SimpleNamespace(text="true"),
                    "async": SimpleNamespace(text="true"),
                    "audio": SimpleNamespace(filename="clip.mp3", content_type="audio/mpeg", value=b"audio-bytes"),
                }

        handler = MultipartHandler("/api/transcribe")
        with patch.object(web_app, "build_model", return_value=object()), patch.object(
            web_app, "transcribe_audio", return_value={"transcript": "异步转写结果", "language": "zh", "notes": ""}
        ):
            web_app.AssistantHandler.do_POST(handler)
        self.assertEqual(handler.responses[0][0], 202)
        task_id = handler.responses[0][1]["task"]["id"]
        for _ in range(50):
            status, task_body = self.request("GET", "/api/tasks/%s" % task_id)
            if task_body["task"]["status"] == "succeeded":
                break
            time.sleep(0.01)
        self.assertEqual(task_body["task"]["result"]["transcription"]["transcript"], "异步转写结果")

    def test_task_cancel_route_cancels_queued_work(self):
        started = threading.Event()
        release = threading.Event()
        blocker = web_app.TASKS.submit("blocker", lambda: (started.set(), release.wait(1), {})[2])
        self.assertTrue(started.wait(1))
        queued = web_app.TASKS.submit("queued", lambda: {})
        status, body = self.request("POST", "/api/tasks/%s/cancel" % queued["id"], {})
        self.assertEqual(status, 202)
        self.assertEqual(body["task"]["status"], "cancelled")
        release.set()
        for _ in range(50):
            if web_app.TASKS.get(blocker["id"])["status"] == "succeeded":
                break
            time.sleep(0.01)

    def test_candidate_import_auto_fills_public_excerpt_without_approving_source(self):
        candidate = {
            "title": "自动读取候选",
            "url": "https://www.xiaohongshu.com/explore/auto-fill",
            "platform": "小红书",
            "platform_id": "xiaohongshu",
        }
        enriched = dict(candidate)
        enriched.update({
            "source_text": "公开页面可见正文，包含面试题目、项目追问和指标讨论。" * 12,
            "fetch_status": "fetched_metadata",
            "fetch": {"fetch_status": "fetched_metadata", "fetch_reason": "已读取公开页面"},
        })
        with patch.object(web_app, "enrich_public_candidate", return_value=enriched):
            status, body = self.request("POST", "/api/research/candidate", {"candidate": candidate})
        self.assertEqual(status, 201)
        self.assertFalse(body["existing"])
        self.assertEqual(body["research"]["status"], "candidate")
        self.assertGreaterEqual(len(body["research"]["source_text"]), 80)
        self.assertEqual(body["research"]["fetch_status"], "fetched_metadata")
        self.assertIn("自动读取", body["research"]["notes"])

    def test_temporary_cleanup_failure_cannot_mask_response(self):
        path = os.path.join(self.tmp.name, "temporary-upload")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("temporary")
        with patch.object(web_app.os, "remove", side_effect=OSError("busy")):
            web_app._remove_temporary_file(path)
        self.assertTrue(os.path.exists(path))

    def test_stale_upload_cleanup_is_scoped_to_known_prefixes(self):
        temporary_root = os.path.join(self.tmp.name, "temporary_uploads")
        os.makedirs(temporary_root, exist_ok=True)
        stale_audio = os.path.join(temporary_root, "autumn-audio-stale.mp3")
        stale_resume = os.path.join(temporary_root, "autumn-resume-stale.pdf")
        unrelated = os.path.join(temporary_root, "keep-this.txt")
        for path in (stale_audio, stale_resume, unrelated):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("temporary")
        removed = web_app.cleanup_stale_uploads()
        self.assertEqual(removed, {"audio": 1, "resume": 1})
        self.assertFalse(os.path.exists(stale_audio))
        self.assertFalse(os.path.exists(stale_resume))
        self.assertTrue(os.path.exists(unrelated))

    def test_corrupt_store_returns_recoverable_service_error(self):
        with open(self.interviews.path, "w", encoding="utf-8") as handle:
            handle.write("{broken")
        status, body = self.request("GET", "/api/interviews")
        self.assertEqual(status, 503)
        self.assertFalse(body["ok"])
        self.assertIn("恢复备份", body["error"])

    def test_training_attempt_route_enforces_phase_contract(self):
        self.interviews.save_review(self.interview["id"], {"action_plan": [{"id": "a1", "action": "练习"}]})
        status, body = self.request("POST", "/api/interviews/%s/actions/a1/attempts" % self.interview["id"], {"phase": "rewrite", "response": "重写"})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        status, body = self.request("POST", "/api/interviews/%s/actions/a1/attempts" % self.interview["id"], {"phase": "pre_test", "response": "原始回答"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["interview"]["review"]["action_plan"][0]["training_progress"]["pre_test"])

    def test_action_pass_requires_post_test(self):
        self.interviews.save_review(self.interview["id"], {"action_plan": [{"id": "a1", "action": "练习"}]})
        status, body = self.request(
            "PATCH",
            "/api/interviews/%s/actions/a1" % self.interview["id"],
            {"done": True, "acceptance_status": "passed"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertIn("后测", body["error"])

    def test_metadata_update_remains_available_after_transcript_cleanup(self):
        self.interviews.clear_transcripts()
        status, body = self.request(
            "PUT",
            "/api/interviews/%s" % self.interview["id"],
            {
                "company": "示例公司",
                "role": "产品经理",
                "outcome": "passed",
                "outcome_source": "self_reported",
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["interview"]["transcript"], "")
        self.assertEqual(body["interview"]["outcome"], "passed")
        self.assertEqual(body["interview"]["outcome_source"], "self_reported")

    def test_research_context_reconciliation_downgrades_removed_source(self):
        snapshot = [{"research_id": self.source["id"], "status": "approved", "title": "候选"}]
        self.research.delete(self.source["id"])
        reconciled = web_app.reconcile_research_context(snapshot)
        self.assertEqual(reconciled[0]["status"], "dismissed")
        self.assertEqual(reconciled[0]["source_state"], "source_removed")
        self.assertFalse(reconciled[0]["citation_allowed"])

    def test_research_context_reconciliation_rejects_unbound_approved_snapshot(self):
        reconciled = web_app.reconcile_research_context([{"status": "approved", "title": "客户端伪造"}])
        self.assertEqual(reconciled[0]["status"], "candidate")
        self.assertEqual(reconciled[0]["source_state"], "source_unbound")
        self.assertFalse(reconciled[0]["citation_allowed"])

    def test_review_route_returns_normalised_v21_contract(self):
        class ReviewModel:
            active_provider = "contract-test"
            model = "contract-model"

            def complete(self, _prompt):
                return json.dumps({
                    "summary": "只返回一个带证据边界的测试复盘。",
                    "skill_diagnosis": [{
                        "skill_id": "metrics_experiment",
                        "score": 5,
                        "dimensions": [{
                            "id": "attribution",
                            "score": 5,
                            "status": "missing",
                            "evidence": "",
                        }],
                    }],
                }, ensure_ascii=False)

        with patch.object(web_app, "build_model", return_value=ReviewModel()):
            status, body = self.request(
                "POST",
                "/api/interviews/%s/review" % self.interview["id"],
                {"redact_company": False},
            )
        self.assertEqual(status, 200)
        review = body["interview"]["review"]
        self.assertEqual(review["schema_version"], "2.1")
        self.assertEqual(len(review["skill_diagnosis"]), 6)
        self.assertEqual(review["scored_by"]["provider"], "contract-test")
        self.assertEqual(review["scored_by"]["model"], "contract-model")
        metrics = next(item for item in review["skill_diagnosis"] if item["skill_id"] == "metrics_experiment")
        self.assertIsNone(metrics["score"])
        self.assertIsNone(metrics["exact_score"])
        self.assertIn("evidence_coverage", review["review_quality"])
        self.assertEqual(review["score_summary"]["coach_score"], 0)

    def test_restore_failure_rolls_back_all_local_stores(self):
        baseline_interviews = self.interviews.records()
        baseline_research = self.research.list()
        backup = create_backup(self.tmp.name, {
            "interviews": [{"id": "replacement"}],
            "resumes": [],
            "research": [{"id": "replacement-source"}],
            "memory_overrides": {"gap": {"gap_key": "gap"}},
        })
        with patch.object(self.research, "replace_all", side_effect=[RuntimeError("disk error"), None]):
            status, body = self.request("POST", "/api/backup/restore/%s" % backup["backup_id"], {"confirm": True})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertEqual(self.interviews.records(), baseline_interviews)
        self.assertEqual(self.research.list(), baseline_research)

    def test_backup_restore_preserves_memory_override_event_history(self):
        self.overrides.upsert("gap", "原始标签", False)
        events = list(reversed(self.overrides.events()))
        backup = create_backup(self.tmp.name, {
            "interviews": self.interviews.records(),
            "resumes": [],
            "research": self.research.list(),
            "memory_overrides": self.overrides.list(),
            "memory_override_events": events,
        })
        self.overrides.upsert("gap", "后来标签", True)
        status, body = self.request("POST", "/api/backup/restore/%s" % backup["backup_id"], {"confirm": True})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(self.overrides.list()["gap"]["title"], "原始标签")
        self.assertEqual(self.overrides.events()[0]["title"], "原始标签")

    def test_restore_rollback_failure_leaves_startup_recovery_marker(self):
        backup = create_backup(self.tmp.name, {
            "interviews": [{"id": "replacement"}],
            "resumes": [],
            "research": [{"id": "replacement-source"}],
            "memory_overrides": {},
        })
        with patch.object(self.research, "replace_all", side_effect=[RuntimeError("disk error"), RuntimeError("rollback error")]):
            status, body = self.request("POST", "/api/backup/restore/%s" % backup["backup_id"], {"confirm": True})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        marker = os.path.join(self.tmp.name, RECOVERY_MARKER_NAME)
        self.assertTrue(os.path.exists(marker))
        status, body = self.request("GET", "/api/recovery")
        self.assertEqual(status, 200)
        self.assertTrue(body["recovery"]["recovery_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
