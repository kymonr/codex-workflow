"""QuickJS job pump for asynchronous agent execution.

Only the calling thread touches the QuickJS context. Agent work runs in a
bounded thread pool and reports JSON envelopes back through a completion queue.
"""

from __future__ import annotations

import json
import os
import queue
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from quickjs import Context

from workflow.errors import SandboxError

DEFAULT_MAX_AGENTS = 1000
_MAX_JS_JOBS = 1_000_000
_JS_JOB_BATCH = 10_000
_WAIT_SECONDS = 0.05


@dataclass(frozen=True)
class _AgentJob:
    job_id: str
    prompt: str
    opts: dict[str, Any]


def default_max_concurrency() -> int:
    return min(16, max(1, (os.cpu_count() or 2) - 2))


def run_job_pump(
    wrapped_source: str,
    *,
    on_agent: Callable[[str, dict[str, Any]], Any],
    on_log: Callable[[str], None] | None,
    memory_limit_bytes: int,
    max_concurrency: int | None = None,
    max_agents: int = DEFAULT_MAX_AGENTS,
) -> None:
    """Evaluate *wrapped_source* and pump promises until the script settles."""

    concurrency = default_max_concurrency() if max_concurrency is None else max_concurrency
    if isinstance(concurrency, bool) or not isinstance(concurrency, int) or concurrency < 1:
        raise SandboxError("max_concurrency must be a positive integer")
    concurrency = min(16, concurrency)
    if (
        isinstance(max_agents, bool)
        or not isinstance(max_agents, int)
        or not 1 <= max_agents <= DEFAULT_MAX_AGENTS
    ):
        raise SandboxError(
            f"max_agents must be between 1 and {DEFAULT_MAX_AGENTS}"
        )

    ctx = Context()
    ctx.set_memory_limit(memory_limit_bytes)

    pending_starts: deque[_AgentJob] = deque()
    inflight: dict[str, Future[Any]] = {}
    done_q: queue.Queue[tuple[str, str]] = queue.Queue()
    next_job_number = 0
    accepted_agents = 0
    total_js_jobs = 0

    def host_start(payload_json: str) -> str:
        nonlocal next_job_number, accepted_agents

        job_id = f"job-{next_job_number:06d}"
        next_job_number += 1
        try:
            payload = json.loads(payload_json)
            if not isinstance(payload, dict):
                raise SandboxError("agent() host payload must be an object")
            prompt = payload.get("prompt")
            opts = payload.get("opts")
            if not isinstance(prompt, str) or not prompt.strip() or not isinstance(opts, dict):
                raise SandboxError("agent() host payload must be {prompt, opts}")
            if accepted_agents >= max_agents:
                done_q.put(
                    (
                        job_id,
                        _error_envelope(
                            f"max-agents limit exceeded ({max_agents})"
                        ),
                    )
                )
                return job_id
            accepted_agents += 1
            pending_starts.append(_AgentJob(job_id, prompt, opts))
        except Exception as exc:
            done_q.put((job_id, _error_envelope(_error_text(exc))))
        return job_id

    def host_log(message: str) -> str:
        try:
            if on_log is not None:
                on_log(str(message))
            return json.dumps({"ok": True})
        except Exception as exc:
            return _error_envelope(_error_text(exc))

    def capture_completion(job_id: str, future: Future[Any]) -> None:
        try:
            value = future.result()
            packed = _success_envelope(value)
        except Exception as exc:
            packed = _error_envelope(_error_text(exc))
        done_q.put((job_id, packed))

    def start_upto_cap() -> int:
        started = 0
        while pending_starts and len(inflight) < concurrency:
            job = pending_starts.popleft()
            future = pool.submit(on_agent, job.prompt, job.opts)
            inflight[job.job_id] = future
            future.add_done_callback(
                lambda finished, job_id=job.job_id: capture_completion(job_id, finished)
            )
            started += 1
        return started

    def deliver(job_id: str, packed_json: str) -> None:
        inflight.pop(job_id, None)
        expression = (
            "__deliver("
            + json.dumps(job_id)
            + ","
            + json.dumps(packed_json)
            + ");"
        )
        try:
            ctx.eval(expression)
        except Exception as exc:
            raise SandboxError(f"agent delivery failed: {exc}") from exc

    def deliver_ready() -> int:
        delivered = 0
        while True:
            try:
                job_id, packed = done_q.get_nowait()
            except queue.Empty:
                return delivered
            deliver(job_id, packed)
            delivered += 1

    ctx.add_callable("__agent_start", host_start)
    ctx.add_callable("__log", host_log)

    pool = ThreadPoolExecutor(
        max_workers=concurrency,
        thread_name_prefix="codex-workflow-agent",
    )
    try:
        try:
            ctx.eval(wrapped_source)
        except Exception as exc:
            raise SandboxError(f"script eval failed: {exc}") from exc

        while True:
            ran_jobs = 0
            while ran_jobs < _JS_JOB_BATCH and ctx.execute_pending_job():
                ran_jobs += 1
                total_js_jobs += 1
                if total_js_jobs > _MAX_JS_JOBS:
                    raise SandboxError("too many pending jobs")

            started = start_upto_cap()
            delivered = deliver_ready()

            try:
                done = bool(ctx.eval("__done"))
                error = ctx.eval("__error")
            except Exception as exc:
                raise SandboxError(f"sandbox state unreadable: {exc}") from exc

            if error:
                raise SandboxError(str(error))
            if (
                done
                and not pending_starts
                and not inflight
                and done_q.empty()
            ):
                break
            if ran_jobs or started or delivered:
                continue
            if pending_starts:
                continue
            if inflight:
                try:
                    job_id, packed = done_q.get(timeout=_WAIT_SECONDS)
                except queue.Empty:
                    continue
                deliver(job_id, packed)
                continue
            if not done:
                raise SandboxError("script stalled with no in-flight agents")
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


def _success_envelope(value: Any) -> str:
    try:
        return json.dumps(
            {"ok": True, "value": value},
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        return _error_envelope(f"agent result is not JSON-serializable: {exc}")


def _error_envelope(message: str) -> str:
    return json.dumps(
        {"ok": False, "error": message},
        ensure_ascii=False,
        allow_nan=False,
    )


def _error_text(exc: BaseException) -> str:
    text = str(exc)
    return text if text else exc.__class__.__name__
