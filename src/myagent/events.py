from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class NullLogger:
    def log(self, event_type: str, **payload: Any) -> None:
        pass

    def message(self, message: dict) -> None:
        pass

    def tool_call(self, name: str, args: dict, call_id: str) -> None:
        pass

    def tool_result(self, call_id: str, result: dict) -> None:
        pass

    def run_start(self, **payload: Any) -> None:
        pass

    def run_end(self, **payload: Any) -> None:
        pass

    def close(self) -> None:
        pass


class JsonlLogger:
    """Append-only JSONL event log. One line per event, flushed immediately."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")
        self.last_id: str | None = None

    def log(self, event_type: str, **payload: Any) -> None:
        event = {
            "id": uuid4().hex,
            "parent_id": self.last_id,
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        self.last_id = event["id"]
        self._fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        self._fh.flush()

    def message(self, message: dict) -> None:
        self.log("message", message=message)

    def tool_call(self, name: str, args: dict, call_id: str) -> None:
        self.log("tool_call", name=name, args=args, call_id=call_id)

    def tool_result(self, call_id: str, result: dict) -> None:
        self.log("tool_result", call_id=call_id, **result)

    def run_start(self, **payload: Any) -> None:
        self.log("run_start", **payload)

    def run_end(self, **payload: Any) -> None:
        self.log("run_end", **payload)

    def close(self) -> None:
        self._fh.close()


def read_events(path: Path) -> list[dict]:
    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def trace_file(path: Path) -> str:
    events = read_events(path)
    lines = []
    for index, event in enumerate(events, start=1):
        stamp = event.get("ts", "")[11:19]
        kind = event.get("type", "?")
        payload = event.get("payload", {})
        if kind == "message":
            message = payload.get("message", {})
            detail = f"{message.get('role')}: {str(message.get('content', ''))[:80]}"
        elif kind == "tool_call":
            detail = f"{payload.get('name')} {json.dumps(payload.get('args', {}), ensure_ascii=False)[:100]}"
        elif kind == "tool_result":
            detail = (
                f"rc={payload.get('returncode')} "
                f"out={str(payload.get('output', ''))[:80]!r}"
            )
        elif kind == "run_start":
            detail = f"task={str(payload.get('task', ''))[:100]}"
        elif kind == "run_end":
            detail = (
                f"status={payload.get('exit_status')} steps={payload.get('steps')} "
                f"cost={payload.get('cost'):.4f}"
            )
        else:
            detail = json.dumps(payload, ensure_ascii=False)[:100]
        lines.append(f"{index:03d}  {stamp}  {kind:<12}  {detail}")
    return "\n".join(lines)
