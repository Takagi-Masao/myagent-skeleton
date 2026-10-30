from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from .base import (
    ToolContext,
    ToolResult,
    decode_utf8,
    kill_process_tree,
    resolve_workspace_path,
    truncate_output,
)


class PythonTool:
    name = "run_python"
    description = (
        "Run Python code or a Python file with the same interpreter as the agent. "
        "Use this for file/text processing, tests, and small scripts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to run. Use either code or path."},
            "path": {"type": "string", "description": "Path to a .py file inside the workspace."},
            "timeout_s": {"type": "integer", "description": "Timeout in seconds."},
        },
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        """Run Python with the same interpreter as the agent.

        Contract:
        - exactly one of code/path; both or neither -> error observation
        - code: write to <workspace>/.myagent/tmp/run_<id>.py, deleted afterwards
        - path: resolve inside workspace; reject ../ and absolute escapes
        - command: [ctx.python_exe, "-X", "utf8", <file>], cwd=workspace
        - env: PYTHONUTF8=1, PYTHONIOENCODING=utf-8
        - timeout: kill the whole process tree, return code -1, error contains
          "timeout"
        - return stdout+stderr, decoded UTF-8 with errors="replace"
        """
        code = args.get("code")
        raw_path = args.get("path")
        has_code = isinstance(code, str) and code.strip() != ""
        has_path = isinstance(raw_path, str) and raw_path.strip() != ""
        if has_code == has_path:
            return ToolResult(-1, error="exactly one of 'code' or 'path' is required")

        workspace = Path(ctx.workspace).resolve()
        timeout = int(args.get("timeout_s", ctx.timeout_s) or ctx.timeout_s)
        temp_script: Path | None = None

        if has_code:
            temp_script = workspace / ".myagent" / "tmp" / f"run_{uuid4().hex[:8]}.py"
            temp_script.parent.mkdir(parents=True, exist_ok=True)
            temp_script.write_text(code, encoding="utf-8")
            script = temp_script
        else:
            try:
                script = resolve_workspace_path(workspace, raw_path)
            except ValueError as exc:
                return ToolResult(-1, error=str(exc))
            if not script.is_file():
                return ToolResult(-1, error=f"not a file: {raw_path}")

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        popen_kwargs: dict = {}
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        try:
            proc = subprocess.Popen(
                [ctx.python_exe or sys.executable, "-X", "utf8", str(script)],
                cwd=str(workspace),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                **popen_kwargs,
            )
            try:
                out, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                kill_process_tree(proc.pid)
                try:
                    out, _ = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:  # pragma: no cover - stubborn tree
                    proc.kill()
                    out, _ = proc.communicate()
                text, truncated = truncate_output(decode_utf8(out), ctx.max_output_chars)
                return ToolResult(
                    -1, text, error=f"timeout after {timeout}s", truncated=truncated
                )

            text, truncated = truncate_output(decode_utf8(out), ctx.max_output_chars)
            return ToolResult(proc.returncode or 0, text, truncated=truncated)
        finally:
            if temp_script is not None:
                temp_script.unlink(missing_ok=True)
