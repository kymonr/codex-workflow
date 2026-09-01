from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


JOURNAL_VERSION = 1


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid journal JSON at {path}:{line_number}"
                ) from exc
            if not isinstance(event, dict):
                raise ValueError(
                    f"journal event must be an object at {path}:{line_number}"
                )
            events.append(event)
    return events


class Journal:
    def __init__(self, path: Path, *, truncate: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if truncate:
            self.path.write_text("", encoding="utf-8")
        else:
            self.path.touch(exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> None:
        if "event" not in event:
            raise ValueError("journal event must include event")
        line = json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
                handle.flush()

    def read_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return read_events(self.path)
