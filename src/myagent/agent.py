from __future__ import annotations

import time
from enum import Enum

from .config import Config
from .environment import detect_environment
from .events import NullLogger
from .prompts import build_instance_prompt, build_system_prompt
from .tools.base import ToolContext
from .tools.registry import ToolRegistry


class StopReason(str, Enum):
    SUBMIT = "Submitted"
    FINAL_ANSWER = "FinalAnswer"
    MAX_STEPS = "MaxSteps"
    MAX_COST = "MaxCost"
    MAX_SECONDS = "MaxSeconds"


class Agent:
    def __init__(
        self,
        model,
        tools: ToolRegistry,
        config: Config,
        logger=None,
    ):
        self.model = model
        self.tools = tools
        self.config = config
        self.logger = logger or NullLogger()
        self.messages: list[dict] = []
        self.ctx = ToolContext(
            workspace=config.workspace,
            timeout_s=config.timeout_s,
            max_output_chars=config.max_output_chars,
            python_exe=config.python_exe,
            shell_backend=config.shell_backend,
        )
        self.steps = 0
        self.cost = 0.0
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.stop_reason: StopReason | None = None
        self.final_text = ""
        self._started = time.time()

    def run(self, task: str) -> dict:
        """Bootstrap the messages, loop until should_stop(), return a result dict.

        Contract:
        1. messages start with system + user (use build_system_prompt /
           build_instance_prompt and detect_environment).
        2. Log run_start / every message / run_end through self.logger.
        3. Loop: call should_stop(); if None, call step().
        4. Return {"exit_status", "submission", "steps", "cost", "usage"}.

        Hint: `exit_status` is `self.stop_reason.value`; the loop must set
        `self.stop_reason` to the reason returned by should_stop().
        """
        raise NotImplementedError("H1: implement Agent.run() - see the docstring above")

    def step(self) -> None:
        """One model call, then execute every tool call in the response.

        Contract:
        1. Increment self.steps.
        2. response = self.model.chat(self.messages, self.tools.schemas()).
        3. Add response["cost"] and response["usage"] to self.cost / self.usage.
        4. Append response["message"] (assistant) and log it.
        5. If there are no tool_calls: set stop_reason=FINAL_ANSWER and
           final_text to the assistant content; return.
        6. For each tool call: log tool_call, execute through self.tools,
           append a {"role": "tool", "tool_call_id": ..., "content": <JSON>}
           message, log tool_result and the message.
        7. If self.ctx.submitted: set stop_reason=SUBMIT, final_text=
           self.ctx.submission, return.
        """
        raise NotImplementedError("H1: implement Agent.step() - see the docstring above")

    def should_stop(self) -> StopReason | None:
        if self.stop_reason is not None:
            return self.stop_reason
        if self.ctx.submitted:
            return StopReason.SUBMIT
        if self.config.max_steps and self.steps >= self.config.max_steps:
            return StopReason.MAX_STEPS
        if self.config.max_cost and self.cost >= self.config.max_cost:
            return StopReason.MAX_COST
        if self.config.max_seconds and time.time() - self._started >= self.config.max_seconds:
            return StopReason.MAX_SECONDS
        return None
