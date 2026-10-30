from __future__ import annotations

from .base import ToolContext, ToolResult


class SubmitTool:
    name = "submit"
    description = "Finish the task. Call this only when the task is complete."
    parameters = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "One paragraph: what you did, what you verified, which files changed.",
            }
        },
        "required": ["summary"],
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        summary = args.get("summary", "")
        if not isinstance(summary, str) or not summary.strip():
            return ToolResult(-1, error="missing 'summary'")
        ctx.submitted = True
        ctx.submission = summary
        return ToolResult(0, f"submitted: {summary}")
