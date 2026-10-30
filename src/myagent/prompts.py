from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"


def _render(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


def build_system_prompt(env: dict[str, str], tool_names: list[str]) -> str:
    template = (PROMPT_DIR / "system.md").read_text(encoding="utf-8")
    return _render(
        template,
        {
            "os": env["os"],
            "shell": env["shell"],
            "python": env["python"],
            "python_version": env["python_version"],
            "workspace": env["workspace"],
            "path_sep": env["path_sep"],
            "tools": ", ".join(tool_names),
        },
    )


def build_instance_prompt(task: str, env: dict[str, str]) -> str:
    template = (PROMPT_DIR / "instance.md").read_text(encoding="utf-8")
    return _render(template, {"task": task, "workspace": env["workspace"]})
