from __future__ import annotations

from .base import Tool, ToolContext, ToolResult


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
        raise NotImplementedError("H2: implement ToolRegistry.execute() - see the docstring above")
