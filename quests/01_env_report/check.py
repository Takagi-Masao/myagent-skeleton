from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = {
    "python_version": str,
    "python_executable": str,
    "platform": str,
    "shell": str,
}


def main() -> int:
    path = Path("env.json")
    if not path.is_file():
        print("FAIL quest01: env.json not found")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL quest01: invalid JSON: {exc}")
        return 1
    if not isinstance(data, dict):
        print("FAIL quest01: env.json must be a JSON object")
        return 1
    for key, kind in REQUIRED.items():
        if key not in data:
            print(f"FAIL quest01: missing field {key}")
            return 1
        if not isinstance(data[key], kind):
            print(f"FAIL quest01: field {key} must be {kind.__name__}")
            return 1
    print("PASS quest01")
    return 0


if __name__ == "__main__":
    sys.exit(main())
