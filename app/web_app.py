"""Local web application for the Autumn PM interview assistant."""

import argparse
import functools
import hmac
import ipaddress
import json
import mimetypes
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.audio_transcription import AudioTranscriptionError, extract_resume_file, transcribe_audio
from core.data_lifecycle import (
    DEFAULT_BACKUP_KEEP,
    clear_recovery_marker,
    create_backup,
    inspect_startup_recovery,
    list_backups,
    mark_recovery_required,
    normalise_backup_keep,
    read_backup,
)
from core.data_retention import apply_retention, normalise_retention_days, preview_retention
from core.growth_memory import build_candidate_memory
from core.interview_review import extract_job_description, generate_growth_report, generate_interview_review, generate_note_questions, sample_interview, sample_reviewed_interview
from core.interview_store import InterviewStore
from core.local_store import StoreDataError
from core.model_provider import build_model, load_dotenv
from core.multipart import parse_multipart
from core.memory_override_store import MemoryOverrideStore
from core.pm_skills import public_skills
from core.research_grounding import ResearchGroundingError, assess_public_source, build_search_query, build_search_queries, derive_research_topic, discover_public_sources, enrich_public_candidate, is_allowed_public_post_url, normalise_platform, run_research_agent
from core.research_store import ResearchStore
from core.resume_store import ResumeStore
from core.operational_log import OperationalLog
from core.task_store import TaskFailure, TaskRegistry


WEB_ROOT = os.path.join(PROJECT_ROOT, "web")
DATA_ROOT = os.path.realpath(os.environ.get("APP_DATA_DIR", os.path.join(PROJECT_ROOT, "data")))
STORE = InterviewStore(os.path.join(DATA_ROOT, "interviews.json"))
RESUME_STORE = ResumeStore(os.path.join(DATA_ROOT, "resumes.json"))
RESEARCH_STORE = ResearchStore(os.path.join(DATA_ROOT, "research.json"))
MEMORY_OVERRIDES = MemoryOverrideStore(os.path.join(DATA_ROOT, "memory_overrides.json"))
MAX_BODY_BYTES = 120000
MAX_AUDIO_BYTES = 50 * 1024 * 1024
MAX_RESUME_FILE_BYTES = 25 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/mp4", "audio/x-m4a", "audio/aac", "audio/ogg", "audio/webm"}
ALLOWED_RESUME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DEMO_MODE = os.environ.get("APP_DEMO_MODE", "").strip().lower() in {"1", "true", "yes"}
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_SECONDS = 60
DEFAULT_API_RATE_LIMIT = 120
API_RATE_WINDOW_SECONDS = 60
DEFAULT_RESEARCH_CACHE_SECONDS = 3600
DEFAULT_TASK_TIMEOUT_SECONDS = 900
_login_failures: Dict[str, Any] = {}
_login_lock = threading.Lock()
_request_buckets: Dict[str, list] = {}
_request_lock = threading.Lock()


def validate_bind_security(host: str) -> None:
    """Refuse an unauthenticated non-demo process on a non-loopback bind."""
    host = str(host or "").strip().lower().strip("[]")
    if host in {"localhost", "127.0.0.1", "::1"}:
        return
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        # A hostname other than localhost may resolve to a public or LAN
        # address, so require the same protection as an explicit public bind.
        is_loopback = False
    if is_loopback or DEMO_MODE or os.environ.get("APP_ACCESS_TOKEN", "").strip():
        return
    raise RuntimeError(
        "非本机绑定必须设置 APP_ACCESS_TOKEN；如仅展示静态 Demo，请设置 APP_DEMO_MODE=1。"
    )


def research_cache_seconds() -> int:
    try:
        value = int(os.environ.get("APP_RESEARCH_CACHE_SECONDS", DEFAULT_RESEARCH_CACHE_SECONDS))
    except (TypeError, ValueError):
        value = DEFAULT_RESEARCH_CACHE_SECONDS
    return max(0, min(86400, value))


