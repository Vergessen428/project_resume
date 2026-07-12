"""Local web application for the Autumn PM interview assistant."""

import argparse
import hmac
import json
import mimetypes
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.audio_transcription import AudioTranscriptionError, extract_resume_file, transcribe_audio
from core.growth_memory import build_candidate_memory
from core.interview_review import extract_job_description, generate_growth_report, generate_interview_review, sample_interview
from core.interview_store import InterviewStore
from core.model_provider import build_model, load_dotenv
from core.multipart import parse_multipart
from core.pm_skills import public_skills
from core.research_grounding import ResearchGroundingError, assess_public_source, discover_public_sources
from core.research_store import ResearchStore
from core.resume_store import ResumeStore


WEB_ROOT = os.path.join(PROJECT_ROOT, "web")
DATA_ROOT = os.path.realpath(os.environ.get("APP_DATA_DIR", os.path.join(PROJECT_ROOT, "data")))
STORE = InterviewStore(os.path.join(DATA_ROOT, "interviews.json"))
RESUME_STORE = ResumeStore(os.path.join(DATA_ROOT, "resumes.json"))
RESEARCH_STORE = ResearchStore(os.path.join(DATA_ROOT, "research.json"))
MAX_BODY_BYTES = 120000
MAX_AUDIO_BYTES = 50 * 1024 * 1024
MAX_RESUME_FILE_BYTES = 25 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/mp4", "audio/x-m4a", "audio/aac", "audio/ogg", "audio/webm"}
ALLOWED_RESUME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def validate_interview(payload: Dict[str, Any]) -> Optional[str]:
    if not str(payload.get("company", "")).strip():
        return "请填写公司名称。"
    if not str(payload.get("role", "")).strip():
        return "请填写投递岗位。"
    transcript = str(payload.get("transcript", "")).strip()
    if len(transcript) < 30:
        return "请粘贴或导入至少一段面试转写/复盘记录。"
    return None


def validate_research(payload: Dict[str, Any]) -> Optional[str]:
    if not str(payload.get("title", "")).strip():
        return "请填写资料标题。"
    url = str(payload.get("url", "")).strip()
    if not (url.startswith("https://") or url.startswith("http://")):
        return "请填写原帖的完整 http(s) 链接。"
    if len(str(payload.get("source_text", "")).strip()) < 80:
        return "请粘贴至少 80 个字的原帖正文摘录，避免 AI 只凭标题判断。"
    return None


class AssistantHandler(BaseHTTPRequestHandler):

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz":
            self.send_json({"ok": True})
            return
        if path.startswith("/api/") and not self.has_api_access():
            return
        if path == "/api/health":
            try:
                model = build_model()
                self.send_json(
                    {
                        "ok": True,
                        "provider": getattr(model, "active_provider", "gemini"),
                        "model": getattr(model, "model", ""),
                        "active_provider": getattr(model, "active_provider", "gemini"),
                        "providers": getattr(model, "provider_names", [getattr(model, "active_provider", "gemini")]),
                    }
                )
            except RuntimeError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 503)
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
        if path == "/api/growth-memory":
            self.send_json({"ok": True, "memory": build_candidate_memory(STORE.records())})
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

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/") and not self.has_api_access():
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
        if path == "/api/interviews":
            error = validate_interview(payload)
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
        if path == "/api/research/discover":
            company = str(payload.get("company", "")).strip()
            role = str(payload.get("role", "")).strip()
            topic = str(payload.get("topic", "")).strip()
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
                )
                self.send_json({"ok": True, "candidates": candidates})
            except ResearchGroundingError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 502)
            return
        if path == "/api/growth-report":
            records = STORE.records()
            if not any(isinstance(record.get("review"), dict) for record in records):
                self.send_json({"ok": False, "error": "至少先完成一场面试复盘，才能生成阶段报告。"}, 400)
                return
            try:
                model = build_model()
                memory = build_candidate_memory(records)
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
        if len(parts) == 4 and parts[:2] == ["api", "interviews"] and parts[3] == "review":
            record = STORE.get(parts[2])
            if record is None:
                self.send_json({"ok": False, "error": "未找到这场面试。"}, 404)
                return
            try:
                model = build_model()
                review = generate_interview_review(
                    model,
                    record,
                    RESEARCH_STORE.approved_for(record.get("company", ""), record.get("role", "")),
                    build_candidate_memory(STORE.records()),
                )
                updated = STORE.save_review(parts[2], review)
                self.send_json({"ok": True, "interview": updated})
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

    def do_PUT(self) -> None:  # noqa: N802
        if not self.has_api_access():
            return
        parts = self.path_parts(urlparse(self.path).path)
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
        error = validate_interview(payload)
        if error:
            self.send_json({"ok": False, "error": error}, 400)
            return
        record = STORE.update(parts[2], payload)
        if record is None:
            self.send_json({"ok": False, "error": "未找到这场面试。"}, 404)
        else:
            self.send_json({"ok": True, "interview": record})

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
            with tempfile.NamedTemporaryFile(prefix="autumn-audio-", suffix=suffix, delete=False) as handle:
                temporary_path = handle.name
                handle.write(audio.value)
            model = build_model()
            transcription = transcribe_audio(model, temporary_path, mime_type)
            self.send_json({"ok": True, "transcription": transcription})
        except AudioTranscriptionError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 502)
        except Exception:
            self.send_json({"ok": False, "error": "音频处理失败，请稍后重试。"}, 502)
        finally:
            if temporary_path and os.path.isfile(temporary_path):
                os.remove(temporary_path)

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
            with tempfile.NamedTemporaryFile(prefix="autumn-resume-", suffix=os.path.splitext(filename)[1], delete=False) as handle:
                temporary_path = handle.name
                handle.write(resume.value)
            model = build_model()
            self.send_json({"ok": True, "resume": extract_resume_file(model, temporary_path, mime_type)})
        except AudioTranscriptionError as exc:
            self.send_json({"ok": False, "error": str(exc)}, 502)
        except Exception:
            self.send_json({"ok": False, "error": "简历文件解析失败，请稍后重试。"}, 502)
        finally:
            if temporary_path and os.path.isfile(temporary_path):
                os.remove(temporary_path)

    def do_PATCH(self) -> None:  # noqa: N802
        if not self.has_api_access():
            return
        parts = self.path_parts(urlparse(self.path).path)
        if len(parts) != 5 or parts[:2] != ["api", "interviews"] or parts[3] != "actions":
            self.send_json({"ok": False, "error": "接口不存在。"}, 404)
            return
        payload = self.read_json_body()
        if payload is None:
            return
        record = STORE.set_action_done(parts[2], parts[4], bool(payload.get("done")))
        if record is None:
            self.send_json({"ok": False, "error": "未找到行动项。"}, 404)
        else:
            self.send_json({"ok": True, "interview": record})

    def path_parts(self, path: str):
        return [part for part in path.split("/") if part]

    def has_api_access(self) -> bool:
        required_token = os.environ.get("APP_ACCESS_TOKEN", "").strip()
        if not required_token:
            return True
        supplied_token = self.headers.get("X-App-Token", "")
        if hmac.compare_digest(required_token, supplied_token):
            return True
        self.send_json({"ok": False, "error": "需要访问口令。"}, 401)
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
    server = ThreadingHTTPServer((args.host, args.port), AssistantHandler)
    print("Autumn PM interview assistant running at http://%s:%s" % (args.host, args.port))
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
