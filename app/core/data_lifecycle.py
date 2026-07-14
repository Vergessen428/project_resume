"""Versioned local backup bundles for the single-user data stores."""

import json
import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


BACKUP_VERSION = "1.1"
SUPPORTED_BACKUP_VERSIONS = {"1.0", BACKUP_VERSION}
DEFAULT_BACKUP_KEEP = 7
RECOVERY_MARKER_VERSION = "1.0"
RECOVERY_MARKER_NAME = "recovery-required.json"
_BACKUP_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def create_backup(data_root: str, bundle: Dict[str, Any], keep_last: Any = DEFAULT_BACKUP_KEEP) -> Dict[str, Any]:
    backup_dir = os.path.join(data_root, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    backup_id = "autumn-backup-%s-%s" % (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:8])
    payload = {"backup_version": BACKUP_VERSION, "backup_id": backup_id, "created_at": created_at, **bundle}
    payload["integrity"] = {"algorithm": "sha256", "digest": _digest(payload)}
    path = os.path.join(backup_dir, backup_id + ".json")
    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(temporary_path, path)
    summary = backup_summary(payload, path)
    summary["rotation"] = rotate_backups(data_root, keep_last)
    return summary


def normalise_backup_keep(value: Any) -> int:
    """Bound the number of verified backups retained by an explicit policy."""
    try:
        keep = int(value)
    except (TypeError, ValueError):
        keep = DEFAULT_BACKUP_KEEP
    return max(1, min(100, keep))


def rotate_backups(data_root: str, keep_last: Any = DEFAULT_BACKUP_KEEP) -> Dict[str, Any]:
    """Delete only old, verified backups; never rotate away an uncertain copy."""
    keep = normalise_backup_keep(keep_last)
    all_backups = list_backups(data_root)
    verified = [item for item in all_backups if item.get("integrity_status") == "verified"]
    unverified_count = len(all_backups) - len(verified)
    verified.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("backup_id", ""))), reverse=True)
    deleted = []
    failures = []
    for item in verified[keep:]:
        path = str(item.get("path", ""))
        if not path or os.path.dirname(os.path.realpath(path)) != os.path.realpath(os.path.join(data_root, "backups")):
            failures.append({"backup_id": item.get("backup_id", ""), "reason": "备份路径不在受控目录内。"})
            continue
        try:
            os.remove(path)
            deleted.append(str(item.get("backup_id", "")))
        except OSError as exc:
            failures.append({"backup_id": item.get("backup_id", ""), "reason": str(exc)[:240]})
    return {
        "keep_last": keep,
        "verified_count": len(verified),
        "deleted": deleted,
        "deleted_count": len(deleted),
        "failures": failures,
        "unverified_preserved": unverified_count,
    }


