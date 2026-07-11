import os
from typing import Any, Dict


SENSITIVE_NAMES = {
    ".env",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SENSITIVE_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

WRITABLE_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
}


class PolicyError(Exception):
    pass


class PolicyEngine:
    def __init__(self, workspace_root: str, max_tool_calls: int = 10) -> None:
        self.workspace_root = os.path.realpath(workspace_root)
        self.max_tool_calls = max_tool_calls

    def check(self, tool_name: str, args: Dict[str, Any], current_tool_calls: int) -> None:
        if current_tool_calls >= self.max_tool_calls:
            raise PolicyError("Tool call limit exceeded.")

        if tool_name in ("read_file", "write_file", "list_files"):
            input_path = str(args.get("path", "."))
            resolved = self.resolve_workspace_path(input_path)

            if tool_name in ("read_file", "write_file"):
                self.assert_not_sensitive(resolved)

            if tool_name == "write_file":
                self.assert_writable_extension(resolved)

    def resolve_workspace_path(self, input_path: str) -> str:
        if not input_path or "\x00" in input_path:
            raise PolicyError("Invalid path.")

        if input_path.startswith("~"):
            raise PolicyError("Home-directory paths are not allowed.")

        if os.path.isabs(input_path):
            raise PolicyError("Absolute paths are not allowed.")

        candidate = os.path.realpath(os.path.join(self.workspace_root, input_path))
        root = self.workspace_root

        if candidate != root and not candidate.startswith(root + os.sep):
            raise PolicyError("Path escapes workspace.")

        return candidate

    def assert_not_sensitive(self, resolved_path: str) -> None:
        parts = resolved_path.split(os.sep)
        base = os.path.basename(resolved_path)
        _, ext = os.path.splitext(base)

        if base in SENSITIVE_NAMES or ext in SENSITIVE_EXTENSIONS:
            raise PolicyError("Sensitive file access is not allowed.")

        for part in parts:
            if part.startswith(".") and part not in (".", ".."):
                raise PolicyError("Hidden paths are not allowed.")

    def assert_writable_extension(self, resolved_path: str) -> None:
        _, ext = os.path.splitext(resolved_path)
        if ext not in WRITABLE_EXTENSIONS:
            raise PolicyError("Only .md, .txt, and .json files can be written.")

