"""Small in-process task registry for long-running local operations.

The registry stores only bounded task metadata on disk; results and runners stay
in memory so interview transcripts and uploaded files are not copied into a
durable task log. A process restart marks unfinished work as abandoned, so
callers must treat this as a local status/retry layer rather than a distributed
job queue.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
import threading
import uuid
from typing import Any, Callable, Dict, Optional


TERMINAL_STATES = {"succeeded", "failed", "timed_out", "abandoned", "cancelled"}


class TaskFailure(RuntimeError):
    """An error whose message is explicitly safe to show to the caller."""

    def __init__(self, message: str):
        self.public_message = str(message or "任务执行失败，请稍后重试。")[:400]
        super().__init__(self.public_message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskRegistry:
    """Run bounded local tasks and expose a JSON-safe status snapshot."""

    def __init__(self, max_workers: int = 2, max_tasks: int = 100, max_attempts: int = 2, timeout_seconds: float = 900, path: Optional[str] = None, event_sink: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.max_tasks = max(10, min(500, int(max_tasks)))
        self.max_attempts = max(1, min(3, int(max_attempts)))
        self.timeout_seconds = max(0.01, min(3600.0, float(timeout_seconds)))
        self.path = os.path.realpath(path) if path else ""
        self._event_sink = event_sink
        self._lock = threading.RLock()
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._runners: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._futures: Dict[str, Any] = {}
        self._timers: Dict[str, threading.Timer] = {}
        self._executor = ThreadPoolExecutor(max_workers=max(1, min(8, int(max_workers))))
        self._load_metadata()

    def submit(self, kind: str, runner: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        if not callable(runner):
            raise TypeError("task runner must be callable")
        task_id = "task_" + uuid.uuid4().hex
        now = _now()
        with self._lock:
            self._prune_locked()
            if len(self._tasks) >= self.max_tasks:
                raise RuntimeError("本地任务队列已满，请稍后重试。")
            task = {
                "id": task_id,
                "kind": str(kind or "task")[:80],
                "status": "queued",
                "attempt": 0,
                "max_attempts": self.max_attempts,
                "created_at": now,
                "updated_at": now,
                "error": "",
                "result": None,
            }
            self._tasks[task_id] = task
            self._runners[task_id] = runner
            self._persist_locked()
            self._emit("task_submitted", task)
        future = self._executor.submit(self._execute, task_id)
        with self._lock:
            self._futures[task_id] = future
        return self.get(task_id) or {}

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(str(task_id))
            return self._public(task) if task else None

    def list(self) -> list:
        with self._lock:
            return [self._public(task) for task in self._tasks.values()]

    def summary(self) -> Dict[str, int]:
        with self._lock:
            counts = {"total": len(self._tasks), "queued": 0, "running": 0, "cancel_requested": 0, "cancelled": 0, "failed": 0, "timed_out": 0, "abandoned": 0}
            for task in self._tasks.values():
                status = str(task.get("status", ""))
                if status in counts:
                    counts[status] += 1
            return counts

    def retry(self, task_id: str) -> Optional[Dict[str, Any]]:
        task_id = str(task_id)
        with self._lock:
            task = self._tasks.get(task_id)
            runner = self._runners.get(task_id)
            if not task or not runner:
                return None
            if task["status"] != "failed":
                raise ValueError("只有失败任务可以重试。")
            if int(task.get("attempt", 0)) >= int(task.get("max_attempts", self.max_attempts)):
                raise ValueError("任务已达到最大重试次数。")
            task["status"] = "queued"
            task["error"] = ""
            task["result"] = None
            task["updated_at"] = _now()
            self._persist_locked()
            self._emit("task_retry_queued", task)
        future = self._executor.submit(self._execute, task_id)
        with self._lock:
            self._futures[task_id] = future
        return self.get(task_id)

    def cancel(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Cancel queued work or request cooperative cancellation for running work."""
        task_id = str(task_id)
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            status = task.get("status")
            if status in TERMINAL_STATES:
                raise ValueError("任务已经结束，不能取消。")
            if status == "cancel_requested":
                return self._public(task)
            task["error"] = "用户已请求取消；当前网络调用可能仍在收尾。"
            if status == "queued":
                task["status"] = "cancelled"
                future = self._futures.get(task_id)
                if future is not None:
                    future.cancel()
            else:
                task["status"] = "cancel_requested"
            task["updated_at"] = _now()
            self._persist_locked()
            self._emit("task_cancel_requested" if status == "running" else "task_cancelled", task)
            return self._public(task)

    def _execute(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            runner = self._runners.get(task_id)
            if not task or not runner or task.get("status") != "queued":
                return
            task["status"] = "running"
            task["attempt"] = int(task.get("attempt", 0)) + 1
            task["updated_at"] = _now()
            self._persist_locked()
            self._emit("task_started", task)
            timer = threading.Timer(self.timeout_seconds, self._timeout, args=(task_id, task["attempt"]))
            timer.daemon = True
            self._timers[task_id] = timer
            timer.start()
        try:
            result = runner()
            if not isinstance(result, dict):
                raise RuntimeError("任务返回格式无效。")
        except Exception as exc:
            with self._lock:
                task = self._tasks.get(task_id)
                if task and task.get("status") == "cancel_requested":
                    task["status"] = "cancelled"
                    task["updated_at"] = _now()
                    self._cancel_timer_locked(task_id)
                    self._persist_locked()
                    self._emit("task_cancelled", task)
                elif task and task.get("status") == "running":
                    task["status"] = "failed"
                    task["error"] = getattr(exc, "public_message", "任务执行失败，请稍后重试。")[:400]
                    task["updated_at"] = _now()
                    self._cancel_timer_locked(task_id)
                    self._persist_locked()
                    self._emit("task_failed", task, {"error_code": type(exc).__name__})
            return
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.get("status") == "cancel_requested":
                task["status"] = "cancelled"
                task["result"] = None
                task["updated_at"] = _now()
                self._cancel_timer_locked(task_id)
                self._persist_locked()
                self._emit("task_cancelled", task)
            elif task and task.get("status") == "running":
                task["status"] = "succeeded"
                task["result"] = result
                task["updated_at"] = _now()
                self._cancel_timer_locked(task_id)
                self._persist_locked()
                self._emit("task_succeeded", task)

    def _timeout(self, task_id: str, attempt: int) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.get("status") not in {"running", "cancel_requested"} or int(task.get("attempt", 0)) != int(attempt):
                return
            if task.get("status") == "cancel_requested":
                task["status"] = "cancelled"
                task["error"] = "用户已请求取消；后台操作超过收尾时间。"
                event = "task_cancelled"
            else:
                task["status"] = "timed_out"
                task["error"] = "任务超过本地超时上限；后台操作可能仍在收尾，请检查结果后再继续。"
                event = "task_timed_out"
            task["updated_at"] = _now()
            self._timers.pop(task_id, None)
            self._persist_locked()
            self._emit(event, task)

    def _cancel_timer_locked(self, task_id: str) -> None:
        timer = self._timers.pop(task_id, None)
        if timer:
            timer.cancel()

    def _prune_locked(self) -> None:
        if len(self._tasks) < self.max_tasks:
            return
        removable = [
            task_id for task_id, task in self._tasks.items()
            if task.get("status") in TERMINAL_STATES
        ]
        for task_id in removable[: max(1, len(removable) // 2)]:
            self._tasks.pop(task_id, None)
            self._runners.pop(task_id, None)
            self._futures.pop(task_id, None)
            self._timers.pop(task_id, None)
        self._persist_locked()

    def _load_metadata(self) -> None:
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            rows = payload.get("tasks", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                return
        except (OSError, UnicodeError, json.JSONDecodeError):
            return
        with self._lock:
            for row in rows[-self.max_tasks:]:
                if not isinstance(row, dict) or not str(row.get("id", "")):
                    continue
                try:
                    attempt = int(row.get("attempt", 0) or 0)
                except (TypeError, ValueError):
                    attempt = 0
                try:
                    max_attempts = int(row.get("max_attempts", self.max_attempts) or self.max_attempts)
                except (TypeError, ValueError):
                    max_attempts = self.max_attempts
                task = {
                    "id": str(row.get("id", ""))[:100],
                    "kind": str(row.get("kind", "task"))[:80],
                    "status": str(row.get("status", "abandoned")),
                    "attempt": max(0, min(3, attempt)),
                    "max_attempts": max(1, min(3, max_attempts)),
                    "created_at": str(row.get("created_at", "")),
                    "updated_at": str(row.get("updated_at", "")),
                    "error": str(row.get("error", ""))[:400],
                    "result": None,
                }
                if task["status"] not in {"queued", "running", "cancel_requested", "cancelled", "succeeded", "failed", "timed_out", "abandoned"}:
                    task["status"] = "abandoned"
                    task["error"] = "任务状态文件包含未知状态，请重新提交。"
                if task["status"] in {"queued", "running"}:
                    task["status"] = "abandoned"
                    task["error"] = "应用重启时任务未完成，无法恢复原始输入；请重新提交。"
                    task["updated_at"] = _now()
                self._tasks[task["id"]] = task
            self._persist_locked()

    def _persist_locked(self) -> None:
        if not self.path:
            return

        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            temporary_path = self.path + ".tmp"
            with open(temporary_path, "w", encoding="utf-8") as handle:
                json.dump({"task_store_version": "1.0", "tasks": [self._disk_record(task) for task in self._tasks.values()]}, handle, ensure_ascii=False, indent=2)
            os.replace(temporary_path, self.path)
        except OSError:
            # Task metadata must not turn a completed model call into a failed
            # user operation when the optional local status file is unwritable.
            return

    def _emit(self, event: str, task: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> None:
        if not self._event_sink:
            return
        fields = {
            "task_id": task.get("id"),
            "kind": task.get("kind"),
            "status": task.get("status"),
            "attempt": task.get("attempt"),
            "max_attempts": task.get("max_attempts"),
        }
        fields.update(extra or {})
        try:
            self._event_sink(event, fields)
        except Exception:
            return

    @staticmethod
    def _disk_record(task: Dict[str, Any]) -> Dict[str, Any]:
        return {key: task.get(key) for key in ("id", "kind", "status", "attempt", "max_attempts", "created_at", "updated_at", "error")}

    @staticmethod
    def _public(task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if task is None:
            return None
        return {
            "id": task["id"],
            "kind": task["kind"],
            "status": task["status"],
            "attempt": task["attempt"],
            "max_attempts": task["max_attempts"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"],
            "error": task.get("error", ""),
            "result": task.get("result") if task.get("status") == "succeeded" else None,
        }