def list_backups(data_root: str) -> List[Dict[str, Any]]:
    backup_dir = os.path.join(data_root, "backups")
    if not os.path.isdir(backup_dir):
        return []
    result = []
    for name in sorted(os.listdir(backup_dir), reverse=True):
        if not name.endswith(".json") or not _BACKUP_ID.match(name[:-5]):
            continue
        path = os.path.join(backup_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("备份不是对象。")
            result.append(backup_summary(payload, path))
        except (OSError, ValueError, json.JSONDecodeError):
            result.append({
                "backup_id": name[:-5],
                "created_at": "",
                "path": path,
                "integrity_status": "unreadable",
                "counts": {"interviews": 0, "resumes": 0, "research": 0},
            })
    return result


def read_backup(data_root: str, backup_id: str) -> Dict[str, Any]:
    backup_id = str(backup_id or "").strip()
    if not _BACKUP_ID.match(backup_id):
        raise ValueError("备份标识无效。")
    path = os.path.join(data_root, "backups", backup_id + ".json")
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or payload.get("backup_version") not in SUPPORTED_BACKUP_VERSIONS:
        raise ValueError("备份版本不受支持。")
    if str(payload.get("backup_id", "")) != backup_id:
        raise ValueError("备份标识与文件内容不一致。")
    if payload.get("backup_version") == BACKUP_VERSION:
        integrity = payload.get("integrity") if isinstance(payload.get("integrity"), dict) else {}
        if integrity.get("algorithm") != "sha256" or integrity.get("digest") != _digest(payload):
            raise ValueError("备份完整性校验失败，文件可能已被修改。")
    for key in ("interviews", "resumes", "research", "memory_overrides"):
        if key not in payload:
            raise ValueError("备份缺少 %s 数据。" % key)
    if not isinstance(payload["interviews"], list) or not isinstance(payload["resumes"], list) or not isinstance(payload["research"], list) or not isinstance(payload["memory_overrides"], dict):
        raise ValueError("备份数据结构无效。")
    if "memory_override_events" not in payload:
        # Backward-compatible default for backups created before governance
        # event history was added.
        payload["memory_override_events"] = []
    if not isinstance(payload["memory_override_events"], list) or not all(isinstance(item, dict) for item in payload["memory_override_events"]):
        raise ValueError("备份记忆治理事件结构无效。")
    return payload


def backup_summary(payload: Dict[str, Any], path: str) -> Dict[str, Any]:
    version = str(payload.get("backup_version", ""))
    if version == BACKUP_VERSION:
        integrity = payload.get("integrity") if isinstance(payload.get("integrity"), dict) else {}
        integrity_status = "verified" if integrity.get("algorithm") == "sha256" and integrity.get("digest") == _digest(payload) else "corrupt"
    elif version == "1.0":
        integrity_status = "legacy_unverified"
    else:
        integrity_status = "unsupported"
    return {
        "backup_id": str(payload.get("backup_id", "")),
        "created_at": str(payload.get("created_at", "")),
        "path": path,
        "integrity_status": integrity_status,
        "counts": {
            "interviews": len(payload.get("interviews", []) if isinstance(payload.get("interviews"), list) else []),
            "resumes": len(payload.get("resumes", []) if isinstance(payload.get("resumes"), list) else []),
            "research": len(payload.get("research", []) if isinstance(payload.get("research"), list) else []),
        },
    }


def mark_recovery_required(
    data_root: str,
    operation: str,
    reason: str,
    rollback_errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Persist a small, non-sensitive startup signal after rollback failure."""
    marker = {
        "marker_version": RECOVERY_MARKER_VERSION,
        "status": "recovery_required",
        "operation": str(operation or "unknown")[:80],
        "reason": str(reason or "未知恢复错误")[:500],
        "rollback_errors": [str(item)[:300] for item in (rollback_errors or [])[:8]],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write_recovery_marker(data_root, marker)
    return marker


def clear_recovery_marker(data_root: str) -> bool:
    path = os.path.join(data_root, RECOVERY_MARKER_NAME)
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def inspect_startup_recovery(data_root: str, store_paths: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Check recovery markers, abandoned atomic temp files, and store JSON shape."""
    issues = []
    marker_path = os.path.join(data_root, RECOVERY_MARKER_NAME)
    marker = None
    if os.path.exists(marker_path):
        try:
            with open(marker_path, "r", encoding="utf-8") as handle:
                marker = json.load(handle)
            if not isinstance(marker, dict) or marker.get("status") != "recovery_required":
                issues.append({"kind": "invalid_recovery_marker", "path": marker_path, "reason": "恢复标记结构无效。"})
            else:
                issues.append({"kind": "recovery_marker", "path": marker_path, "reason": str(marker.get("reason", "需要恢复"))[:500]})
        except (OSError, UnicodeError, json.JSONDecodeError):
            issues.append({"kind": "invalid_recovery_marker", "path": marker_path, "reason": "恢复标记不可读取。"})

    for label, path in (store_paths or {}).items():
        path = os.path.realpath(str(path))
        temporary_path = path + ".tmp"
        if os.path.exists(temporary_path):
            issues.append({"kind": "orphaned_temp_file", "store": str(label), "path": temporary_path, "reason": "发现未完成的原子写入临时文件。"})
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            expected = dict if str(label) in {"memory_overrides", "tasks"} else list
            if not isinstance(value, expected):
                issues.append({"kind": "invalid_store_shape", "store": str(label), "path": path, "reason": "本地数据结构不是预期类型。"})
        except (OSError, UnicodeError, json.JSONDecodeError):
            issues.append({"kind": "unreadable_store", "store": str(label), "path": path, "reason": "本地数据文件不可读取。"})

    return {
        "status": "recovery_required" if issues else "ok",
        "recovery_required": bool(issues),
        "marker": marker,
        "issues": issues[:20],
    }


def _write_recovery_marker(data_root: str, marker: Dict[str, Any]) -> None:
    os.makedirs(data_root, exist_ok=True)
    path = os.path.join(data_root, RECOVERY_MARKER_NAME)
    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump(marker, handle, ensure_ascii=False, indent=2)
    os.replace(temporary_path, path)


def _digest(payload: Dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "integrity"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
