from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROVIDERS: dict[str, dict[str, str]] = {
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.8-flash",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-flash",
    },
    "custom": {
        "base_url": "",
        "model": "",
    },
}

# USD per 1M tokens, only for the two presets. Unknown models show tokens, cost 0.
PRICES: dict[str, tuple[float, float]] = {
    "qwen3.8-flash": (0.8, 2.7),
    "deepseek-flash": (0.5, 2.0),
}


def load_dotenv(path: Path) -> None:
    """Tiny .env loader. Does not override already-exported variables."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


@dataclass
class Config:
    provider: str = "dashscope"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    max_steps: int = 20
    max_cost: float = 0.5
    max_seconds: int = 300
    timeout_s: int = 120
    max_output_chars: int = 8000
    workspace: Path = field(default_factory=Path.cwd)
    python_exe: str = field(default_factory=lambda: sys.executable)
    shell_backend: str = "auto"
    session_dir: Path | None = None

    def __post_init__(self) -> None:
        self.workspace = Path(self.workspace).resolve()
        if self.session_dir is None:
            self.session_dir = self.workspace / ".myagent" / "sessions"
        else:
            self.session_dir = Path(self.session_dir).resolve()
        preset = PROVIDERS.get(self.provider, PROVIDERS["custom"])
        self.base_url = self.base_url or preset["base_url"]
        self.model = self.model or preset["model"]

    @classmethod
    def from_env(cls, workspace: Path | str | None = None, **overrides) -> "Config":
        ws = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        load_dotenv(ws / ".env")
        # Also allow running from the skeleton root with --workspace <quest>:
        # the root .env is a fallback; the workspace .env wins if both exist.
        if Path.cwd().resolve() != ws:
            load_dotenv(Path.cwd() / ".env")
        provider = os.getenv("MYAGENT_PROVIDER", "dashscope").strip() or "dashscope"
        preset = PROVIDERS.get(provider, PROVIDERS["custom"])
        data = {
            "provider": provider,
            "base_url": os.getenv("MYAGENT_BASE_URL", "").strip() or preset["base_url"],
            "api_key": os.getenv("MYAGENT_API_KEY", "").strip(),
            "model": os.getenv("MYAGENT_MODEL", "").strip() or preset["model"],
            "max_steps": _env_int("MYAGENT_MAX_STEPS", 20),
            "max_cost": _env_float("MYAGENT_MAX_COST", 0.5),
            "max_seconds": _env_int("MYAGENT_MAX_SECONDS", 300),
            "timeout_s": _env_int("MYAGENT_TIMEOUT_S", 120),
            "max_output_chars": _env_int("MYAGENT_MAX_OUTPUT_CHARS", 8000),
            "workspace": ws,
            "python_exe": os.getenv("MYAGENT_PYTHON", "").strip() or sys.executable,
            "shell_backend": os.getenv("MYAGENT_SHELL_BACKEND", "auto").strip() or "auto",
        }
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)

    def cost_of(self, usage: dict[str, int]) -> float:
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        price_in, price_out = PRICES.get(self.model, (0.0, 0.0))
        return (prompt * price_in + completion * price_out) / 1_000_000
