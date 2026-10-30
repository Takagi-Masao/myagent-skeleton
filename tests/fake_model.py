from __future__ import annotations

import json
from typing import Any


class FakeModel:
    """Scripted model: returns pre-built responses, never calls the network."""

    def __init__(self, script: list[dict[str, Any]]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        self.calls.append(messages)
        if not self.script:
            return {
                "message": {"role": "assistant", "content": "done"},
                "tool_calls": [],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                "cost": 0.0,
            }
        item = self.script.pop(0)
        if "raise" in item:
            raise RuntimeError(item["raise"])

        content = item.get("content", "")
        raw_calls = item.get("tool_calls", []) or []
        assistant: dict[str, Any] = {"role": "assistant", "content": content}
        normalized = []
        if raw_calls:
            assistant["tool_calls"] = []
            for call in raw_calls:
                arguments = call.get("arguments", {})
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                assistant["tool_calls"].append(
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["name"], "arguments": arguments},
                    }
                )
                normalized.append(
                    {"id": call["id"], "name": call["name"], "arguments": arguments}
                )
        usage = item.get("usage", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
        return {
            "message": assistant,
            "tool_calls": normalized,
            "usage": usage,
            "cost": item.get("cost", 0.0),
            "raw": {},
        }
