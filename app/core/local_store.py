"""Shared failure-closed helpers for the local JSON stores."""

import json
import os
from typing import Any, Type


class StoreDataError(RuntimeError):
    """Raised when a local store cannot be trusted as structured data."""


def read_json_value(path: str, default: Any, expected_type: Type[Any], label: str) -> Any:
    """Read one store without silently converting corruption into an empty store."""
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StoreDataError("%s数据文件损坏或不可读，请先恢复备份：%s" % (label, os.path.basename(path))) from exc
    if not isinstance(value, expected_type):
        raise StoreDataError("%s数据文件结构无效，请先恢复备份：%s" % (label, os.path.basename(path)))
    return value
