from __future__ import annotations

from pathlib import Path

from .events import read_events


def resume(path: Path) -> list[dict]:
    """Rebuild the message list from a JSONL session.

    Contract:
    - read all events; keep payload["message"] for type == "message"
    - if the last message is an assistant with tool_calls and some calls have
      no matching tool message, append an interrupted tool observation for each
      missing call (same tool_call_id, content says "interrupted")
    - return [] for an empty file
    """
    raise NotImplementedError("H4 (Silver): implement session.resume() - see the docstring above")
