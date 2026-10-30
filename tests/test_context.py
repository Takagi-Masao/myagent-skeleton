from __future__ import annotations

import pytest

from myagent.context import estimate_tokens, maybe_compact

from .fake_model import FakeModel

pytestmark = pytest.mark.gold


def test_estimate_tokens_grows():
    short = [{"role": "user", "content": "hi"}]
    long = [{"role": "user", "content": "hi" * 1000}]
    assert estimate_tokens(long) > estimate_tokens(short)


def test_no_compaction_below_threshold():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "ok"},
    ]
    model = FakeModel([])
    result, record = maybe_compact(messages, model, max_tokens=10_000)
    assert result == messages
    assert record is None
    assert model.calls == []


def test_compaction_keeps_system_task_and_tail():
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "task"}]
    for i in range(12):
        messages.append({"role": "assistant", "content": f"step {i} " + "x" * 200})
    messages.append({"role": "user", "content": "last"})
    model = FakeModel([{"content": "summary text"}])
    result, record = maybe_compact(messages, model, max_tokens=100, keep_last=3)
    assert result[0]["content"] == "sys"
    assert result[1]["content"] == "task"
    assert result[-1]["content"] == "last"
    assert "summary text" in result[2]["content"]
    assert record is not None
    assert record["tokens_after"] < record["tokens_before"]
    assert record["messages_after"] < record["messages_before"]
