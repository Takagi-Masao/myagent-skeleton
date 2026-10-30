from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .agent import Agent
from .config import Config
from .environment import detect_environment
from .events import JsonlLogger, trace_file
from .model import ModelConfigError, OpenAIModel
from .tools import (
    ListDirTool,
    PythonTool,
    ReadFileTool,
    ShellTool,
    SubmitTool,
    ToolContext,
    ToolRegistry,
    WriteFileTool,
)
from .tools.base import ToolResult


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in (
        SubmitTool(),
        PythonTool(),
        ShellTool(),
        ReadFileTool(),
        WriteFileTool(),
        ListDirTool(),
    ):
        registry.register(tool)
    return registry


def _cmd_run(args: argparse.Namespace) -> int:
    config = Config.from_env(
        workspace=args.workspace,
        provider=args.provider,
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        max_steps=args.max_steps,
        max_cost=args.max_cost,
        max_seconds=args.max_seconds,
        timeout_s=args.timeout,
        shell_backend=args.shell_backend,
        python_exe=args.python,
    )
    session_dir = Path(args.session_dir).resolve() if args.session_dir else config.session_dir
    session_path = session_dir / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    logger = JsonlLogger(session_path)
    try:
        model = OpenAIModel(config)
        agent = Agent(model, _build_registry(), config, logger)
        result = agent.run(args.task)
    except NotImplementedError as exc:
        print(f"\n[TODO] {exc}", file=sys.stderr)
        print("Implement the TODO in src/myagent and run again.", file=sys.stderr)
        return 2
    except ModelConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    finally:
        logger.close()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nsession: {session_path}")
    return 0


def _cmd_trace(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        print(f"no such session: {path}", file=sys.stderr)
        return 2
    print(trace_file(path))
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = Config.from_env(
        workspace=args.workspace,
        provider=args.provider,
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        python_exe=args.python,
    )
    env = detect_environment()
    checks: dict[str, object] = {}

    print(f"myagent {__version__} doctor")
    print(f"  os:        {env['os']} ({env['machine']})")
    print(f"  python:    {env['python']} ({env['python_version']}, {env['python_source']})")
    print(f"  shell:     {env['shell']}")
    print(f"  workspace: {config.workspace}")
    print(f"  provider:  {config.provider}")
    print(f"  base_url:  {config.base_url}")
    print(f"  model:     {config.model}")
    print(f"  api_key:   {'set' if config.api_key else 'EMPTY'}")

    checks["python_version"] = sys.version_info >= (3, 10)
    checks["api_key"] = bool(config.api_key)

    try:
        import openai  # noqa: F401

        checks["openai"] = True
        print(f"  openai:    installed ({openai.__version__})")
    except Exception as exc:  # noqa: BLE001
        checks["openai"] = False
        print(f"  openai:    MISSING ({exc})")

    # shell smoke test
    try:
        ctx = ToolContext(workspace=config.workspace, shell_backend=config.shell_backend)
        result = ShellTool().run({"command": "echo myagent-doctor"}, ctx)
        checks["shell"] = result.returncode == 0 and "myagent-doctor" in result.output
        print(f"  shell test: {'pass' if checks['shell'] else 'FAIL'}")
    except Exception as exc:  # noqa: BLE001
        checks["shell"] = False
        print(f"  shell test: FAIL ({exc})")

    # model tool-call test (costs a few tokens)
    if config.api_key:
        try:
            model = OpenAIModel(config)
            echo_tool = {
                "type": "function",
                "function": {
                    "name": "echo",
                    "description": "Echo the given text.",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
            }
            response = model.chat(
                [{"role": "user", "content": "Call the echo tool with text 'ping'."}],
                [echo_tool],
                tool_choice={"type": "function", "function": {"name": "echo"}},
            )
            checks["tool_call"] = bool(response.get("tool_calls"))
            print(f"  tool_call test: {'pass' if checks['tool_call'] else 'FAIL'}")
            if not checks["tool_call"]:
                print(f"    model said: {str(response['message'].get('content'))[:120]}")
        except Exception as exc:  # noqa: BLE001
            checks["tool_call"] = False
            print(f"  tool_call test: FAIL ({type(exc).__name__}: {exc})")
    else:
        checks["tool_call"] = False
        print("  tool_call test: skipped (no api key)")

    ok = all(bool(checks.get(key)) for key in ("python_version", "api_key", "openai", "shell", "tool_call"))
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")

    if args.report:
        report_path = config.workspace / ".myagent" / "doctor.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "env": env,
            "config": {
                "provider": config.provider,
                "base_url": config.base_url,
                "model": config.model,
                "api_key_set": bool(config.api_key),
                "python_exe": config.python_exe,
                "shell_backend": config.shell_backend,
            },
            "checks": checks,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report: {report_path}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="myagent", description="A minimal coding agent for the AI lab course.")
    parser.add_argument("--version", action="version", version=f"myagent {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one task")
    run.add_argument("task", help="task description")
    run.add_argument("--workspace", default=".")
    run.add_argument("--session-dir", default=None)
    run.add_argument("--provider", default=None)
    run.add_argument("--base-url", default=None)
    run.add_argument("--model", default=None)
    run.add_argument("--api-key", default=None)
    run.add_argument("--max-steps", type=int, default=None)
    run.add_argument("--max-cost", type=float, default=None)
    run.add_argument("--max-seconds", type=int, default=None)
    run.add_argument("--timeout", type=int, default=None)
    run.add_argument("--shell-backend", default=None)
    run.add_argument("--python", default=None)
    run.set_defaults(func=_cmd_run)

    doctor = sub.add_parser("doctor", help="check environment, model, and tools")
    doctor.add_argument("--workspace", default=".")
    doctor.add_argument("--provider", default=None)
    doctor.add_argument("--base-url", default=None)
    doctor.add_argument("--model", default=None)
    doctor.add_argument("--api-key", default=None)
    doctor.add_argument("--python", default=None)
    doctor.add_argument("--report", action="store_true", help="write .myagent/doctor.json")
    doctor.set_defaults(func=_cmd_doctor)

    trace = sub.add_parser("trace", help="render a JSONL session")
    trace.add_argument("path")
    trace.set_defaults(func=_cmd_trace)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
