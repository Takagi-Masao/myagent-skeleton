from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def detect_shell() -> str:
    if os.name == "nt":
        return "PowerShell 7 (pwsh)" if shutil.which("pwsh") else "Windows PowerShell 5.1"
    shell = os.environ.get("SHELL", "bash")
    return Path(shell).name


def python_source() -> str:
    if os.getenv("CONDA_PREFIX"):
        return "conda"
    if os.getenv("VIRTUAL_ENV"):
        return "venv"
    if "uv" in sys.prefix.lower() or os.getenv("UV_PROJECT_ENVIRONMENT"):
        return "uv"
    if sys.prefix != sys.base_prefix:
        return "venv"
    return "system"


def detect_environment() -> dict[str, str]:
    return {
        "os": f"{platform.system()} {platform.release()}",
        "os_name": os.name,
        "machine": platform.machine(),
        "shell": detect_shell(),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "python_source": python_source(),
        "workspace": str(Path.cwd().resolve()),
        "path_sep": os.sep,
        "encoding": sys.stdout.encoding or "unknown",
    }
