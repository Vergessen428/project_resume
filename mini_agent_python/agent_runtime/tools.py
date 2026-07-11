import os
from typing import Any, Dict, List

from .types import Tool, ToolContext, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list(self) -> List[Tool]:
        return list(self._tools.values())

    def execute(self, name: str, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, content="", error="Unknown tool: %s" % name)

        try:
            return tool.handler(args, ctx)
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))


def build_default_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="list_files",
            description="List text files inside the workspace.",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path."}
                },
            },
            handler=list_files,
        )
    )
    registry.register(
        Tool(
            name="read_file",
            description="Read a UTF-8 text file inside the workspace.",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."}
                },
                "required": ["path"],
            },
            handler=read_file,
        )
    )
    registry.register(
        Tool(
            name="write_file",
            description="Write UTF-8 text to a file inside the workspace.",
            schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "content": {"type": "string", "description": "File content."},
                },
                "required": ["path", "content"],
            },
            handler=write_file,
        )
    )
    return registry


def list_files(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    rel_path = str(args.get("path", "."))
    root = os.path.realpath(ctx.workspace_root)
    base = os.path.realpath(os.path.join(root, rel_path))
    files: List[str] = []

    if not os.path.isdir(base):
        return ToolResult(ok=False, content="", error="Directory does not exist.")

    for current, dirs, filenames in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            full_path = os.path.join(current, filename)
            rel = os.path.relpath(full_path, root)
            files.append(rel)

    files.sort()
    return ToolResult(ok=True, content="\n".join(files))


def read_file(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    rel_path = str(args.get("path", ""))
    full_path = os.path.realpath(os.path.join(ctx.workspace_root, rel_path))

    if not os.path.isfile(full_path):
        return ToolResult(ok=False, content="", error="File does not exist.")

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    if len(content) > 12000:
        content = content[:12000] + "\n\n[TRUNCATED]"

    return ToolResult(ok=True, content=content)


def write_file(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    rel_path = str(args.get("path", ""))
    content = str(args.get("content", ""))
    full_path = os.path.realpath(os.path.join(ctx.workspace_root, rel_path))
    parent = os.path.dirname(full_path)
    os.makedirs(parent, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return ToolResult(ok=True, content="Wrote %s" % rel_path)

