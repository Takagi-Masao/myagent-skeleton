from __future__ import annotations

import pytest

from myagent.agent import Agent, StopReason
from myagent.config import Config
from myagent.tools.base import ToolResult
from myagent.tools.registry import ToolRegistry

from .fake_model import FakeModel

pytestmark = pytest.mark.bronze


class EchoTool:
    name = "echo"
    description = "Echo text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, args, ctx):
        if args.get("text") == "boom":
            raise RuntimeError("tool exploded")
        return ToolResult(0, f"echo:{args.get('text')}")


def make_agent(tmp_path, script, max_steps=5):
    config = Config(workspace=tmp_path, max_steps=max_steps, max_seconds=0, max_cost=0)
    tools = ToolRegistry()
    tools.register(EchoTool())
    return Agent(FakeModel(script), tools, config)


def test_final_answer_stops(tmp_path):
    agent = make_agent(tmp_path, [{"content": "done"}])
    result = agent.run("say done")
    assert result["exit_status"] == StopReason.FINAL_ANSWER.value
    assert [m["role"] for m in agent.messages] == ["system", "user", "assistant"]
    assert result["steps"] == 1


def test_one_tool_call_is_executed_and_paired(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {"tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "hi"}}]},
            {"content": "done"},
        ],
    )
    result = agent.run("echo hi")
    assert result["exit_status"] == StopReason.FINAL_ANSWER.value
    tool_messages = [m for m in agent.messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "c1"
    assert "echo:hi" in tool_messages[0]["content"]


def test_two_tool_calls_in_one_response(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [
                    {"id": "c1", "name": "echo", "arguments": {"text": "a"}},
                    {"id": "c2", "name": "echo", "arguments": {"text": "b"}},
                ]
            },
            {"content": "done"},
        ],
    )
    agent.run("two")
    tool_messages = [m for m in agent.messages if m.get("role") == "tool"]
    assert [m["tool_call_id"] for m in tool_messages] == ["c1", "c2"]


def test_content_and_tool_call_are_both_kept(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "content": "I will echo",
                "tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "hi"}}],
            },
            {"content": "done"},
        ],
    )
    agent.run("echo")
    assistant = [m for m in agent.messages if m.get("role") == "assistant"][0]
    assert assistant["content"] == "I will echo"
    assert assistant["tool_calls"][0]["id"] == "c1"


def test_empty_response_stops(tmp_path):
    agent = make_agent(tmp_path, [{"content": ""}])
    result = agent.run("nothing")
    assert result["exit_status"] == StopReason.FINAL_ANSWER.value
    assert result["steps"] == 1


def test_max_steps(tmp_path):
    tool_call = {"tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "x"}}]}
    agent = make_agent(tmp_path, [tool_call, tool_call, tool_call], max_steps=2)
    result = agent.run("loop")
    assert result["exit_status"] == StopReason.MAX_STEPS.value
    assert result["steps"] == 2


def test_model_exception_propagates(tmp_path):
    agent = make_agent(tmp_path, [{"raise": "model down"}])
    with pytest.raises(RuntimeError, match="model down"):
        agent.run("fail")


def test_tool_exception_becomes_observation(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {"tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "boom"}}]},
            {"content": "done"},
        ],
    )
    agent.run("explode")
    tool_message = [m for m in agent.messages if m.get("role") == "tool"][0]
    assert "RuntimeError" in tool_message["content"]
    assert tool_message["content"].count("tool exploded") == 1
