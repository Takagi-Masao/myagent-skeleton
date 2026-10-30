from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ToolResult:
    returncode: int = 0
    output: str = ""
    error: str = ""
    truncated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "returncode": self.returncode,
            "output": self.output,
            "error": self.error,
            "truncated": self.truncated,
        }


@dataclass
class ToolContext:
    workspace: Path
    timeout_s: int = 120
    max_output_chars: int = 8000
    python_exe: str = field(default_factory=lambda: sys.executable)
    shell_backend: str = "auto"
    submitted: bool = False
    submission: str = ""


class Tool(Protocol):
    name: str
    description: str
    parameters: dict

    def run(self, args: dict, ctx: ToolContext) -> ToolResult: ...


def decode_utf8(data: bytes | None) -> str:
    return (data or b"").decode("utf-8", errors="replace")


def truncate_output(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    head = max_chars // 2
    tail = max_chars - head
    omitted = len(text) - max_chars
    return (
        text[:head]
        + f"\n... [{omitted} chars omitted] ...\n"
        + text[-tail:],
        True,
    )


def resolve_workspace_path(workspace: Path, raw: str | None) -> Path:
    workspace = workspace.resolve()
    if not raw:
        return workspace
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise ValueError(f"path escapes workspace: {raw}")
    return resolved


def kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except ProcessLookupError:
        pass
