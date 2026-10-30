from __future__ import annotations

import pytest

from myagent.agent import Agent
from myagent.config import Config
from myagent.tools.python_tool import PythonTool
from myagent.tools.registry import ToolRegistry
from myagent.tools.submit import SubmitTool

from .fake_model import FakeModel

pytestmark = pytest.mark.bronze


def make_agent(tmp_path, script):
    config = Config(workspace=tmp_path, max_steps=5, max_seconds=0, max_cost=0)
    tools = ToolRegistry()
    tools.register(PythonTool())
    tools.register(SubmitTool())
    return Agent(FakeModel(script), tools, config)


def test_agent_writes_file(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [
                    {
                        "id": "c1",
                        "name": "run_python",
                        "arguments": {"code": "open('hello.txt', 'w', encoding='utf-8').write('hi')"},
                    }
                ]
            },
            {"content": "done"},
        ],
    )
    result = agent.run("write hello.txt")
    assert result["exit_status"] == "FinalAnswer"
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hi"


def test_agent_submits(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [
                    {"id": "c1", "name": "submit", "arguments": {"summary": "ok"}}
                ]
            }
        ],
    )
    result = agent.run("finish")
    assert result["exit_status"] == "Submitted"
    assert result["submission"] == "ok"


def test_agent_recovers_from_bad_tool_args(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [
                    {"id": "c1", "name": "run_python", "arguments": {"code": "print('a')", "path": "x.py"}}
                ]
            },
            {"content": "done"},
        ],
    )
    result = agent.run("bad args")
    assert result["exit_status"] == "FinalAnswer"
    tool_message = [m for m in agent.messages if m.get("role") == "tool"][0]
    assert "exactly one" in tool_message["content"]
