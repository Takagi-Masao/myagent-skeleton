from __future__ import annotations

import json

from .base import Tool, ToolContext, ToolResult, truncate_output


def _parse_arguments(args: dict | str | None) -> tuple[dict | None, str | None]:
    """Return (arguments, error). Blank input means "no arguments"."""
    if args is None:
        return {}, None
    if isinstance(args, str):
        text = args.strip()
        if not text:
            return {}, None
        try:
            args = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f"invalid JSON in tool arguments: {exc}"
    if not isinstance(args, dict):
        return None, f"tool arguments must be a JSON object, got {type(args).__name__}"
    return args, None


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, args: dict | str, ctx: ToolContext) -> ToolResult:
        """Turn one tool call into an observation. Never raise into the agent loop.

        Contract:
        - unknown tool -> ToolResult(-1, error="unknown tool ... available: ...")
        - args is a JSON string -> parse it; invalid JSON -> error observation
        - args is not a dict -> error observation
        - tool.run raises -> error observation (type + message), not a crash
        - tool returns a non-ToolResult -> error observation
        - truncate result.output to ctx.max_output_chars and set truncated
        """
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools)) or "(none)"
            return ToolResult(-1, error=f"unknown tool '{name}'; available: {available}")

        parsed, error = _parse_arguments(args)
        if error is not None:
            return ToolResult(-1, error=error)

        try:
            result = tool.run(parsed, ctx)
        except Exception as exc:  # noqa: BLE001 - every tool failure becomes an observation
            return ToolResult(-1, error=f"{type(exc).__name__}: {exc}")

        if not isinstance(result, ToolResult):
            return ToolResult(
                -1,
                error=f"tool '{name}' returned {type(result).__name__}, expected ToolResult",
            )

        output, truncated = truncate_output(result.output or "", ctx.max_output_chars)
        if truncated:
            result.output = output
            result.truncated = True
        return result
