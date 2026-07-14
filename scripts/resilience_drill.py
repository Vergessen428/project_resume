#!/usr/bin/env python3
"""Run deterministic local-data and task lifecycle failure drills.

The drill uses a temporary APP_DATA_DIR and the production restore/task code.
It never touches a user's real data and never calls a model or the network.
"""

from contextlib import contextmanager
import json
import os
import sys
import tempfile
import threading
import time
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))


def wait_for(registry, task_id, expected, timeout=2.0):
    deadline = time.time() + timeout
    current = registry.get(task_id)
    while time.time() < deadline:
        current = registry.get(task_id)
        if current and current.get("status") == expected:
            return current
        time.sleep(0.01)
    raise AssertionError("task %s did not reach %s: %s" % (task_id, expected, current))


@contextmanager
def isolated_app_data():
    with tempfile.TemporaryDirectory(prefix="autumn-resilience-") as data_root:
        os.environ["APP_DATA_DIR"] = data_root
        os.environ["APP_ACCESS_TOKEN"] = ""
        yield data_root


def run_drill():
    with isolated_app_data() as data_root:
        # Import after APP_DATA_DIR is set so restore_backup_bundle uses only
        # this disposable directory.
        import web_app
        from core.data_lifecycle import clear_recovery_marker, create_backup, list_backups, read_backup
        from core.task_store import TaskRegistry

        baseline = {
            "interviews": [{"id": "drill-interview"}],
            "resumes": [],
            "research": [{"id": "drill-research"}],
            "memory_overrides": {},
        }
        tamper = create_backup(data_root, baseline)
        tamper_path = tamper["path"]
        with open(tamper_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["interviews"][0]["id"] = "tampered"
        with open(tamper_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        tampered_summary = next(item for item in list_backups(data_root) if item["backup_id"] == tamper["backup_id"])
        assert tampered_summary["integrity_status"] == "corrupt"
        try:
            read_backup(data_root, tamper["backup_id"])
        except ValueError as exc:
            assert "完整性" in str(exc)
        else:
            raise AssertionError("tampered backup was accepted")

        # Seed the production stores, then force both the replacement and
        # rollback write for one store to fail. The production path must leave
        # the recovery marker for the next startup.
        web_app.STORE.create({"company": "演练", "role": "PM", "transcript": "baseline"})
        replacement = create_backup(data_root, baseline)
        with patch.object(
            web_app.RESEARCH_STORE,
            "replace_all",
            side_effect=[RuntimeError("disk error"), RuntimeError("rollback error")],
        ):
            try:
                web_app.restore_backup_bundle(read_backup(data_root, replacement["backup_id"]))
            except RuntimeError as exc:
                assert "回滚" in str(exc)
            else:
                raise AssertionError("restore failure was not surfaced")
        recovery = web_app.startup_recovery_status()
        assert recovery["recovery_required"] is True
        clear_recovery_marker(data_root)

        timeout_registry = TaskRegistry(max_workers=1, timeout_seconds=0.03)
        try:
            timeout_task = timeout_registry.submit("drill-timeout", lambda: (time.sleep(0.08), {"late": True})[1])
            timeout_result = wait_for(timeout_registry, timeout_task["id"], "timed_out")
            time.sleep(0.08)
            assert timeout_result["result"] is None
            assert timeout_registry.get(timeout_task["id"])["result"] is None
        finally:
            timeout_registry._executor.shutdown(wait=True)

        cancel_registry = TaskRegistry(max_workers=1)
        started = threading.Event()
        release = threading.Event()

        def slow_runner():
            started.set()
            release.wait(1)
            return {"late": True}

        try:
            cancel_task = cancel_registry.submit("drill-cancel", slow_runner)
            assert started.wait(1)
            requested = cancel_registry.cancel(cancel_task["id"])
            assert requested["status"] == "cancel_requested"
            release.set()
            cancelled = wait_for(cancel_registry, cancel_task["id"], "cancelled")
            assert cancelled["result"] is None
        finally:
            release.set()
            cancel_registry._executor.shutdown(wait=True)

    return {
        "ok": True,
        "scenarios": {
            "backup_tamper_rejected": "passed",
            "restore_rollback_failure_marks_recovery": "passed",
            "task_timeout_discards_late_result": "passed",
            "task_cancel_discards_late_result": "passed",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_drill(), ensure_ascii=False, sort_keys=True))
