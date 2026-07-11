import json
import os
import time
from typing import Any, Dict


class JsonlLogger:
    def __init__(self, logs_dir: str) -> None:
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)

    def write(self, run_id: str, event_type: str, data: Dict[str, Any]) -> None:
        event = {
            "time": int(time.time()),
            "type": event_type,
            "data": data,
        }
        path = os.path.join(self.logs_dir, "%s.jsonl" % run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

