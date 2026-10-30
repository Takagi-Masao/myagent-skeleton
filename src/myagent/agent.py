from __future__ import annotations

import json
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


def _logged_args(raw_args: object) -> object:
    """Decode a model's JSON argument string so the trace shows a JSON object."""
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return raw_args
    return raw_args


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
        env = detect_environment()
        # detect_environment() reports the process cwd, but every tool runs inside
        # config.workspace (which differs when --workspace is used). Tell the model
        # the directory the tools actually operate in, or it writes to both.
        env["workspace"] = str(self.config.workspace)
        tool_names = [schema["function"]["name"] for schema in self.tools.schemas()]
        self.messages = [
            {"role": "system", "content": build_system_prompt(env, tool_names)},
            {"role": "user", "content": build_instance_prompt(task, env)},
        ]
        self.logger.run_start(
            task=task,
            workspace=str(self.config.workspace),
            model=self.config.model,
            tools=tool_names,
        )
        for message in self.messages:
            self.logger.message(message)

        while True:
            reason = self.should_stop()
            if reason is not None:
                self.stop_reason = reason
                break
            self.step()

        if self.stop_reason is StopReason.SUBMIT:
            submission = self.ctx.submission
        elif self.stop_reason is StopReason.FINAL_ANSWER:
            submission = self.final_text
        else:
            submission = self.ctx.submission or self.final_text

        result = {
            "exit_status": self.stop_reason.value if self.stop_reason else "Unknown",
            "submission": submission,
            "steps": self.steps,
            "cost": round(self.cost, 6),
            "usage": dict(self.usage),
        }
        self.logger.run_end(**result)
        return result

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
        self.steps += 1
        response = self.model.chat(self.messages, self.tools.schemas())

        self.cost += float(response.get("cost") or 0.0)
        usage = response.get("usage") or {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self.usage[key] += int(usage.get(key, 0) or 0)

        message = response["message"]
        self.messages.append(message)
        self.logger.message(message)

        tool_calls = response.get("tool_calls") or []
        if not tool_calls:
            self.stop_reason = StopReason.FINAL_ANSWER
            self.final_text = message.get("content") or ""
            return

        for call in tool_calls:
            call_id = call.get("id")
            name = call.get("name")
            raw_args = call.get("arguments")
            self.logger.tool_call(name, _logged_args(raw_args), call_id)

            result = self.tools.execute(name, raw_args, self.ctx)
            payload = result.as_dict()
            self.logger.tool_result(call_id, payload)

            tool_message = {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(payload, ensure_ascii=False),
            }
            self.messages.append(tool_message)
            self.logger.message(tool_message)

        if self.ctx.submitted:
            self.stop_reason = StopReason.SUBMIT
            self.final_text = self.ctx.submission

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
