from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> None:
        if "event" not in event:
            raise ValueError("journal event must include event")
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
                handle.flush()

    def read_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return read_events(self.path)
