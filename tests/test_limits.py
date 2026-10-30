from __future__ import annotations

import time

import pytest

from myagent.agent import Agent, StopReason
from myagent.config import Config
from myagent.tools.base import ToolResult
from myagent.tools.registry import ToolRegistry
from myagent.tools.submit import SubmitTool

from .fake_model import FakeModel
from .test_loop import EchoTool

pytestmark = pytest.mark.bronze


class SlowTool:
    name = "slow"
    description = "Sleep."
    parameters = {"type": "object", "properties": {}}

    def run(self, args, ctx):
        time.sleep(1.2)
        return ToolResult(0, "slept")


def make_agent(tmp_path, script, **config_kwargs):
    defaults = {"max_steps": 5, "max_seconds": 0, "max_cost": 0}
    defaults.update(config_kwargs)
    config = Config(workspace=tmp_path, **defaults)
    tools = ToolRegistry()
    tools.register(EchoTool())
    tools.register(SubmitTool())
    tools.register(SlowTool())
    return Agent(FakeModel(script), tools, config)


def test_submit_stops_with_submission(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [
                    {"id": "c1", "name": "submit", "arguments": {"summary": "finished"}}
                ]
            }
        ],
    )
    result = agent.run("finish")
    assert result["exit_status"] == StopReason.SUBMIT.value
    assert result["submission"] == "finished"
    assert agent.ctx.submitted is True


def test_max_cost_stops(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "x"}}],
                "cost": 0.6,
            }
        ],
        max_cost=0.5,
    )
    result = agent.run("expensive")
    assert result["exit_status"] == StopReason.MAX_COST.value


def test_max_seconds_stops(tmp_path):
    agent = make_agent(
        tmp_path,
        [
            {
                "tool_calls": [{"id": "c1", "name": "slow", "arguments": {}}],
            }
        ],
        max_seconds=1,
    )
    result = agent.run("slow")
    assert result["exit_status"] == StopReason.MAX_SECONDS.value


def test_final_answer_stops(tmp_path):
    agent = make_agent(tmp_path, [{"content": "done"}])
    result = agent.run("done")
    assert result["exit_status"] == StopReason.FINAL_ANSWER.value
    assert result["submission"] == "done"
