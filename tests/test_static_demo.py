"""Source-level smoke checks for the static demo and browser wiring."""

from html.parser import HTMLParser
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(ROOT, *parts), "r", encoding="utf-8") as handle:
        return handle.read()


class LocalAssetParser(HTMLParser):
    """Collect local assets so static-host root paths cannot silently drift."""

    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        value = attrs.get("src") if tag == "script" else attrs.get("href")
        if value:
            self.assets.append(value)


class StaticDemoSmokeTests(unittest.TestCase):
    def test_static_host_asset_manifest_is_self_contained(self):
        html = read("static_demo", "index.html")
        parser = LocalAssetParser()
        parser.feed(html)
        self.assertEqual(
            set(parser.assets),
            {"/styles.css", "/demo_data.js", "/app.js"},
        )
        for asset in parser.assets:
            self.assertTrue(asset.startswith("/"), asset)
            self.assertNotIn("://", asset)
            asset_path = os.path.join(ROOT, "static_demo", asset.lstrip("/"))
            self.assertTrue(os.path.isfile(asset_path), asset)

    def test_deployment_contracts_match_current_entrypoints(self):
        render = read("render.yaml")
        dockerfile = read("Dockerfile")
        workflow = read(".github", "workflows", "test.yml")
        hf_readme = read("static_demo", "README.md")
        root_readme = read("README.md")

        self.assertIn("startCommand: \"python3 -B app/web_app.py --host 0.0.0.0 --port $PORT\"", render)
        self.assertIn("healthCheckPath: /healthz", render)
        self.assertIn('CMD ["python3", "-B", "app/web_app.py", "--host", "0.0.0.0", "--port", "7860"]', dockerfile)
        self.assertIn("EXPOSE 7860", dockerfile)
        self.assertIn("python -m app.core.evaluation_harness", workflow)
        self.assertIn("scripts/static_demo_http_smoke.py", workflow)
        self.assertIn("sdk: static", hf_readme)
        self.assertIn("https://huggingface.co/spaces/", root_readme)
        for filename in (
            "01-review-workspace.png",
            "02-review-output.png",
            "03-research-library.png",
            "04-growth-report.png",
        ):
            self.assertIn(f"docs/screenshots/{filename}", root_readme)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "docs", "screenshots", filename)))

    def test_demo_data_is_separate_and_loaded_before_app(self):
        html = read("static_demo", "index.html")
        self.assertIn('<script src="/demo_data.js"></script>', html)
        self.assertIn('<script src="/app.js"></script>', html)
        self.assertLess(html.index("/demo_data.js"), html.index("/app.js"))
        self.assertIn("AUTUMN_DEMO_DATA", read("static_demo", "demo_data.js"))
        self.assertIn("skill_diagnosis", read("static_demo", "demo_data.js"))
        self.assertNotIn("const review = {", read("static_demo", "app.js"))

    def test_static_actions_are_explicitly_read_only(self):
        app = read("static_demo", "app.js")
        self.assertIn("function demoWrite", app)
        self.assertIn("function demoDataAction", app)
        self.assertIn("demo_only: true", app)
        self.assertIn("未真实联网、读取原帖或写入资料库", app)
        self.assertIn("source_kind: \"demo_synthetic\"", read("static_demo", "demo_data.js"))
        self.assertIn("manual_check_required", read("static_demo", "demo_data.js"))
        self.assertIn("persisted", app)
        self.assertIn("relevance_breakdown", read("static_demo", "demo_data.js"))
        self.assertIn("question_leads", read("static_demo", "demo_data.js"))
        self.assertIn("出题线索", app)
        self.assertIn("outcome.interpretation", app)
        self.assertIn("结果为自报训练反馈，不是招聘预测", read("static_demo", "app.js"))

    def test_dynamic_jd_flow_passes_analysis_and_auto_ingests_sources(self):
        app = read("app", "web", "app.js")
        self.assertIn("jd_analysis: app.jdAnalysis", app)
        self.assertIn("job_description: field('job_description').value", app)
        self.assertIn("autoSearchFromJd", app)
        self.assertIn("data.persisted || data.collected", app)
        self.assertIn("persist_agent_candidates", read("app", "web_app.py"))
        self.assertEqual(app.count("function renderDiscovery("), 1)
        self.assertIn("reconcile_research_context", read("app", "web_app.py"))
        self.assertIn("renderTaskStatus", app)
        self.assertIn("/api/tasks/", app)
        self.assertIn("/api/tasks/${task.id}/cancel", app)
        self.assertIn("标题、链接、正文和查询元数据已回填", app)
        self.assertIn("公开页正文不足，请补充原帖摘录", app)
        self.assertIn("job_description: field('job_description').value", app)

    def test_search_controls_explain_preview_vs_agent_ingest(self):
        for path in (("app", "web", "index.html"), ("static_demo", "index.html")):
            html = read(*path)
            self.assertIn("仅搜索候选预览", html)
            self.assertIn("Agent 自动调研并收录", html)
        static_app = read("static_demo", "app.js")
        self.assertIn("job_description: field('job_description').value", static_app)
        self.assertIn("jd_analysis: app.jdAnalysis", static_app)

    def test_demo_review_has_all_six_skills_and_calibrated_summary(self):
        data = read("static_demo", "demo_data.js")
        skill_dimensions = {
            "product_sense": ("user_problem", "goal_definition", "tradeoff", "prioritization"),
            "story_ownership": ("scope", "decision", "collaboration", "result_learning"),
            "metrics_experiment": ("definition", "decomposition", "attribution", "experiment_quantify"),
            "execution_collaboration": ("planning", "alignment", "resource_tradeoff", "closure"),
            "structured_communication": ("structure", "directness", "precision", "probe_response"),
            "business_context": ("jd_link", "user_business", "market_context", "role_fit"),
        }
        for skill_id, dimension_ids in skill_dimensions.items():
            self.assertIn(f'skill_id: "{skill_id}"', data)
            for dimension_id in dimension_ids:
                self.assertIn(f'id: "{dimension_id}"', data)
        self.assertIn("coach_score: 60", data)
        self.assertIn("evidence_coverage: 0.63", data)
        self.assertIn("scored_by", data)
        self.assertIn("outcome_signal", data)
        self.assertIn('outcome_source: "self_reported"', data)
        self.assertIn("outcome_source: data.outcome ? 'self_reported' : ''", read("static_demo", "app.js"))
        self.assertIn('evidence_quality: "verified"', data)
        self.assertIn('skills: ["metrics_experiment", "structured_communication"]', data)
        self.assertIn('skill_id: "business_context", skill_name: "业务与岗位理解", score: null, exact_score: null', data)
        self.assertIn('memory_version: "1.3"', data)
        self.assertIn('algorithm_version: "growth-memory-1.3"', data)
        self.assertIn("question_leads", data)
        self.assertIn("search_meta", data)
        self.assertIn("relevance_breakdown", data)
        self.assertIn('provenance_status: "manual_check_required"', data)
        self.assertIn("静态演示不联网", data)
        self.assertIn("这是静态 Demo", data)
        self.assertIn("action_key", data)
        self.assertIn("source_skill_ids", data)
        self.assertIn("source_gap_ids", data)
        self.assertIn("source_interview_id", data)

    def test_search_controls_explain_preview_vs_agent_ingest(self):
        for path in (("app", "web", "app.js"), ("static_demo", "app.js")):
            script = read(*path)
            self.assertIn("仅搜索候选预览", script)
            self.assertIn("Agent 自动调研并收录", script)
            self.assertIn("jd_analysis: app.jdAnalysis", script)
        dynamic = read("app", "web", "app.js")
        self.assertIn("async: true", dynamic)
        self.assertIn("waitForTask(accepted.task", dynamic)

    def test_discovery_ui_explains_that_agent_is_the_auto_fetch_path(self):
        app = read("app", "web", "app.js")
        static_app = read("static_demo", "app.js")
        self.assertIn("meta.mode === 'public_discovery_with_bounded_fetch'", app)
        self.assertIn("meta.demo_only", static_app)

    def test_responsive_and_lifecycle_controls_exist(self):
        html = read("static_demo", "index.html")
        css = read("static_demo", "styles.css")
        dynamic_html = read("app", "web", "index.html")
        self.assertIn('id="task-status"', dynamic_html)
        self.assertIn('id="cancel-task"', dynamic_html)
        self.assertIn('id="export-data"', html)
        self.assertIn('id="clear-transcripts"', html)
        self.assertIn('id="retention-preview"', html)
        self.assertIn('id="retention-apply"', html)
        self.assertIn("retention_days", read("app", "web_app.py"))
        self.assertIn("research-screening", read("app", "web", "app.js"))
        self.assertIn("research-screening", read("static_demo", "app.js"))
        self.assertIn("provenanceLabel", read("app", "web", "app.js"))
        self.assertIn("provenanceLabel", read("static_demo", "app.js"))
        self.assertIn("ensureJdResearchForQuestions", read("app", "web", "app.js"))
        self.assertIn("ensureJdResearchForQuestions", read("static_demo", "app.js"))
        self.assertIn("research_meta", read("app", "web", "app.js"))
        self.assertIn("note-research-meta", read("static_demo", "styles.css"))
        self.assertIn("provenance-badge", read("app", "web", "styles.css"))
        self.assertIn("provenance-badge", css)
        self.assertIn("question_leads", read("app", "web", "app.js"))
        self.assertIn("training_progress", read("static_demo", "app.js"))
        self.assertIn("下一场验证", read("app", "web", "app.js"))
        self.assertIn("completed_at", read("app", "web", "app.js"))
        self.assertIn("下一场验证", read("static_demo", "app.js"))
        self.assertIn("pre_test", read("app", "core", "interview_store.py"))
        self.assertIn("/api/growth-memory/replay", read("app", "web_app.py"))
        self.assertIn("override_events", read("app", "web_app.py"))
        self.assertIn("appendMemoryAudit", read("app", "web", "app.js"))
        self.assertIn("/api/memory/overrides/audit/", read("app", "web", "app.js"))
        self.assertIn("撤销", read("app", "web", "app.js"))
        self.assertIn("/api/memory/overrides/audit", read("app", "web_app.py"))
        self.assertIn("revert_event", read("app", "core", "memory_override_store.py"))
        self.assertIn("memory-audit-row", css)
        self.assertIn("/api/recovery", read("app", "web_app.py"))
        self.assertIn("recovery_required", read("app", "core", "data_lifecycle.py"))
        self.assertIn('"audit"', read("app", "core", "growth_memory.py"))
        self.assertIn("@media", css)
        self.assertIn("grid-template-columns", css)

    def test_browser_smoke_is_pinned_and_covers_runtime_contract(self):
        workflow = read(".github", "workflows", "test.yml")
        script = read("scripts", "browser_demo_smoke.mjs")
        self.assertIn("browser-smoke:", workflow)
        self.assertIn("playwright@1.52.0", workflow)
        self.assertIn("playwright install --with-deps chromium", workflow)
        self.assertIn("node scripts/browser_demo_smoke.mjs", workflow)
        for marker in (
            "#discover-platform",
            "xiaohongshu",
            "#agent-trace",
            "#note-questions-panel .note-question",
            "静态 Demo",
            "scrollWidth",
            "static-demo-mobile.png",
        ):
            self.assertIn(marker, script)

    def test_documentation_screenshots_are_real_png_assets(self):
        for filename in (
            "01-review-workspace.png",
            "02-review-output.png",
            "03-research-library.png",
            "04-growth-report.png",
        ):
            path = os.path.join(ROOT, "docs", "screenshots", filename)
            with open(path, "rb") as handle:
                payload = handle.read(32)
            self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"), filename)
            self.assertGreater(len(payload), 8, filename)

    def test_sensitive_information_warning_is_non_blocking_and_synced(self):
        dynamic_html = read("app", "web", "index.html")
        static_html = read("static_demo", "index.html")
        for html in (dynamic_html, static_html):
            self.assertIn('id="sensitive-warning"', html)
            self.assertIn('aria-live="polite"', html)
        dynamic_app = read("app", "web", "app.js")
        static_app = read("static_demo", "app.js")
        for app in (dynamic_app, static_app):
            self.assertIn("可能包含敏感信息", app)
            self.assertIn("SENSITIVE_PATTERNS", app)
            self.assertIn("此提示不代表完整脱敏", app)
        self.assertIn("updateSensitiveWarning();", dynamic_app)
        self.assertIn("updateSensitiveWarning();", static_app)
        self.assertIn("可能包含敏感信息提示", read("README.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
