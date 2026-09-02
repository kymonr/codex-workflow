"""Mock and real Codex agent executors."""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, TextIO

from workflow.errors import AgentError
from workflow.schema import validate_instance

AGENT_TIMEOUT_SECONDS = 900
_TERMINATE_GRACE_SECONDS = 2.0
_ERROR_TAIL_BYTES = 4096


def _validated_seconds(
    value: object,
    *,
    allow_zero: bool,
    message: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    try:
        seconds = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(message) from exc
    if not math.isfinite(seconds) or (seconds < 0 if allow_zero else seconds <= 0):
        raise ValueError(message)
    return seconds


class MockExecutor:
    def __init__(
        self,
        payload: Any,
        *,
        handler: Callable[[str, dict[str, Any]], Any] | None = None,
        delay_s: float = 0.0,
    ) -> None:
        validated_delay = _validated_seconds(
            delay_s,
            allow_zero=True,
            message="mock delay_s must be a finite non-negative number",
        )
        self.payload = payload
        self.handler = handler
        self.delay_s = validated_delay
        self._cancelled = threading.Event()

    def cancel_all(self) -> None:
        self._cancelled.set()

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
        if self._cancelled.is_set():
            raise AgentError("agent cancelled")
        if self.delay_s and self._cancelled.wait(self.delay_s):
            raise AgentError("agent cancelled")
        if self._cancelled.is_set():
            raise AgentError("agent cancelled")
        payload = (
            self.handler(prompt, dict(opts))
            if self.handler is not None
            else self.payload
        )
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        (slot / "last.txt").write_text(text + "\n", encoding="utf-8")
        return _decode_result(
            payload if not isinstance(payload, str) else text,
            schema,
        )


class CodexExecutor:
    def __init__(self, timeout_seconds: float = AGENT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = _validated_seconds(
            timeout_seconds,
            allow_zero=False,
            message="agent timeout must be a positive finite number",
        )
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._active: set[subprocess.Popen[Any]] = set()

    def cancel_all(self) -> None:
        self._cancelled.set()
        with self._lock:
            active = list(self._active)
        for process in active:
            _terminate_process_tree(process)

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
        if self._cancelled.is_set():
            raise AgentError("codex exec cancelled")

        last_path = slot / "last.txt"
        stdout_path = slot / "stdout.log"
        stderr_path = slot / "stderr.log"
        timed_out = False
        return_code: int | None = None
        with (
            stdout_path.open("w", encoding="utf-8", newline="") as stdout,
            stderr_path.open("w", encoding="utf-8", newline="") as stderr,
        ):
            process = self._spawn(argv, stdout, stderr)
            try:
                return_code = process.wait(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_process_tree(process)
                process.wait(timeout=_TERMINATE_GRACE_SECONDS)
            finally:
                with self._lock:
                    self._active.discard(process)

        if timed_out:
            raise AgentError(
                f"codex exec timed out after {self.timeout_seconds:g}s"
            )
        if return_code is None:
            raise AgentError("codex exec returned no exit code")
        if self._cancelled.is_set() and return_code != 0:
            raise AgentError("codex exec cancelled")
        if return_code != 0:
            snippet = _read_error_tail(stderr_path, stdout_path)
            raise AgentError(f"codex exec exit {return_code}: {snippet}")
        if not last_path.is_file():
            raise AgentError("codex exec produced no last-message file")
        text = last_path.read_text(encoding="utf-8")
        return _decode_result(text, schema)

    def _spawn(
        self,
        argv: list[str],
        stdout: TextIO,
        stderr: TextIO,
    ) -> subprocess.Popen[Any]:
        kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": stdout,
            "stderr": stderr,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(
                subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0,
            )
        else:
            kwargs["start_new_session"] = True

        with self._lock:
            if self._cancelled.is_set():
                raise AgentError("codex exec cancelled")
            try:
                process = subprocess.Popen(argv, **kwargs)
            except OSError as exc:
                raise AgentError(f"failed to start codex exec: {exc}") from exc
            self._active.add(process)
        return process


def _terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=creationflags,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return

    try:
        process.wait(timeout=_TERMINATE_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    try:
        process.kill()
    except OSError:
        pass


def _read_error_tail(stderr_path: Path, stdout_path: Path) -> str:
    for path in (stderr_path, stdout_path):
        try:
            with path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - _ERROR_TAIL_BYTES))
                text = handle.read().decode("utf-8", errors="replace").strip()
        except OSError:
            continue
        if text:
            return text[-500:]
    return "no error output"


def _decode_result(raw: Any, schema: dict | None) -> Any:
    if schema is None:
        return raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AgentError(
                "agent() result is not JSON, but a schema was given"
            ) from exc
    else:
        parsed = raw
    validate_instance(parsed, schema)
    return parsed