def task_timeout_seconds() -> float:
    try:
        value = float(os.environ.get("APP_TASK_TIMEOUT_SECONDS", DEFAULT_TASK_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        value = DEFAULT_TASK_TIMEOUT_SECONDS
    return max(1.0, min(3600.0, value))


OP_LOG = OperationalLog(os.path.join(DATA_ROOT, "operations.jsonl"))
TASKS = TaskRegistry(
    path=os.path.join(DATA_ROOT, "tasks.json"),
    timeout_seconds=task_timeout_seconds(),
    event_sink=OP_LOG.emit,
)


def seed_demo_data() -> None:
    """In demo mode, make sure a visitor lands on a fully worked example."""
    if not DEMO_MODE:
        return
    if startup_recovery_status().get("recovery_required"):
        return
    if not STORE.records():
        sample = sample_reviewed_interview()
        review = sample.pop("review", None)
        created = STORE.create(sample)
        if review:
            STORE.save_review(created["id"], review)


def redact_company_for_model(value: Any, company: str) -> Any:
    """Best-effort replacement for the user-entered company name before model calls."""
    company = str(company or "").strip()
    if not company:
        return value
    if isinstance(value, str):
        return value.replace(company, "[目标公司]")
    if isinstance(value, list):
        return [redact_company_for_model(item, company) for item in value]
    if isinstance(value, dict):
        return {key: redact_company_for_model(item, company) for key, item in value.items()}
    return value


def _remove_temporary_file(path: str) -> None:
    """Best-effort cleanup that cannot replace the response with a cleanup error."""
    if not path or not os.path.isfile(path):
        return
    try:
        os.remove(path)
    except OSError:
        # The request already has a domain-specific result. Cleanup failure is
        # operational noise and must not turn a successful transcription into
        # a generic 502 or mask the original exception.
        return


def _temporary_upload_root() -> str:
    """Keep transient uploads under the app data boundary for crash cleanup."""
    root = os.path.join(DATA_ROOT, "temporary_uploads")
    os.makedirs(root, exist_ok=True)
    return root


def cleanup_stale_uploads() -> Dict[str, int]:
    """Remove only known upload prefixes left by a prior interrupted process."""
    root = _temporary_upload_root()
    prefixes = {"audio": "autumn-audio-", "resume": "autumn-resume-"}
    removed = {key: 0 for key in prefixes}
    for name in os.listdir(root):
        kind = next((key for key, prefix in prefixes.items() if name.startswith(prefix)), None)
        if kind is None:
            continue
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            os.remove(path)
            removed[kind] += 1
        except OSError:
            continue
    return removed


def _new_temporary_upload(prefix: str, suffix: str):
    return tempfile.NamedTemporaryFile(
        prefix=prefix,
        suffix=suffix,
        dir=_temporary_upload_root(),
        delete=False,
    )


# A crash can happen before a task's finally block runs. Clean only stale files
# at import/startup; do not call this from health probes while work is running.
cleanup_stale_uploads()


def _build_discovery_search_meta(
    platform: str,
    company: str,
    role: str,
    round_name: str,
    topic: str,
    candidates: Any,
) -> Dict[str, Any]:
    """Describe public discovery plus bounded page reads without implying verification."""
    rows = candidates if isinstance(candidates, list) else []
    queries = []
    status_counts: Dict[str, int] = {}
    failure_reasons = []
    for candidate in rows:
        if not isinstance(candidate, dict):
            continue
        query = str(candidate.get("search_query", "")).strip()
        if query and query not in queries:
            queries.append(query[:1000])
        status = str(candidate.get("fetch_status", "not_attempted")).strip() or "not_attempted"
        status_counts[status] = status_counts.get(status, 0) + 1
        fetched = candidate.get("fetch") if isinstance(candidate.get("fetch"), dict) else {}
        reason = str(fetched.get("fetch_reason", "")).strip()
        if reason and reason not in failure_reasons and "已读取公开页面" not in reason:
            failure_reasons.append(reason[:300])
    if not queries:
        queries = [build_search_query(company, role, round_name, topic, platform)]
    label = {"all": "全网", "xiaohongshu": "小红书", "nowcoder": "牛客"}[platform]
    return {
        "mode": "public_discovery_with_bounded_fetch",
        "auto_fetch": True,
        "platform": platform,
        "platform_label": label,
        "queries_tried": queries,
        "result_count": len(rows),
        "fetch_status_counts": status_counts,
        "failure_reasons": failure_reasons[:8],
        "empty_reason": (
            "未发现候选链接。已尝试公开搜索和白名单页面读取；可换查询词或手动打开原帖。"
            if not rows else ""
        ),
    }


def run_research_agent_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the research Agent without coupling it to an HTTP response."""
    company = str(payload.get("company", "")).strip()
    role = str(payload.get("role", "")).strip()
    round_name = str(payload.get("round_name", "")).strip()
    topic = derive_research_topic(
        payload.get("topic", ""),
        payload.get("jd_analysis"),
        payload.get("job_description", ""),
    )
    platform = normalise_platform(payload.get("platform"))
    if not company and not role and not topic:
        raise ValueError("请至少填写公司、岗位或搜索主题。")
    cache_ttl = research_cache_seconds()
    cache_queries = build_search_queries(company, role, round_name, topic, platform)
    cached = RESEARCH_STORE.recent_candidates_for_queries(
        cache_queries, platform=platform, ttl_seconds=cache_ttl, limit=3,
    )
    if len(cached) >= 3:
        return {
            "collected": cached,
            "persisted": cached,
            "assessed": [item for item in cached if item.get("assessment")],
            "skipped": [],
            "trace": [{"round": 0, "action": "cache", "reasoning": "命中本地研究缓存，未重复调用联网搜索。", "added": len(cached)}],
            "stop_reason": "已复用缓存中的近期候选资料。",
            "found_enough": True,
            "search_meta": {
                "platform": platform,
                "platform_label": {"all": "全网", "xiaohongshu": "小红书", "nowcoder": "牛客"}.get(platform, "全网"),
                "queries_tried": cache_queries,
                "result_count": len(cached),
                "fetch_status_counts": {},
                "failure_reasons": [],
                "empty_reason": "",
                "cache_hit": True,
                "cache_ttl_seconds": cache_ttl,
            },
        }
    model = build_model()
    result = run_research_agent(model, company, role, round_name, topic, platform=platform)
    persistence = persist_agent_candidates(model, result["collected"])
    result.setdefault("search_meta", {})["cache_hit"] = False
    result["search_meta"]["cache_ttl_seconds"] = cache_ttl
    return {
        "collected": result["collected"],
        "persisted": persistence["persisted"],
        "assessed": persistence["assessed"],
        "skipped": persistence["skipped"],
        "trace": result["trace"],
        "stop_reason": result["stop_reason"],
        "found_enough": result["found_enough"],
        "search_meta": result.get("search_meta", {}),
    }


def run_safe_task(runner, fallback: str) -> Dict[str, Any]:
    """Keep internal model/network exceptions out of task status responses."""
    try:
        return runner()
    except (ResearchGroundingError, RuntimeError, ValueError, AudioTranscriptionError) as exc:
        raise TaskFailure(str(exc)[:400] or fallback) from exc
    except Exception as exc:
        raise TaskFailure(fallback) from exc


def run_review_request(interview_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate and persist one review without coupling it to an HTTP response."""
    record = STORE.get(interview_id)
    if record is None:
        raise ValueError("未找到这场面试。")
    model = build_model()
    company = record.get("company", "")
    redact_company = payload.get("redact_company") is True
    review_record = redact_company_for_model(record, company) if redact_company else record
    research_context = RESEARCH_STORE.approved_for(company, record.get("role", "")) + reconcile_research_context(record.get("research_context", []))
    if redact_company:
        research_context = redact_company_for_model(research_context, company)
    review = generate_interview_review(
        model,
        review_record,
        research_context,
        build_candidate_memory(STORE.records(), MEMORY_OVERRIDES.list()),
    )
    return {"interview": STORE.save_review(interview_id, review)}



def validate_interview(payload: Dict[str, Any], require_transcript: bool = True) -> Optional[str]:
    if not str(payload.get("company", "")).strip():
        return "请填写公司名称。"
    if not str(payload.get("role", "")).strip():
        return "请填写投递岗位。"
    transcript = str(payload.get("transcript", "")).strip()
    if require_transcript and not transcript:
        return "请填写至少一段面试转写或面后速记。"
    return None


def validate_research(payload: Dict[str, Any]) -> Optional[str]:
    # Manual ingest and edits must obey the same public-source boundary as
    # search candidates; otherwise a pasted arbitrary URL could bypass it.
    candidate_error = validate_research_candidate(payload)
    if candidate_error:
        return candidate_error
    if len(str(payload.get("source_text", "")).strip()) < 80:
        return "请粘贴至少 80 个字的原帖正文摘录，避免 AI 只凭标题判断。"
    return None


def validate_research_candidate(payload: Dict[str, Any]) -> Optional[str]:
    if not str(payload.get("title", "")).strip():
        return "搜索候选缺少标题。"
    url = str(payload.get("url", "")).strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        return "搜索候选缺少完整 http(s) 链接。"
    if not is_allowed_public_post_url(url):
        return "搜索候选必须是白名单平台下的具体公开原帖链接。"
    return None


def reconcile_research_context(sources: Any) -> list:
    """Refresh persisted source status before a model sees an old snapshot.

    Interview records intentionally keep a small snapshot so they remain
    readable after a research record changes. The snapshot is historical
    context, not a permanent approval. When its source id is known, the
    current research gate wins; removed or downgraded sources remain available
    as question leads but lose citation eligibility.
    """
    result = []
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict):
            continue
        refreshed = dict(source)
        research_id = str(source.get("research_id", "")).strip()
        if not research_id:
            # A caller-provided snapshot is only a question lead until it is
            # bound to a ResearchStore record. Never trust status=approved
            # from an unbound JSON payload.
            refreshed["status"] = "candidate"
            refreshed["source_state"] = "source_unbound"
            refreshed["citation_allowed"] = False
        else:
            current = RESEARCH_STORE.get(research_id)
            if current is None:
                refreshed["status"] = "dismissed"
                refreshed["source_state"] = "source_removed"
                refreshed["citation_allowed"] = False
            elif not RESEARCH_STORE.is_usable_record(current):
                refreshed["status"] = str(current.get("status", "candidate"))[:30]
                refreshed["source_state"] = "source_not_usable"
                refreshed["citation_allowed"] = False
            else:
                refreshed["status"] = str(current.get("status", "approved"))[:30]
                refreshed["source_state"] = "source_currently_usable"
                refreshed["citation_allowed"] = True
                if isinstance(current.get("assessment"), dict):
                    refreshed["assessment"] = current["assessment"]
        result.append(refreshed)
    return result[:8]


def persist_agent_candidates(model: Any, candidates: Any) -> Dict[str, Any]:
    """Persist Agent output server-side so browser failure cannot lose the run."""
    persisted = []
    assessed = []
    skipped = []
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, dict):
            skipped.append({"reason": "候选格式无效。"})
            continue
        candidate = dict(candidate)
        error = validate_research_candidate(candidate)
        if error:
            skipped.append({"url": str(candidate.get("url", ""))[:2000], "reason": error})
            continue
        url = str(candidate.get("url", "")).strip()
        existing = next((item for item in RESEARCH_STORE.list() if item.get("url") == url), None)
        if existing:
            existing_text = str(existing.get("source_text", "")).strip()
            fetched_text = str(candidate.get("source_text", "")).strip()
            # A previous shell-only discovery may later return real public
            # text. Upgrade only an empty record; never overwrite a user's
            # manual excerpt with automatically fetched content.
            if not existing_text and len(fetched_text) >= 80:
                update_payload = {
                    key: candidate.get(key)
                    for key in (
                        "title", "url", "canonical_url", "platform", "platform_id", "company", "role",
                        "round_name", "topic", "published_date", "search_query", "source_kind",
                        "provenance_status", "retrieved_at", "fetched_at", "fetch_status", "fetch_reason",
                        "source_text", "comments_text", "tags", "notes", "screening",
                    )
                    if key in candidate
                }
                current = RESEARCH_STORE.update(existing["id"], update_payload) or existing
                try:
                    assessment = assess_public_source(model, current, RESEARCH_STORE.list())
                    current = RESEARCH_STORE.save_assessment(existing["id"], assessment) or current
                    assessed.append(current)
                except Exception as exc:
                    current = dict(current)
                    current["assessment_error"] = str(exc)[:240]
                persisted.append(current)
            else:
                persisted.append(existing)
            continue
        created = RESEARCH_STORE.create(candidate)
        current = created
        if len(str(created.get("source_text", "")).strip()) >= 80:
            try:
                assessment = assess_public_source(model, created, RESEARCH_STORE.list())
                current = RESEARCH_STORE.save_assessment(created["id"], assessment) or created
                assessed.append(current)
            except Exception as exc:
                # Research collection remains useful when the second AI call
                # fails; leave the candidate visible for a later retry.
                current = dict(created)
                current["assessment_error"] = str(exc)[:240]
        persisted.append(current)
    return {"persisted": persisted, "assessed": assessed, "skipped": skipped}


