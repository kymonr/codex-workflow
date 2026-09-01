"""Process supervisor for workflow runtimes.

The QuickJS context lives in a child process so synchronous JavaScript loops
can be stopped without enabling QuickJS ``set_time_limit``.  On timeout or
interruption the supervisor terminates the whole runtime process tree.
"""

from __future__ import annotations

import math
import multiprocessing
import os
import pickle
import signal
import subprocess
import sys
import time
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from workflow.errors import WorkflowError
from workflow.run import RunConfig, RunResult, run_workflow


class SupervisorError(WorkflowError):
    """The supervised runtime could not complete safely."""


DEFAULT_RUNTIME_TIMEOUT_SECONDS = 3600.0
_POLL_SECONDS = 0.05
_STOP_GRACE_SECONDS = 2.0


def supervise_workflow(
    config: RunConfig,
    *,
    timeout_seconds: float,
) -> RunResult:
    """Run one workflow in a killable child process."""

    _validate_timeout(timeout_seconds)
    try:
        pickle.dumps(config)
    except Exception as exc:
        raise SupervisorError(
            "supervised RunConfig must be serializable; mock_handler is not "
            "supported unless it is picklable"
        ) from exc

    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_child_entry,
        args=(config, sender),
        name="codex-workflow-runtime",
    )
    try:
        process.start()
    except Exception as exc:
        receiver.close()
        sender.close()
        raise SupervisorError(f"failed to start workflow runtime: {exc}") from exc
    sender.close()

    deadline = time.monotonic() + float(timeout_seconds)
    payload: dict[str, Any] | None = None
    try:
        while payload is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_process_tree(process)
                raise SupervisorError(
                    f"workflow runtime timed out after {timeout_seconds:g}s"
                )
            if receiver.poll(min(_POLL_SECONDS, remaining)):
                try:
                    received = receiver.recv()
                except EOFError as exc:
                    raise SupervisorError(
                        "workflow runtime closed without a result"
                    ) from exc
                if not isinstance(received, dict):
                    raise SupervisorError(
                        "workflow runtime returned an invalid result"
                    )
                payload = received
                break
            if not process.is_alive():
                if receiver.poll():
                    continue
                raise SupervisorError(
                    "workflow runtime exited without a result "
                    f"(exit code {process.exitcode})"
                )
    except KeyboardInterrupt as exc:
        _stop_process_tree(process)
        raise SupervisorError("workflow runtime interrupted") from exc
    finally:
        receiver.close()

    process.join(_STOP_GRACE_SECONDS)
    if process.is_alive():
        _stop_process_tree(process)
    exit_code = process.exitcode
    process.close()

    if payload is None:
        raise SupervisorError("workflow runtime produced no result")
    if not payload.get("ok"):
        message = payload.get("error")
        if not isinstance(message, str) or not message:
            message = "workflow runtime failed"
        raise SupervisorError(message)
    if exit_code not in (0, None):
        raise SupervisorError(
            f"workflow runtime exited with code {exit_code} after reporting success"
        )

    run_dir = payload.get("run_dir")
    journal_path = payload.get("journal_path")
    mock = payload.get("mock")
    if (
        not isinstance(run_dir, str)
        or not isinstance(journal_path, str)
        or not isinstance(mock, bool)
    ):
        raise SupervisorError("workflow runtime returned an invalid result")
    return RunResult(
        run_dir=Path(run_dir),
        journal_path=Path(journal_path),
        mock=mock,
    )


def _child_entry(config: RunConfig, sender: Connection) -> None:
    try:
        if os.name != "nt":
            os.setsid()
        result = run_workflow(config)
        sender.send(
            {
                "ok": True,
                "run_dir": str(result.run_dir),
                "journal_path": str(result.journal_path),
                "mock": result.mock,
            }
        )
    except BaseException as exc:
        try:
            sender.send(
                {
                    "ok": False,
                    "error": _error_text(exc),
                    "error_type": exc.__class__.__name__,
                }
            )
        except Exception:
            pass
    finally:
        sender.close()


def _validate_timeout(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise SupervisorError("timeout_seconds must be a positive finite number")


def _stop_process_tree(process: multiprocessing.Process) -> None:
    if process.pid is None or not process.is_alive():
        process.join(timeout=0)
        return

    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            [
                "taskkill",
                "/PID",
                str(process.pid),
                "/T",
                "/F",
            ],
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
            pass

    process.join(_STOP_GRACE_SECONDS)
    if process.is_alive():
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.kill()
        process.join(_STOP_GRACE_SECONDS)


def _error_text(exc: BaseException) -> str:
    text = str(exc)
    return text if text else exc.__class__.__name__
