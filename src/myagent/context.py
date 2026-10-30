from __future__ import annotations

import json


def estimate_tokens(messages: list[dict]) -> int:
    """Rough estimate: 4 characters per token. Good enough for a threshold."""
    chars = 0
    for message in messages:
        chars += len(str(message.get("content", "")))
        for call in message.get("tool_calls", []) or []:
            chars += len(json.dumps(call, ensure_ascii=False))
    return max(1, chars // 4)


def maybe_compact(
    messages: list[dict],
    model,
    max_tokens: int,
    keep_last: int = 6,
) -> tuple[list[dict], dict | None]:
    """Summarize the middle of the conversation when it exceeds max_tokens.

    Contract:
    - below threshold -> return (messages, None), do not call the model
    - keep the first system message, the first user message (task), and the
      last `keep_last` messages
    - summarize the middle with model.chat(...); tools=None
    - return (compacted, record) where record has tokens_before/after,
      messages_before/after, summary
    """
    raise NotImplementedError("H5 (Gold): implement context.maybe_compact() - see the docstring above")
