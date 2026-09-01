from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from workflow.errors import AgentError
from workflow.schema import validate_instance

AGENT_TIMEOUT_SECONDS = 900


class MockExecutor:
    def __init__(
        self,
        payload: Any,
        *,
        handler: Callable[[str, dict[str, Any]], Any] | None = None,
        delay_s: float = 0.0,
    ) -> None:
        if isinstance(delay_s, bool) or not isinstance(delay_s, (int, float)) or delay_s < 0:
            raise ValueError("mock delay_s must be a non-negative number")
        self.payload = payload
        self.handler = handler
        self.delay_s = float(delay_s)

    def run(
        self,
        *,
        argv: list[str],
        slot: Path,
        schema: dict | None,
        prompt: str,
        opts: dict[str, Any],
    ) -> Any:
        del argv
        (slot / "stdout.log").write_text("", encoding="utf-8")
        (slot / "stderr.log").write_text("", encoding="utf-8")
        if self.delay_s:
            time.sleep(self.delay_s)
        payload = self.handler(prompt, dict(opts)) if self.handler is not None else self.payload
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, ensure_ascii=False)
        (slot / "last.txt").write_text(text + "\n", encoding="utf-8")
        return _decode_result(payload if not isinstance(payload, str) else text, schema)


class CodexExecutor:
    def run(
        self,
        *,
        argv: list[str],
        slot: Path,
        schema: dict | None,
        prompt: str,
        opts: dict[str, Any],
    ) -> Any:
        del prompt, opts
        last_path = slot / "last.txt"
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            _write_logs(slot, getattr(exc, "stdout", "") or "", getattr(exc, "stderr", "") or "")
            raise AgentError(f"codex exec timed out after {AGENT_TIMEOUT_SECONDS}s") from exc
        _write_logs(slot, completed.stdout, completed.stderr)
        if completed.returncode != 0:
            snippet = (completed.stderr or completed.stdout or "").strip()[:500]
            raise AgentError(f"codex exec exit {completed.returncode}: {snippet}")
        if not last_path.is_file():
            raise AgentError("codex exec produced no last-message file")
        text = last_path.read_text(encoding="utf-8")
        return _decode_result(text, schema)


def _write_logs(slot: Path, stdout: str, stderr: str) -> None:
    (slot / "stdout.log").write_text(stdout or "", encoding="utf-8")
    (slot / "stderr.log").write_text(stderr or "", encoding="utf-8")


def _decode_result(raw: Any, schema: dict | None) -> Any:
    if schema is None:
        return raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AgentError("agent() result is not JSON, but a schema was given") from exc
    else:
        parsed = raw
    validate_instance(parsed, schema)
    return parsed