def _store_paths() -> Dict[str, str]:
    return {
        "interviews": STORE.path,
        "resumes": RESUME_STORE.path,
        "research": RESEARCH_STORE.path,
        "memory_overrides": MEMORY_OVERRIDES.path,
        "memory_override_events": MEMORY_OVERRIDES.events_path,
        "tasks": TASKS.path,
    }


def startup_recovery_status() -> Dict[str, Any]:
    return inspect_startup_recovery(DATA_ROOT, _store_paths())


def _public_recovery_status(status: Dict[str, Any]) -> Dict[str, Any]:
    """Do not expose local absolute paths through public health endpoints."""
    safe = dict(status)
    safe["issues"] = []
    for issue in status.get("issues", []) if isinstance(status.get("issues"), list) else []:
        if not isinstance(issue, dict):
            continue
        item = dict(issue)
        if item.get("path"):
            item["path"] = os.path.basename(str(item["path"]))
        safe["issues"].append(item)
    return safe


def _public_backup_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Keep filesystem paths internal; backup IDs remain sufficient for restore."""
    return {key: value for key, value in summary.items() if key != "path"}


def restore_backup_bundle(backup: Dict[str, Any]) -> None:
    """Replace all local stores together, rolling back on a write failure."""
    stores = [
        (STORE, STORE.records()),
        (RESUME_STORE, [RESUME_STORE.get(item["id"]) for item in RESUME_STORE.list()]),
        (RESEARCH_STORE, RESEARCH_STORE.list()),
        (MEMORY_OVERRIDES, MEMORY_OVERRIDES.list()),
    ]
    try:
        baseline_events = list(reversed(MEMORY_OVERRIDES.events(500)))
    except StoreDataError:
        # A corrupt audit log must not prevent restoring the primary labels
        # from a verified backup; the restore will replace the event file.
        baseline_events = []
    replacement = [
        (STORE, backup["interviews"]),
        (RESUME_STORE, backup["resumes"]),
        (RESEARCH_STORE, backup["research"]),
        (MEMORY_OVERRIDES, backup["memory_overrides"]),
    ]
    marker_preexisting = startup_recovery_status().get("recovery_required")
    try:
        for store, records in replacement:
            store.replace_all(records)
        MEMORY_OVERRIDES.replace_events(backup.get("memory_override_events", []))
    except Exception as exc:
        rollback_errors = []
        for store, records in reversed(stores):
            try:
                store.replace_all(records)
            except Exception as rollback_exc:
                rollback_errors.append("%s: %s" % (getattr(store, "path", "store"), type(rollback_exc).__name__))
                # Preserve the original failure for the API response. The
                # stores use atomic file replacement, so the next startup can
                # still recover from the last successful individual write.
                pass
        try:
            MEMORY_OVERRIDES.replace_events(baseline_events)
        except Exception as rollback_exc:
            rollback_errors.append("%s: %s" % (getattr(MEMORY_OVERRIDES, "events_path", "memory_override_events"), type(rollback_exc).__name__))
        if rollback_errors:
            try:
                mark_recovery_required(
                    DATA_ROOT,
                    "backup_restore",
                    "恢复备份时写入失败，且回滚未能完整完成。请使用已验证备份恢复。",
                    rollback_errors,
                )
            except OSError:
                # Keep the original restore failure visible if the marker
                # itself cannot be written because the disk is unavailable.
                pass
        raise RuntimeError("恢复写入失败，已尝试回滚本地数据。") from exc
    if not marker_preexisting:
        clear_recovery_marker(DATA_ROOT)


def store_error_guard(method):
    """Return JSON instead of silently turning local-data corruption into a 500."""
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except StoreDataError as exc:
            OP_LOG.emit("store_error", {"route": urlparse(getattr(self, "path", "")).path[:120], "error_code": type(exc).__name__})
            self.send_json({"ok": False, "error": str(exc)}, 503)
    return guarded


class AssistantHandler(BaseHTTPRequestHandler):

    @store_error_guard
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz":
            recovery = startup_recovery_status()
            self.send_json({"ok": not recovery.get("recovery_required"), "data_status": _public_recovery_status(recovery), "tasks": TASKS.summary(), "operations": OP_LOG.summary()}, 503 if recovery.get("recovery_required") else 200)
            return
        if path.startswith("/api/") and not self.allow_api_request():
            return
        if path.startswith("/api/") and not self.has_api_access():
            return
        if path == "/api/health":
            recovery = startup_recovery_status()
            if recovery.get("recovery_required"):
                self.send_json({"ok": False, "error": "本地数据需要恢复，请先检查备份。", "data_status": _public_recovery_status(recovery), "tasks": TASKS.summary(), "operations": OP_LOG.summary(), "demo_mode": DEMO_MODE, "can_write": self.can_write()}, 503)
                return
            try:
                model = build_model()
                self.send_json(
                    {
                        "ok": True,
                        "provider": getattr(model, "active_provider", "gemini"),
                        "model": getattr(model, "model", ""),
                        "active_provider": getattr(model, "active_provider", "gemini"),
                        "providers": getattr(model, "provider_names", [getattr(model, "active_provider", "gemini")]),
                        "demo_mode": DEMO_MODE,
                        "can_write": self.can_write(),
                        "data_status": _public_recovery_status(recovery),
                        "tasks": TASKS.summary(),
                        "operations": OP_LOG.summary(),
                    }
                )
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc), "demo_mode": DEMO_MODE, "can_write": self.can_write()}, 503)
            return
        if path == "/api/interviews":
            self.send_json({"ok": True, "interviews": STORE.list()})
            return
        if path == "/api/resumes":
            self.send_json({"ok": True, "resumes": RESUME_STORE.list()})
            return
        if path == "/api/research":
            self.send_json({"ok": True, "research": RESEARCH_STORE.list(), "stats": RESEARCH_STORE.stats()})
            return
        if path == "/api/tasks":
            self.send_json({"ok": True, "tasks": TASKS.list()})
            return
        if path == "/api/operations":
            self.send_json({"ok": True, "events": OP_LOG.list(100), "summary": OP_LOG.summary()})
            return
        if len(self.path_parts(path)) == 3 and self.path_parts(path)[:2] == ["api", "tasks"]:
            task = TASKS.get(self.path_parts(path)[2])
            if task is None:
                self.send_json({"ok": False, "error": "未找到这个任务。"}, 404)
            else:
                self.send_json({"ok": True, "task": task})
            return
        if path == "/api/growth-memory/replay":
            memory = build_candidate_memory(STORE.records(), MEMORY_OVERRIDES.list())
            self.send_json({"ok": True, "memory": memory, "replay": memory.get("audit", {}), "override_events": MEMORY_OVERRIDES.events(20)})
            return
        if path == "/api/growth-memory":
            self.send_json({"ok": True, "memory": build_candidate_memory(STORE.records(), MEMORY_OVERRIDES.list()), "override_events": MEMORY_OVERRIDES.events(20)})
            return
        if path == "/api/memory/overrides":
            self.send_json({"ok": True, "overrides": MEMORY_OVERRIDES.list()})
            return
        if path == "/api/memory/overrides/audit":
            self.send_json({"ok": True, "events": MEMORY_OVERRIDES.events(100)})
            return
        if path == "/api/export":
            self.send_json({
                "ok": True,
                "export_version": "1.0",
                "interviews": STORE.records(),
                "resumes": [RESUME_STORE.get(item["id"]) for item in RESUME_STORE.list()],
                "research": RESEARCH_STORE.list(),
                "memory_overrides": MEMORY_OVERRIDES.list(),
                "memory_override_events": MEMORY_OVERRIDES.events(500),
            })
            return
        if path == "/api/backups":
            self.send_json({"ok": True, "backups": [_public_backup_summary(item) for item in list_backups(DATA_ROOT)]})
            return
        if path == "/api/recovery":
            self.send_json({"ok": True, "recovery": _public_recovery_status(startup_recovery_status())})
            return
        if path == "/api/data/retention":
            days = normalise_retention_days(os.environ.get("APP_RETENTION_DAYS", 0))
            self.send_json({"ok": True, "policy": preview_retention(STORE.records(), RESEARCH_STORE.list(), days)})
            return
        if path == "/api/skills":
            self.send_json({"ok": True, "skills": public_skills()})
            return
        parts = self.path_parts(path)
        if len(parts) == 3 and parts[:2] == ["api", "interviews"]:
            record = STORE.get(parts[2])
            if record is None:
                self.send_json({"ok": False, "error": "未找到这场面试。"}, 404)
            else:
                self.send_json({"ok": True, "interview": record})
            return
        if len(parts) == 3 and parts[:2] == ["api", "resumes"]:
            record = RESUME_STORE.get(parts[2])
            if record is None:
                self.send_json({"ok": False, "error": "未找到这份简历。"}, 404)
            else:
                self.send_json({"ok": True, "resume": record})
            return
        if len(parts) == 3 and parts[:2] == ["api", "research"]:
            record = RESEARCH_STORE.get(parts[2])
            if record is None:
                self.send_json({"ok": False, "error": "未找到这条公开资料。"}, 404)
            else:
                self.send_json({"ok": True, "research": record})
            return
        if path in ("/", "/index.html"):
            self.send_file(os.path.join(WEB_ROOT, "index.html"), "text/html; charset=utf-8")
            return
        static_types = {
            "/app.js": "application/javascript; charset=utf-8",
            "/styles.css": "text/css; charset=utf-8",
        }
        if path in static_types:
            self.send_file(os.path.join(WEB_ROOT, path.lstrip("/")), static_types[path])
            return
        self.send_error(404, "Not found")

    @store_error_guard
    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self.allow_api_request():
            return
        if path.startswith("/api/") and not self.has_api_access():
            return
        if not self.require_write():
            return
        if path == "/api/transcribe":
            self.handle_audio_upload()
            return
        if path == "/api/resumes/parse":
            self.handle_resume_file_upload()
            return
        payload = self.read_json_body()
        if payload is None:
            return
        if len(self.path_parts(path)) == 4 and self.path_parts(path)[:2] == ["api", "tasks"] and self.path_parts(path)[3] in {"retry", "cancel"}:
            task_id = self.path_parts(path)[2]
            try:
                task = TASKS.retry(task_id) if self.path_parts(path)[3] == "retry" else TASKS.cancel(task_id)
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            if task is None:
                self.send_json({"ok": False, "error": "未找到可操作的任务。"}, 404)
            else:
                self.send_json({"ok": True, "task": task}, 202)
            return
        if path == "/api/backup":
            summary = create_backup(DATA_ROOT, {
                "interviews": STORE.records(),
                "resumes": [RESUME_STORE.get(item["id"]) for item in RESUME_STORE.list()],
                "research": RESEARCH_STORE.list(),
                "memory_overrides": MEMORY_OVERRIDES.list(),
                "memory_override_events": list(reversed(MEMORY_OVERRIDES.events(500))),
            }, keep_last=normalise_backup_keep(os.environ.get("APP_BACKUP_KEEP", DEFAULT_BACKUP_KEEP)))
            self.send_json({"ok": True, "backup": _public_backup_summary(summary)}, 201)
            return
        parts = self.path_parts(path)
        if len(parts) == 6 and parts[:4] == ["api", "memory", "overrides", "audit"] and parts[5] == "revert":
            if payload.get("confirm") is not True:
                self.send_json({"ok": False, "error": "撤销治理操作前需要明确确认。"}, 400)
                return
            try:
                event = MEMORY_OVERRIDES.revert_event(unquote(parts[4]))
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            self.send_json({"ok": True, "event": event, "overrides": MEMORY_OVERRIDES.list()})
            return
        if path.startswith("/api/backup/restore/"):
            backup_id = unquote(path.rsplit("/", 1)[-1])
            if payload.get("confirm") is not True:
                self.send_json({"ok": False, "error": "恢复备份前需要明确确认。"}, 400)
                return
            try:
                backup = read_backup(DATA_ROOT, backup_id)
                restore_backup_bundle(backup)
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                self.send_json({"ok": False, "error": "恢复失败：%s" % str(exc)[:240]}, 400)
                return
            self.send_json({"ok": True, "restored": backup_id, "counts": {"interviews": len(backup["interviews"]), "resumes": len(backup["resumes"]), "research": len(backup["research"])}})
            return
        if path == "/api/data/cleanup":
            target = str(payload.get("target", "")).strip().lower()
            before = str(payload.get("before", "")).strip()[:30]
            if target not in {"transcripts", "research_excerpts", "all_transient"}:
                self.send_json({"ok": False, "error": "清理目标无效。"}, 400)
                return
            if payload.get("confirm") is not True:
                self.send_json({"ok": False, "error": "清理数据前需要明确确认。"}, 400)
                return
            cleared = {"transcripts": 0, "research_excerpts": 0}
            if target in {"transcripts", "all_transient"}:
                cleared["transcripts"] = STORE.clear_transcripts(before)
            if target in {"research_excerpts", "all_transient"}:
                cleared["research_excerpts"] = RESEARCH_STORE.clear_excerpts(before)
            self.send_json({"ok": True, "target": target, "before": before, "cleared": cleared})
            return
        if path == "/api/data/retention":
            days = normalise_retention_days(payload.get("retention_days", os.environ.get("APP_RETENTION_DAYS", 0)))
            target = str(payload.get("target", "all_transient")).strip().lower()
            if not days:
                self.send_json({"ok": False, "error": "保留天数必须是大于 0 的整数。"}, 400)
                return
            if payload.get("confirm") is not True:
                self.send_json({"ok": False, "error": "执行保留策略前需要明确确认。"}, 400)
                return
            try:
                result = apply_retention(STORE, RESEARCH_STORE, days, target)
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            self.send_json({"ok": True, "retention": result})
            return
        if path == "/api/interviews":
            error = validate_interview(payload, require_transcript=True)
            if error:
                self.send_json({"ok": False, "error": error}, 400)
                return
            self.send_json({"ok": True, "interview": STORE.create(payload)}, 201)
            return
        if path == "/api/interviews/demo":
            self.send_json({"ok": True, "interview": STORE.create(sample_interview())}, 201)
            return
        if path == "/api/resumes":
            error = self.validate_resume(payload)
            if error:
                self.send_json({"ok": False, "error": error}, 400)
                return
            self.send_json({"ok": True, "resume": RESUME_STORE.create(payload)}, 201)
            return
        if path == "/api/research":
            error = validate_research(payload)
            if error:
                self.send_json({"ok": False, "error": error}, 400)
                return
            self.send_json({"ok": True, "research": RESEARCH_STORE.create(payload)}, 201)
            return
        if path == "/api/research/candidate":
            candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else payload
            candidate = dict(candidate)
            error = validate_research_candidate(candidate)
            if error:
                self.send_json({"ok": False, "error": error}, 400)
                return
            url = str(candidate.get("url", "")).strip()
            existing = next((item for item in RESEARCH_STORE.list() if item.get("url") == url), None)
            if existing:
                self.send_json({"ok": True, "research": existing, "existing": True})
                return
            enriched = enrich_public_candidate(candidate)
            fetched = enriched.get("fetch") if isinstance(enriched.get("fetch"), dict) else {}
            fetched_text = str(enriched.get("source_text", "")).strip()
            fetch_status = str(enriched.get("fetch_status", "manual_check_required"))
            if fetched_text:
                notes = "Agent 已自动读取公开页面可见文本；这不是人工确认，仍需检查原帖和上下文后再预审。"
            else:
                reason = str(fetched.get("fetch_reason", "公开页面未返回足够正文。"))
                notes = "Agent 已尝试自动打开原帖，但未获得足够正文：%s 仍可手动检查链接。" % reason
            enriched.update({
                "status": "candidate",
                "source_text": fetched_text,
                "notes": notes,
                "fetch_status": fetch_status,
            })
            self.send_json({"ok": True, "research": RESEARCH_STORE.create(enriched), "existing": False}, 201)
            return
        if path == "/api/research/discover":
            company = str(payload.get("company", "")).strip()
            role = str(payload.get("role", "")).strip()
            topic = derive_research_topic(payload.get("topic", ""), payload.get("jd_analysis"), payload.get("job_description", ""))
            platform = normalise_platform(payload.get("platform"))
            if not company and not role and not topic:
                self.send_json({"ok": False, "error": "请至少填写公司、岗位或搜索主题。"}, 400)
                return
            try:
                model = build_model()
                candidates = discover_public_sources(
                    model,
                    company,
                    role,
                    str(payload.get("round_name", "")).strip(),
                    topic,
                    platform,
                )
                self.send_json({
                    "ok": True,
                    "candidates": candidates,
                    "search_meta": _build_discovery_search_meta(
                        platform,
                        company,
                        role,
                        str(payload.get("round_name", "")).strip(),
                        topic,
                        candidates,
                    ),
                })
            except ResearchGroundingError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 502)
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 503)
            except Exception:
                self.send_json({"ok": False, "error": "联网搜索失败，请检查模型配置后重试。"}, 502)
            return
        if path == "/api/research/agent":
            if payload.get("async") is True:
                async_company = str(payload.get("company", "")).strip()
                async_role = str(payload.get("role", "")).strip()
                async_topic = derive_research_topic(
                    payload.get("topic", ""),
                    payload.get("jd_analysis"),
                    payload.get("job_description", ""),
                )
                if not async_company and not async_role and not async_topic:
                    self.send_json({"ok": False, "error": "请至少填写公司、岗位或搜索主题。"}, 400)
                    return
                try:
                    task = TASKS.submit(
                        "research_agent",
                        lambda: run_safe_task(
                            lambda: run_research_agent_request(dict(payload)),
                            "智能调研失败，请检查模型配置后重试。",
                        ),
                    )
                except ValueError as exc:
                    self.send_json({"ok": False, "error": str(exc)}, 400)
                except RuntimeError as exc:
                    self.send_json({"ok": False, "error": str(exc)}, 503)
                else:
                    self.send_json({"ok": True, "task": task}, 202)
                return
            try:
                self.send_json({"ok": True, **run_research_agent_request(payload)})
            except ResearchGroundingError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 502)
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 503)
            except Exception:
                self.send_json({"ok": False, "error": "智能调研失败，请检查模型配置后重试。"}, 502)
            return
        if path == "/api/note-questions":
            jd = str(payload.get("job_description", "")).strip()
            resume = str(payload.get("resume_context", "")).strip()
            iid = str(payload.get("interview_id", "")).strip()
            sources = payload.get("research_context") if isinstance(payload.get("research_context"), list) else []
            if iid:
                record = STORE.get(iid)
                if record:
                    jd = jd or str(record.get("job_description", ""))
                    resume = resume or str(record.get("resume_context", ""))
                    sources = sources or reconcile_research_context(record.get("research_context", []))
            sources = reconcile_research_context(sources)
            try:
                model = build_model()
                analysis = payload.get("jd_analysis") if isinstance(payload.get("jd_analysis"), dict) else {}
                if iid and record:
                    analysis = analysis or record.get("jd_analysis") or {}
                prompt_sources = sources + RESEARCH_STORE.approved_for(str(payload.get("company", "")), str(payload.get("role", "")))
                result = generate_note_questions(model, jd, resume, prompt_sources, analysis)
                approved_count = sum(
                    1 for item in prompt_sources
                    if isinstance(item, dict)
                    and str(item.get("status", "candidate")).strip().lower() == "approved"
                    and item.get("citation_allowed") is not False
                )
                self.send_json({
                    "ok": True,
                    "questions": result["questions"],
                    "research_meta": {
                        "provided_count": len([item for item in prompt_sources if isinstance(item, dict)]),
                        "approved_count": approved_count,
                        "mode": "jd_and_research" if prompt_sources else "jd_resume_fallback",
                        "note": (
                            "公开线索只影响追问方向，不进入本场表现证据。"
                            if prompt_sources else "未获取到公开研究线索，本次问题仅基于 JD 与简历。"
                        ),
                    },
                })
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 503)
            except Exception:
                self.send_json({"ok": False, "error": "速记问卷生成失败，请检查 Gemini 网络与配额后重试。"}, 502)
            return
        if path == "/api/growth-report":
            records = STORE.records()
            if not any(isinstance(record.get("review"), dict) for record in records):
                self.send_json({"ok": False, "error": "至少先完成一场面试复盘，才能生成阶段报告。"}, 400)
                return
            try:
                model = build_model()
                memory = build_candidate_memory(records, MEMORY_OVERRIDES.list())
                report = generate_growth_report(model, records, memory)
                self.send_json({"ok": True, "report": report, "memory": memory})
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 503)
            except Exception:
                self.send_json({"ok": False, "error": "阶段报告生成失败，请检查 Gemini 网络与配额后重试。"}, 502)
            return
        if path == "/api/extract-jd":
            raw_jd = str(payload.get("job_description", "")).strip()
            if len(raw_jd) < 30:
                self.send_json({"ok": False, "error": "请先粘贴一段足够完整的 JD。"}, 400)
                return
            try:
                model = build_model()
                self.send_json({"ok": True, "analysis": extract_job_description(model, raw_jd)})
            except Exception:
                self.send_json({"ok": False, "error": "JD 提取失败，请检查 Gemini 网络与配额后重试。"}, 502)
            return
        parts = self.path_parts(path)
        if len(parts) == 6 and parts[:2] == ["api", "interviews"] and parts[3] == "actions" and parts[5] == "attempts":
            try:
                updated = STORE.add_action_attempt(
                    parts[2],
                    parts[4],
                    payload.get("phase", ""),
                    payload.get("response", ""),
                    score=payload.get("self_score"),
                    criteria_met=payload.get("criteria_met"),
                    note=payload.get("note", ""),
                )
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
                return
            if updated is None:
                self.send_json({"ok": False, "error": "未找到训练行动。"}, 404)
            else:
                self.send_json({"ok": True, "interview": updated})
            return
        if len(parts) == 4 and parts[:2] == ["api", "interviews"] and parts[3] == "review":
            record = STORE.get(parts[2])
            if record is None:
                self.send_json({"ok": False, "error": "未找到这场面试。"}, 404)
                return
            if payload.get("async") is True:
                try:
                    task = TASKS.submit(
                        "interview_review",
                        lambda: run_safe_task(
                            lambda: run_review_request(parts[2], dict(payload)),
                            "复盘生成失败，请检查模型网络与配额后重试。",
                        ),
                    )
                except ValueError as exc:
                    self.send_json({"ok": False, "error": str(exc)}, 400)
                except RuntimeError as exc:
                    self.send_json({"ok": False, "error": str(exc)}, 503)
                else:
                    self.send_json({"ok": True, "task": task}, 202)
                return
            try:
                self.send_json({"ok": True, **run_review_request(parts[2], payload)})
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 400)
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 503)
            except Exception:
                self.send_json(
                    {"ok": False, "error": "复盘生成失败。请稍后重试，并检查 Gemini 网络与配额。"},
                    502,
                )
            return
        if len(parts) == 4 and parts[:2] == ["api", "research"] and parts[3] == "assess":
            record = RESEARCH_STORE.get(parts[2])
            if record is None:
                self.send_json({"ok": False, "error": "未找到这条公开资料。"}, 404)
                return
            try:
                model = build_model()
                assessment = assess_public_source(model, record, RESEARCH_STORE.list())
                updated = RESEARCH_STORE.save_assessment(parts[2], assessment)
                self.send_json({"ok": True, "research": updated})
            except ResearchGroundingError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 502)
            except Exception:
                self.send_json({"ok": False, "error": "AI 预审失败，请检查 Gemini 网络与配额后重试。"}, 502)
            return
        if len(parts) == 4 and parts[:2] == ["api", "research"] and parts[3] == "status":
            status = str(payload.get("status", ""))
            updated = RESEARCH_STORE.set_status(parts[2], status)
            if updated is None:
                self.send_json({"ok": False, "error": "资料状态无效或资料不存在。"}, 400)
            else:
                self.send_json({"ok": True, "research": updated})
            return
        self.send_json({"ok": False, "error": "接口不存在。"}, 404)

    @store_error_guard
    def do_PUT(self) -> None:  # noqa: N802
        if urlparse(self.path).path.startswith("/api/") and not self.allow_api_request():
            return
        if not self.has_api_access():
            return
        if not self.require_write():
            return
        parts = self.path_parts(urlparse(self.path).path)
        if len(parts) == 4 and parts[:3] == ["api", "memory", "gaps"]:
            payload = self.read_json_body()
            if payload is None:
                return
            gap_key = unquote(parts[3]).strip()
            if not gap_key or len(gap_key) > 180:
                self.send_json({"ok": False, "error": "缺口标识无效。"}, 400)
                return
            title = payload.get("title") if "title" in payload else None
            if title is not None and len(str(title).strip()) > 160:
                self.send_json({"ok": False, "error": "缺口名称过长。"}, 400)
                return
            record = MEMORY_OVERRIDES.upsert(gap_key, title=title, ignored=payload.get("ignored") is True)
            self.send_json({"ok": True, "override": record})
            return
        if len(parts) == 3 and parts[:2] == ["api", "resumes"]:
            payload = self.read_json_body()
            if payload is None:
                return
            error = self.validate_resume(payload)
            if error:
                self.send_json({"ok": False, "error": error}, 400)
                return
            record = RESUME_STORE.update(parts[2], payload)
            if record is None:
                self.send_json({"ok": False, "error": "未找到这份简历。"}, 404)
            else:
                self.send_json({"ok": True, "resume": record})
            return
        if len(parts) == 3 and parts[:2] == ["api", "research"]:
            payload = self.read_json_body()
            if payload is None:
                return
            error = validate_research(payload)
            if error:
                self.send_json({"ok": False, "error": error}, 400)
                return
            record = RESEARCH_STORE.update(parts[2], payload)
            if record is None:
                self.send_json({"ok": False, "error": "未找到这条公开资料。"}, 404)
            else:
                self.send_json({"ok": True, "research": record})
            return
        if len(parts) != 3 or parts[:2] != ["api", "interviews"]:
            self.send_json({"ok": False, "error": "接口不存在。"}, 404)
            return
        payload = self.read_json_body()
        if payload is None:
            return
        # An existing record may have had its raw transcript intentionally
        # cleared. Metadata, outcome and governance must remain editable.
        error = validate_interview(payload, require_transcript=False)
        if error:
            self.send_json({"ok": False, "error": error}, 400)
            return
        record = STORE.update(parts[2], payload)
        if record is None:
            self.send_json({"ok": False, "error": "未找到这场面试。"}, 404)
        else:
            self.send_json({"ok": True, "interview": record})

    @store_error_guard
    def do_DELETE(self) -> None:  # noqa: N802
        if urlparse(self.path).path.startswith("/api/") and not self.allow_api_request():
            return
        if not self.has_api_access():
            return
        if not self.require_write():
            return
        parts = self.path_parts(urlparse(self.path).path)
        if len(parts) == 4 and parts[:3] == ["api", "memory", "gaps"]:
            gap_key = unquote(parts[3]).strip()
            if not MEMORY_OVERRIDES.delete(gap_key):
                self.send_json({"ok": False, "error": "未找到缺口治理记录。"}, 404)
                return
            self.send_json({"ok": True, "deleted": gap_key})
            return
        if len(parts) != 3:
            self.send_json({"ok": False, "error": "接口不存在。"}, 404)
            return
        stores = {"interviews": STORE, "resumes": RESUME_STORE, "research": RESEARCH_STORE}
        if parts[0:2] != ["api", "interviews"] and parts[0:2] != ["api", "resumes"] and parts[0:2] != ["api", "research"]:
            self.send_json({"ok": False, "error": "接口不存在。"}, 404)
            return
        store = stores.get(parts[1])
        if store is None or not store.delete(parts[2]):
            self.send_json({"ok": False, "error": "未找到要删除的资料。"}, 404)
            return
        self.send_json({"ok": True, "deleted": parts[2]})

    def handle_audio_upload(self) -> None:
        fields = self.read_multipart(MAX_AUDIO_BYTES, "音频文件需小于 50 MB。请裁剪为本轮面试的相关片段后重试。")
        if fields is None:
            return
        consent = fields.get("consent")
        audio = fields.get("audio")
        if consent is None or consent.text != "true" or audio is None or not audio.filename:
            self.send_json({"ok": False, "error": "上传前请确认你有权使用这段录音。"}, 400)
            return
        filename = os.path.basename(audio.filename)
        mime_type = audio.content_type or mimetypes.guess_type(filename)[0] or ""
        if mime_type not in ALLOWED_AUDIO_TYPES:
            self.send_json({"ok": False, "error": "仅支持 MP3、M4A、WAV、AAC、OGG 和 WebM 音频。"}, 400)
            return
        suffix = os.path.splitext(filename)[1] or ".audio"
        temporary_path = ""
        try:
            with _new_temporary_upload("autumn-audio-", suffix) as handle:
                temporary_path = handle.name
                handle.write(audio.value)
            if fields.get("async") is not None and fields["async"].text == "true":
                task_path = temporary_path

                def transcribe_task() -> Dict[str, Any]:
                    try:
                        return run_safe_task(
                            lambda: {"transcription": transcribe_audio(build_model(), task_path, mime_type)},
                            "音频处理失败，请稍后重试。",
                        )
                    finally:
                        _remove_temporary_file(task_path)

                try:
                    task = TASKS.submit("audio_transcription", transcribe_task)
                except RuntimeError as exc:
                    self.send_json({"ok": False, "error": str(exc)}, 503)
                else:
                    temporary_path = ""
                    self.send_json({"ok": True, "task": task}, 202)
                return
            model = build_model()
            transcription = transcribe_audio(model, temporary_path, mime_type)
            self.send_json({"ok": True, "transcription": transcription})
        except AudioTranscriptionError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 502)
        except Exception:
            self.send_json({"ok": False, "error": "音频处理失败，请稍后重试。"}, 502)
        finally:
            _remove_temporary_file(temporary_path)

    def validate_resume(self, payload: Dict[str, Any]) -> Optional[str]:
        if not str(payload.get("name", "")).strip():
            return "请填写简历版本名称。"
        if len(str(payload.get("content", "")).strip()) < 30:
            return "请粘贴至少一段简历内容。"
        return None

    def handle_resume_file_upload(self) -> None:
        fields = self.read_multipart(MAX_RESUME_FILE_BYTES, "简历文件需小于 25 MB。")
        if fields is None:
            return
        consent = fields.get("consent")
        resume = fields.get("resume")
        if consent is None or consent.text != "true" or resume is None or not resume.filename:
            self.send_json({"ok": False, "error": "解析前请确认你同意将文件发送给 Gemini。"}, 400)
            return
        filename = os.path.basename(resume.filename)
        mime_type = resume.content_type or mimetypes.guess_type(filename)[0] or ""
        if mime_type not in ALLOWED_RESUME_TYPES:
            self.send_json({"ok": False, "error": "仅支持 PDF、PNG、JPG/JPEG 和 WebP 简历。"}, 400)
            return
        temporary_path = ""
        try:
            with _new_temporary_upload("autumn-resume-", os.path.splitext(filename)[1]) as handle:
                temporary_path = handle.name
                handle.write(resume.value)
            model = build_model()
            self.send_json({"ok": True, "resume": extract_resume_file(model, temporary_path, mime_type)})
        except AudioTranscriptionError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 502)
        except Exception:
            self.send_json({"ok": False, "error": "简历文件解析失败，请稍后重试。"}, 502)
        finally:
            _remove_temporary_file(temporary_path)

    @store_error_guard
    def do_PATCH(self) -> None:  # noqa: N802
        if urlparse(self.path).path.startswith("/api/") and not self.allow_api_request():
            return
        if not self.has_api_access():
            return
        if not self.require_write():
            return
        parts = self.path_parts(urlparse(self.path).path)
        if len(parts) != 5 or parts[:2] != ["api", "interviews"] or parts[3] != "actions":
            self.send_json({"ok": False, "error": "接口不存在。"}, 404)
            return
        payload = self.read_json_body()
        if payload is None:
            return
        acceptance_status = str(payload.get("acceptance_status", "")).strip().lower()
        acceptance_note = str(payload.get("acceptance_note", ""))
        if acceptance_status not in {"", "pending", "passed", "needs_retry"}:
            self.send_json({"ok": False, "error": "验收状态无效。"}, 400)
            return
        try:
            record = STORE.set_action_done(
                parts[2],
                parts[4],
                bool(payload.get("done")),
                acceptance_status=acceptance_status,
                acceptance_note=acceptance_note,
            )
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)
            return
        if record is None:
            self.send_json({"ok": False, "error": "未找到行动项。"}, 404)
        else:
            self.send_json({"ok": True, "interview": record})

    def path_parts(self, path: str):
        return [part for part in path.split("/") if part]

    def client_id(self) -> str:
        address = getattr(self, "client_address", None)
        return address[0] if address else "unknown"

    def allow_api_request(self) -> bool:
        """Bound API request volume without counting the public health probe."""
        try:
            limit = int(os.environ.get("APP_RATE_LIMIT_PER_MINUTE", DEFAULT_API_RATE_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_API_RATE_LIMIT
        if limit <= 0:
            return True
        now = time.monotonic()
        client = self.client_id()
        with _request_lock:
            cutoff = now - API_RATE_WINDOW_SECONDS
            timestamps = [stamp for stamp in _request_buckets.get(client, []) if stamp > cutoff]
            if len(timestamps) >= limit:
                _request_buckets[client] = timestamps
                self.send_json({"ok": False, "error": "请求过于频繁，请稍后重试。"}, 429)
                return False
            timestamps.append(now)
            _request_buckets[client] = timestamps
            if len(_request_buckets) > 256:
                _request_buckets.clear()
                _request_buckets[client] = timestamps
        return True

    def has_valid_token(self) -> bool:
        required_token = os.environ.get("APP_ACCESS_TOKEN", "").strip()
        if not required_token:
            return True
        supplied_token = self.headers.get("X-App-Token", "")
        if not supplied_token:
            return False
        return hmac.compare_digest(required_token, supplied_token)

    def can_write(self) -> bool:
        """Return whether the caller may perform writes under the current deployment policy."""
        if DEMO_MODE and not os.environ.get("APP_ACCESS_TOKEN", "").strip():
            return False
        return self.has_valid_token()

    def has_api_access(self) -> bool:
        """Read-level gate. Demo mode lets anyone read; otherwise a token is required."""
        if not os.environ.get("APP_ACCESS_TOKEN", "").strip():
            return True
        if DEMO_MODE:
            return True
        return self._token_or_error(401, "需要访问口令。")

    def require_write(self) -> bool:
        """Write-level gate for POST/PUT/PATCH."""
        required_token = os.environ.get("APP_ACCESS_TOKEN", "").strip()
        if not DEMO_MODE:
            # The read gate already validated the token on these routes.
            return True
        if not required_token:
            self.send_json({"ok": False, "error": "演示模式未设置管理口令，当前服务仅允许只读访问。"}, 503)
            return False
        return self._token_or_error(403, "演示模式为只读。保存、AI 复盘和联网搜索需要管理口令。")

    def _token_or_error(self, fail_status: int, fail_error: str) -> bool:
        """Validate the supplied token with per-IP brute-force protection."""
        client = self.client_id()
        now = time.monotonic()
        with _login_lock:
            state = _login_failures.get(client)
            if state and state["count"] >= LOGIN_MAX_FAILURES and now < state["until"]:
                self.send_json({"ok": False, "error": "尝试次数过多，请稍后再试。"}, 429)
                return False
        if self.has_valid_token():
            with _login_lock:
                _login_failures.pop(client, None)
            return True
        with _login_lock:
            state = _login_failures.get(client, {"count": 0, "until": 0.0})
            state["count"] += 1
            if state["count"] >= LOGIN_MAX_FAILURES:
                state["until"] = now + LOGIN_LOCK_SECONDS
            _login_failures[client] = state
        self.send_json({"ok": False, "error": fail_error}, fail_status)
        return False

    def read_multipart(self, max_bytes: int, size_error: str):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if not 0 < content_length <= max_bytes:
            self.send_json({"ok": False, "error": size_error}, 400)
            return None
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json({"ok": False, "error": "上传格式不正确。"}, 400)
            return None
        body = self.rfile.read(content_length)
        try:
            return parse_multipart(body, content_type)
        except ValueError:
            self.send_json({"ok": False, "error": "上传格式不正确。"}, 400)
            return None

    def read_json_body(self) -> Optional[Dict[str, Any]]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if not 0 < content_length <= MAX_BODY_BYTES:
            self.send_json({"ok": False, "error": "请求内容不合法，请缩短转写内容后重试。"}, 400)
            return None
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json({"ok": False, "error": "请求格式不正确。"}, 400)
            return None
        if not isinstance(payload, dict):
            self.send_json({"ok": False, "error": "请求格式不正确。"}, 400)
            return None
        return payload

    def send_file(self, path: str, content_type: str) -> None:
        if not os.path.isfile(path):
            self.send_error(404, "Static file not found")
            return
        with open(path, "rb") as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Autumn PM interview assistant")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    args = parser.parse_args()
    validate_bind_security(args.host)
    seed_demo_data()
    server = ThreadingHTTPServer((args.host, args.port), AssistantHandler)
    print("Autumn PM interview assistant running at http://%s:%s" % (args.host, args.port))
    if DEMO_MODE:
        print("Demo mode: read-only for visitors; writes need APP_ACCESS_TOKEN.")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAssistant stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
