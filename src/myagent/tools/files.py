from __future__ import annotations

from .base import (
    ToolContext,
    ToolResult,
    resolve_workspace_path,
    truncate_output,
)


class ReadFileTool:
    name = "read_file"
    description = "Read a text file slice with line numbers. Use start_line/end_line for large files."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer", "description": "1-based, default 1"},
            "end_line": {"type": "integer", "description": "inclusive, default start+199"},
        },
        "required": ["path"],
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        try:
            path = resolve_workspace_path(ctx.workspace, args.get("path"))
        except ValueError as exc:
            return ToolResult(-1, error=str(exc))
        if not path.is_file():
            return ToolResult(-1, error=f"not a file: {args.get('path')}")
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        start = max(1, int(args.get("start_line", 1) or 1))
        end = int(args.get("end_line", start + 199) or start + 199)
        end = min(end, start + 199, len(lines))
        body = "\n".join(f"{i:4d}  {lines[i - 1]}" for i in range(start, end + 1))
        body, truncated = truncate_output(body, ctx.max_output_chars)
        return ToolResult(0, body, truncated=truncated)


class WriteFileTool:
    name = "write_file"
    description = "Write or append a UTF-8 text file inside the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "append": {"type": "boolean", "description": "append instead of overwrite"},
        },
        "required": ["path", "content"],
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        try:
            path = resolve_workspace_path(ctx.workspace, args.get("path"))
        except ValueError as exc:
            return ToolResult(-1, error=str(exc))
        content = args.get("content", "")
        if not isinstance(content, str):
            return ToolResult(-1, error="'content' must be a string")
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.get("append") else "w"
        with path.open(mode, encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        return ToolResult(0, f"wrote {len(content)} chars to {path.relative_to(ctx.workspace)}")


class ListDirTool:
    name = "list_dir"
    description = "List files and directories inside the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "default '.'"},
            "max_entries": {"type": "integer", "description": "default 200"},
        },
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        try:
            path = resolve_workspace_path(ctx.workspace, args.get("path") or ".")
        except ValueError as exc:
            return ToolResult(-1, error=str(exc))
        if not path.is_dir():
            return ToolResult(-1, error=f"not a directory: {args.get('path')}")
        limit = max(1, int(args.get("max_entries", 200) or 200))
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        lines = []
        for entry in entries[:limit]:
            if entry.is_dir():
                lines.append(f"d  {entry.name}/")
            else:
                lines.append(f"f  {entry.name}  ({entry.stat().st_size} bytes)")
        if len(entries) > limit:
            lines.append(f"... {len(entries) - limit} more entries")
        body, truncated = truncate_output("\n".join(lines), ctx.max_output_chars)
        return ToolResult(0, body, truncated=truncated)
