from __future__ import annotations

import base64
import os
import shutil
import subprocess
from pathlib import Path

from .base import (
    ToolContext,
    ToolResult,
    decode_utf8,
    kill_process_tree,
    truncate_output,
)

POWERSHELL_PREFIX = (
    "[Console]::OutputEncoding=[Text.UTF8Encoding]::new();"
    "$OutputEncoding=[Text.UTF8Encoding]::new();"
)


class PowerShellBackend:
    def run(self, command: str, ctx: ToolContext) -> ToolResult:
        ps = shutil.which("pwsh") or "powershell.exe"
        encoded = base64.b64encode(
            (POWERSHELL_PREFIX + command).encode("utf-16-le")
        ).decode("ascii")
        proc = subprocess.Popen(
            [
                ps,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            cwd=str(ctx.workspace),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        try:
            out, _ = proc.communicate(timeout=ctx.timeout_s)
            text, truncated = truncate_output(decode_utf8(out), ctx.max_output_chars)
            return ToolResult(proc.returncode or 0, text, truncated=truncated)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc.pid)
            out, _ = proc.communicate()
            text, _ = truncate_output(decode_utf8(out), ctx.max_output_chars)
            return ToolResult(-1, text, error=f"timeout after {ctx.timeout_s}s")


class PosixShellBackend:
    def run(self, command: str, ctx: ToolContext) -> ToolResult:
        shell = shutil.which("bash") or "/bin/sh"
        env = os.environ | {
            "PYTHONUTF8": "1",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", ""),
        }
        proc = subprocess.Popen(
            [shell, "-c", command],
            cwd=str(ctx.workspace),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            out, _ = proc.communicate(timeout=ctx.timeout_s)
            text, truncated = truncate_output(decode_utf8(out), ctx.max_output_chars)
            return ToolResult(proc.returncode or 0, text, truncated=truncated)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc.pid)
            out, _ = proc.communicate()
            text, _ = truncate_output(decode_utf8(out), ctx.max_output_chars)
            return ToolResult(-1, text, error=f"timeout after {ctx.timeout_s}s")


class ShellTool:
    name = "run_shell"
    description = (
        "Run a shell command in the workspace. On Windows this is PowerShell; "
        "on Linux/macOS this is bash. Each call is a new shell: cd does not persist."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute."},
            "timeout_s": {"type": "integer", "description": "Timeout in seconds."},
        },
        "required": ["command"],
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        command = args.get("command")
        if not isinstance(command, str) or not command.strip():
            return ToolResult(-1, error="missing 'command'")
        timeout = int(args.get("timeout_s", ctx.timeout_s) or ctx.timeout_s)
        local_ctx = ToolContext(
            workspace=ctx.workspace,
            timeout_s=timeout,
            max_output_chars=ctx.max_output_chars,
            python_exe=ctx.python_exe,
            shell_backend=ctx.shell_backend,
        )
        backend = _get_backend(ctx.shell_backend)
        return backend.run(command, local_ctx)


def _get_backend(name: str):
    name = (name or "auto").lower()
    if name == "auto":
        return PowerShellBackend() if os.name == "nt" else PosixShellBackend()
    if name == "powershell":
        if os.name != "nt":
            raise RuntimeError("powershell backend is only available on Windows")
        return PowerShellBackend()
    if name == "gitbash":
        if os.name != "nt":
            raise RuntimeError("gitbash backend is only available on Windows")
        if not shutil.which("bash"):
            raise RuntimeError("Git Bash not found; install it or use the powershell backend")
        return PosixShellBackend()
    if name in ("bash", "zsh", "posix"):
        return PosixShellBackend()
    raise RuntimeError(f"unknown shell backend: {name}")
