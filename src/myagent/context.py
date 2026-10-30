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
    if not messages:
        return messages, None
    tokens_before = estimate_tokens(messages)
    if max_tokens <= 0 or tokens_before <= max_tokens:
        return messages, None

    # Keep the system prompt and the task, then the newest `keep_last` messages.
    head_count = 1 if messages[0].get("role") == "system" else 0
    if len(messages) > head_count and messages[head_count].get("role") == "user":
        head_count += 1
    tail_start = max(head_count, len(messages) - max(0, keep_last))
    head = messages[:head_count]
    middle = messages[head_count:tail_start]
    tail = messages[tail_start:]
    if not middle:
        return messages, None

    transcript = "\n\n".join(
        f"{message.get('role', '?')}: {str(message.get('content', ''))[:2000]}"
        for message in middle
    )
    response = model.chat(
        [
            {
                "role": "system",
                "content": (
                    "You compress an agent transcript. Keep the task, decisions taken, "
                    "files touched, errors and open TODOs. Reply with the summary only."
                ),
            },
            {
                "role": "user",
                "content": f"Summarize these {len(middle)} messages:\n\n{transcript}",
            },
        ],
        tools=None,
    )
    summary = str((response.get("message") or {}).get("content") or "").strip()
    if not summary:
        return messages, None

    summary_message = {
        "role": "user",
        "content": f"[context compacted: {len(middle)} earlier messages summarized]\n{summary}",
    }
    compacted = head + [summary_message] + tail
    record = {
        "tokens_before": tokens_before,
        "tokens_after": estimate_tokens(compacted),
        "messages_before": len(messages),
        "messages_after": len(compacted),
        "summary": summary,
    }
    return compacted, record
