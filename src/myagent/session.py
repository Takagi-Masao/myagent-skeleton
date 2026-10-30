from __future__ import annotations

from pathlib import Path

from .events import read_events

INTERRUPTED = "interrupted: the session ended before this tool call returned a result"


def _messages_from(path: Path) -> list[dict]:
    """Collect payload["message"] from every 'message' event, in order."""
    messages: list[dict] = []
    for event in read_events(path):
        if event.get("type") != "message":
            continue
        message = (event.get("payload") or {}).get("message")
        if isinstance(message, dict):
            messages.append(message)
    return messages


def _unanswered_tool_calls(messages: list[dict]) -> list[str]:
    """Tool calls of the newest assistant turn that still have no tool result.

    Scanning backwards (instead of only looking at messages[-1]) also repairs a
    session that died halfway through a multi-call response: the calls answered
    before the crash are kept, the rest get an interrupted observation.
    """
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") != "assistant" or not message.get("tool_calls"):
            continue
        answered = {
            later.get("tool_call_id")
            for later in messages[index + 1:]
            if later.get("role") == "tool"
        }
        return [
            call["id"]
            for call in message["tool_calls"]
            if call.get("id") and call["id"] not in answered
        ]
    return []


def resume(path: Path) -> list[dict]:
    """Rebuild the message list from a JSONL session.

    Contract:
    - read all events; keep payload["message"] for type == "message"
    - if the last message is an assistant with tool_calls and some calls have
      no matching tool message, append an interrupted tool observation for each
      missing call (same tool_call_id, content says "interrupted")
    - return [] for an empty file
    """
    messages = _messages_from(path)
    for call_id in _unanswered_tool_calls(messages):
        messages.append({"role": "tool", "tool_call_id": call_id, "content": INTERRUPTED})
    return messages
