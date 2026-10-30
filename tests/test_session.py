from __future__ import annotations

import pytest

from myagent.events import JsonlLogger, read_events
from myagent.session import resume

pytestmark = pytest.mark.silver


def _write_session(tmp_path, messages):
    path = tmp_path / "s.jsonl"
    logger = JsonlLogger(path)
    logger.run_start(task="test")
    for message in messages:
        logger.message(message)
    logger.run_end(exit_status="FinalAnswer", steps=1, cost=0.0)
    logger.close()
    return path


def test_read_events_roundtrip(tmp_path):
    path = _write_session(
        tmp_path,
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            {"role": "assistant", "content": "done"},
        ],
    )
    events = read_events(path)
    assert events[0]["type"] == "run_start"
    assert len([e for e in events if e["type"] == "message"]) == 3


def test_resume_returns_messages(tmp_path):
    path = _write_session(
        tmp_path,
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
        ],
    )
    messages = resume(path)
    assert [m["role"] for m in messages] == ["system", "user"]


def test_resume_fills_interrupted_tool_call(tmp_path):
    path = _write_session(
        tmp_path,
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "task"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "c1", "type": "function", "function": {"name": "run_python", "arguments": "{}"}}
                ],
            },
        ],
    )
    messages = resume(path)
    assert messages[-1]["role"] == "tool"
    assert messages[-1]["tool_call_id"] == "c1"
    assert "interrupted" in messages[-1]["content"]


def test_resume_empty_file(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    assert resume(path) == []
