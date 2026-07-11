"""Temporary Gemini Files API audio transcription for V2 uploads."""

import json
import os
import re
import time
import urllib.request
from typing import Any, Dict


NATIVE_GEMINI_ROOT = "https://generativelanguage.googleapis.com"


class AudioTranscriptionError(RuntimeError):
    pass


def transcribe_audio(model: Any, audio_path: str, mime_type: str) -> Dict[str, str]:
    model = _gemini_client(model)
    api_key = getattr(model, "api_key", "")
    model_name = getattr(model, "model", "")
    if not api_key or not model_name:
        raise AudioTranscriptionError("当前模型不支持音频转写，请使用 Gemini 模型。")

    file_name = ""
    try:
        uploaded = _upload_file(api_key, audio_path, mime_type)
        file = uploaded.get("file", {})
        file_name = str(file.get("name", ""))
        active_file = _wait_until_active(api_key, file)
        result = _generate_transcript(api_key, model_name, active_file, mime_type)
        return _parse_transcript(result)
    except AudioTranscriptionError:
        raise
    except Exception as exc:
        raise AudioTranscriptionError("音频转写没有完成，请检查网络、Gemini 配额或音频格式后重试。") from exc
    finally:
        if file_name:
            _delete_file(api_key, file_name)


def extract_resume_file(model: Any, file_path: str, mime_type: str) -> Dict[str, str]:
    model = _gemini_client(model)
    api_key = getattr(model, "api_key", "")
    model_name = getattr(model, "model", "")
    if not api_key or not model_name:
        raise AudioTranscriptionError("当前模型不支持简历文件解析，请使用 Gemini 模型。")
    file_name = ""
    try:
        uploaded = _upload_file(api_key, file_path, mime_type)
        file = uploaded.get("file", {})
        file_name = str(file.get("name", ""))
        active_file = _wait_until_active(api_key, file)
        prompt = """Extract this resume faithfully. Return only JSON:
{"name":"suggested short resume version name", "target_role":"target role if stated", "content":"complete extracted resume text in Chinese or its original language"}.
Do not add achievements or facts that are not visible in the uploaded document or image. Preserve dates, employers, project names, skills and metrics when legible."""
        return _parse_resume(_generate_file_text(api_key, model_name, active_file, mime_type, prompt))
    except AudioTranscriptionError:
        raise
    except Exception as exc:
        raise AudioTranscriptionError("简历解析没有完成，请检查网络、Gemini 配额或文件格式后重试。") from exc
    finally:
        if file_name:
            _delete_file(api_key, file_name)


def _upload_file(api_key: str, audio_path: str, mime_type: str) -> Dict[str, Any]:
    size = os.path.getsize(audio_path)
    metadata = json.dumps({"file": {"display_name": "autumn-interview-audio"}}).encode("utf-8")
    start_request = urllib.request.Request(
        NATIVE_GEMINI_ROOT + "/upload/v1beta/files",
        data=metadata,
        headers={
            "x-goog-api-key": api_key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(start_request, timeout=60) as response:
        upload_url = response.headers.get("x-goog-upload-url")
    if not upload_url:
        raise AudioTranscriptionError("Gemini 没有返回音频上传地址。")

    with open(audio_path, "rb") as handle:
        audio_bytes = handle.read()
    upload_request = urllib.request.Request(
        upload_url,
        data=audio_bytes,
        headers={
            "Content-Length": str(size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
        method="POST",
    )
    with urllib.request.urlopen(upload_request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_until_active(api_key: str, file: Dict[str, Any]) -> Dict[str, Any]:
    current = file
    for _ in range(20):
        state = str(current.get("state", "ACTIVE"))
        if state == "ACTIVE":
            return current
        if state == "FAILED":
            raise AudioTranscriptionError("Gemini 无法处理这个音频文件。")
        name = str(current.get("name", ""))
        if not name:
            raise AudioTranscriptionError("Gemini 音频文件状态异常。")
        time.sleep(1)
        request = urllib.request.Request(
            NATIVE_GEMINI_ROOT + "/v1beta/" + name,
            headers={"x-goog-api-key": api_key},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            current = json.loads(response.read().decode("utf-8"))
    raise AudioTranscriptionError("音频处理时间过长，请缩短文件后重试。")


def _generate_transcript(api_key: str, model_name: str, file: Dict[str, Any], mime_type: str) -> str:
    prompt = """Transcribe this interview audio faithfully in Chinese. Return only JSON:
{"transcript":"timestamped transcript", "language":"detected language", "notes":"brief quality note"}.
Use timestamps in [MM:SS] where possible. Label speakers only when reasonably clear; otherwise use 说话人1/说话人2. Do not summarize or invent content."""
    return _generate_file_text(api_key, model_name, file, mime_type, prompt)


def _generate_file_text(api_key: str, model_name: str, file: Dict[str, Any], mime_type: str, prompt: str) -> str:
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "file_data": {
                            "mime_type": mime_type,
                            "file_uri": file.get("uri", ""),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {"temperature": 0},
    }
    request = urllib.request.Request(
        NATIVE_GEMINI_ROOT + "/v1beta/models/%s:generateContent" % model_name,
        data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))


def _parse_transcript(content: str) -> Dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            return {"transcript": content.strip(), "language": "", "notes": "模型未返回结构化转写。"}
        parsed = json.loads(cleaned[start : end + 1])
    transcript = str(parsed.get("transcript", "")).strip()
    if not transcript:
        raise AudioTranscriptionError("未从音频中提取到可用文字。")
    return {
        "transcript": transcript[:32000],
        "language": str(parsed.get("language", ""))[:40],
        "notes": str(parsed.get("notes", ""))[:500],
    }


def _parse_resume(content: str) -> Dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            return {"name": "导入的简历", "target_role": "", "content": content.strip()}
        parsed = json.loads(cleaned[start : end + 1])
    extracted = str(parsed.get("content", "")).strip()
    if len(extracted) < 20:
        raise AudioTranscriptionError("未能从文件中解析出足够的简历文字。")
    return {
        "name": str(parsed.get("name", "导入的简历"))[:120],
        "target_role": str(parsed.get("target_role", ""))[:120],
        "content": extracted[:24000],
    }


def _delete_file(api_key: str, file_name: str) -> None:
    try:
        request = urllib.request.Request(
            NATIVE_GEMINI_ROOT + "/v1beta/" + file_name,
            headers={"x-goog-api-key": api_key},
            method="DELETE",
        )
        with urllib.request.urlopen(request, timeout=30):
            return
    except Exception:
        return


def _gemini_client(model: Any) -> Any:
    """Find Gemini inside a text-model failover chain for Files API features."""
    get_provider = getattr(model, "get_provider", None)
    if callable(get_provider):
        candidate = get_provider("gemini")
        if candidate is not None:
            return candidate
    return model
