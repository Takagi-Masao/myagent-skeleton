from __future__ import annotations

import time
from typing import Any

from .config import Config


class ModelConfigError(RuntimeError):
    pass


class OpenAIModel:
    """Thin wrapper around the OpenAI-compatible chat completions API."""

    def __init__(self, config: Config):
        self.config = config
        if not self.config.api_key:
            raise ModelConfigError(
                "MYAGENT_API_KEY is empty. Copy .env.example to .env and fill your key."
            )
        if not self.config.base_url or not self.config.model:
            raise ModelConfigError("MYAGENT_BASE_URL / MYAGENT_MODEL is empty.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ModelConfigError("openai is not installed: python -m pip install openai") from exc
        self._client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = "auto",
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=tools or None,
                    tool_choice=(tool_choice if tools else None),
                    temperature=0.2,
                )
                return self._normalize(response)
            except Exception as exc:  # noqa: BLE001 - retry only transient errors
                last_error = exc
                status = getattr(exc, "status_code", None)
                if status not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"model call failed: {last_error}")

    def _normalize(self, response: Any) -> dict[str, Any]:
        choice = response.choices[0]
        msg = choice.message
        tool_calls: list[dict] = []
        assistant: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant["tool_calls"] = []
            for call in msg.tool_calls:
                item = {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                assistant["tool_calls"].append(item)
                tool_calls.append(
                    {
                        "id": call.id,
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    }
                )
        usage = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(response.usage, "total_tokens", 0) or 0,
        }
        return {
            "message": assistant,
            "tool_calls": tool_calls,
            "usage": usage,
            "cost": self.config.cost_of(usage),
            "raw": response.model_dump() if hasattr(response, "model_dump") else {},
        }
