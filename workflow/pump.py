"""QuickJS job pump for asynchronous agents and nested workflow scripts.

Only the calling thread touches the QuickJS context. Agent work runs in a
bounded thread pool. Child scripts are compiled and started by this same pump,
so they share the context, concurrency cap, live-agent limit, and completion
queues with the parent script.
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
_MAX_AGENT_PAYLOAD_CHARS = 128_000
_MAX_WORKFLOW_PAYLOAD_CHARS = 256_000
_MAX_WORKFLOW_CALLS = 4096
_MAX_JS_JOBS = 1_000_000
_JS_JOB_BATCH = 10_000
_WAIT_SECONDS = 0.05


@dataclass(frozen=True)
class PreparedWorkflow:
    function_source: str
    args_json: str


@dataclass(frozen=True)
class _AgentJob:
    job_id: str
    prepared: Any


@dataclass(frozen=True)
class _WorkflowJob:
    job_id: str
    prepared: PreparedWorkflow | None = None
    error: str | None = None


def default_max_concurrency() -> int:
    return min(16, max(1, (os.cpu_count() or 2) - 2))


def run_job_pump(
    user_function_source: str,
    *,
    runtime_source: str,
    prepare_agent: Callable[[str, dict[str, Any]], Any],
    execute_agent: Callable[[Any], Any],
    is_cached_agent: Callable[[Any], bool] | None,
    prepare_workflow: (
        Callable[[dict[str, Any], Any], PreparedWorkflow] | None
    ),
    on_log: Callable[[str], None] | None,
    on_phase: Callable[[str], None] | None,
    on_cancel: Callable[[], None] | None,
    args_json: str,
    budget_tokens: int | None,
    memory_limit_bytes: int,
    max_concurrency: int | None = None,
    max_agents: int = DEFAULT_MAX_AGENTS,
) -> None:
    """Evaluate a root script and pump it and its child workflows to completion."""

    concurrency = (
        default_max_concurrency()
        if max_concurrency is None
        else max_concurrency
    )
    if (
        isinstance(concurrency, bool)
        or not isinstance(concurrency, int)
        or concurrency < 1
    ):
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

    pending_agents: deque[_AgentJob] = deque()
    pending_workflows: deque[_WorkflowJob] = deque()
    inflight: dict[str, Future[Any]] = {}
    done_q: queue.Queue[tuple[str, str]] = queue.Queue()
    next_agent_job = 0
    next_workflow_job = 0
    accepted_agents = 0
    accepted_workflows = 0
    total_js_jobs = 0

    def host_start(payload_json: str) -> str:
        nonlocal next_agent_job, accepted_agents

        job_id = f"job-{next_agent_job:06d}"
        next_agent_job += 1
        try:
            if not isinstance(payload_json, str):
                raise SandboxError("agent() host payload must be JSON text")
            if len(payload_json) > _MAX_AGENT_PAYLOAD_CHARS:
                raise SandboxError("agent() host payload is too large")
            payload = json.loads(payload_json)
            if not isinstance(payload, dict):
                raise SandboxError("agent() host payload must be an object")
            prompt = payload.get("prompt")
            opts = payload.get("opts")
            if (
                not isinstance(prompt, str)
                or not prompt.strip()
                or not isinstance(opts, dict)
            ):
                raise SandboxError(
                    "agent() host payload must be {prompt, opts}"
                )
            prepared = prepare_agent(prompt, opts)
            if is_cached_agent is not None and is_cached_agent(prepared):
                try:
                    value = execute_agent(prepared)
                    packed = _success_envelope(value)
                except Exception as exc:
                    packed = _error_envelope(_error_text(exc))
                done_q.put((job_id, packed))
                return job_id

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
            pending_agents.append(_AgentJob(job_id, prepared))
        except Exception as exc:
            done_q.put((job_id, _error_envelope(_error_text(exc))))
        return job_id

    def host_workflow_start(payload_json: str) -> str:
        nonlocal next_workflow_job, accepted_workflows

        job_id = f"workflow-{next_workflow_job:06d}"
        next_workflow_job += 1
        try:
            if not isinstance(payload_json, str):
                raise SandboxError("workflow() host payload must be JSON text")
            if len(payload_json) > _MAX_WORKFLOW_PAYLOAD_CHARS:
                raise SandboxError("workflow() host payload is too large")
            payload = json.loads(payload_json)
            if (
                not isinstance(payload, dict)
                or set(payload) != {"spec", "args"}
            ):
                raise SandboxError(
                    "workflow() host payload must be {spec, args}"
                )
            if prepare_workflow is None:
                raise SandboxError("workflow() is not available in this run")
            if accepted_workflows >= _MAX_WORKFLOW_CALLS:
                raise SandboxError(
                    f"workflow() supports at most {_MAX_WORKFLOW_CALLS} calls"
                )
            spec = payload["spec"]
            if not isinstance(spec, dict):
                raise SandboxError("workflow() spec must be an object")
            prepared = prepare_workflow(spec, payload["args"])
            if not isinstance(prepared, PreparedWorkflow):
                raise SandboxError(
                    "workflow() host returned an invalid prepared child"
                )
            accepted_workflows += 1
            pending_workflows.append(
                _WorkflowJob(job_id=job_id, prepared=prepared)
            )
        except Exception as exc:
            pending_workflows.append(
                _WorkflowJob(job_id=job_id, error=_error_text(exc))
            )
        return job_id

    def host_log(message: str) -> str:
        try:
            if on_log is not None:
                on_log(str(message))
            return json.dumps({"ok": True})
        except Exception as exc:
            return _error_envelope(_error_text(exc))

    def host_phase(title: str) -> str:
        try:
            if not isinstance(title, str) or not title.strip():
                raise SandboxError(
                    "phase() title must be a non-empty string"
                )
            if len(title) > 80:
                raise SandboxError(
                    "phase() title must be at most 80 characters"
                )
            if on_phase is not None:
                on_phase(title)
            return json.dumps({"ok": True})
        except Exception as exc:
            return _error_envelope(_error_text(exc))

    def capture_completion(
        job_id: str,
        future: Future[Any],
    ) -> None:
        try:
            value = future.result()
            packed = _success_envelope(value)
        except Exception as exc:
            packed = _error_envelope(_error_text(exc))
        done_q.put((job_id, packed))

    def start_agents_upto_cap() -> int:
        started = 0
        while pending_agents and len(inflight) < concurrency:
            job = pending_agents.popleft()
            future = pool.submit(execute_agent, job.prepared)
            inflight[job.job_id] = future
            future.add_done_callback(
                lambda finished, job_id=job.job_id: capture_completion(
                    job_id,
                    finished,
                )
            )
            started += 1
        return started

    def deliver_agent(job_id: str, packed_json: str) -> None:
        inflight.pop(job_id, None)
        try:
            runtime("deliver", job_id, packed_json)
        except Exception as exc:
            raise SandboxError(f"agent delivery failed: {exc}") from exc

    def deliver_ready_agents() -> int:
        delivered = 0
        while True:
            try:
                job_id, packed = done_q.get_nowait()
            except queue.Empty:
                return delivered
            deliver_agent(job_id, packed)
            delivered += 1

    def reject_workflow(job_id: str, message: str) -> None:
        try:
            runtime("reject_workflow", job_id, message)
        except Exception as exc:
            raise SandboxError(
                f"workflow rejection delivery failed: {exc}"
            ) from exc

    def start_pending_workflows() -> int:
        started = 0
        while pending_workflows:
            job = pending_workflows.popleft()
            if job.error is not None:
                reject_workflow(job.job_id, job.error)
                started += 1
                continue
            prepared = job.prepared
            if prepared is None:
                reject_workflow(
                    job.job_id,
                    "workflow() host produced no child program",
                )
                started += 1
                continue
            try:
                child_main = ctx.eval(prepared.function_source)
            except Exception as exc:
                reject_workflow(
                    job.job_id,
                    f"child script eval failed: {_error_text(exc)}",
                )
                started += 1
                continue
            if not callable(child_main):
                reject_workflow(
                    job.job_id,
                    "child script did not evaluate to a callable program",
                )
                started += 1
                continue
            try:
                runtime(
                    "start_child",
                    job.job_id,
                    child_main,
                    prepared.args_json,
                )
            except Exception as exc:
                reject_workflow(
                    job.job_id,
                    f"child script start failed: {_error_text(exc)}",
                )
            started += 1
        return started

    def read_state() -> tuple[bool, str | None, int]:
        try:
            raw = runtime("state")
            state = json.loads(raw)
        except Exception as exc:
            raise SandboxError(f"sandbox state unreadable: {exc}") from exc
        if (
            not isinstance(state, dict)
            or not isinstance(state.get("done"), bool)
            or (
                state.get("error") is not None
                and not isinstance(state.get("error"), str)
            )
            or isinstance(state.get("activeChildren"), bool)
            or not isinstance(state.get("activeChildren"), int)
            or state["activeChildren"] < 0
        ):
            raise SandboxError(
                "sandbox state unreadable: invalid state envelope"
            )
        return (
            state["done"],
            state.get("error"),
            state["activeChildren"],
        )

    ctx.add_callable("__agent_start", host_start)
    ctx.add_callable("__workflow_start", host_workflow_start)
    ctx.add_callable("__log", host_log)
    ctx.add_callable("__phase_set", host_phase)
    ctx.set("__workflow_args_json", args_json)
    ctx.set("__budget_total_json", json.dumps(budget_tokens))

    try:
        runtime = ctx.eval(runtime_source)
    except Exception as exc:
        raise SandboxError(f"sandbox bootstrap failed: {exc}") from exc
    if not callable(runtime):
        raise SandboxError("sandbox bootstrap did not return a runtime")

    try:
        user_main = ctx.eval(user_function_source)
    except Exception as exc:
        raise SandboxError(f"script eval failed: {exc}") from exc
    if not callable(user_main):
        raise SandboxError("script eval failed: user program is not callable")

    try:
        runtime("start", user_main)
    except Exception as exc:
        raise SandboxError(f"script start failed: {exc}") from exc

    pool = ThreadPoolExecutor(
        max_workers=concurrency,
        thread_name_prefix="codex-workflow-agent",
    )
    try:
        while True:
            ran_jobs = 0
            while ran_jobs < _JS_JOB_BATCH:
                try:
                    ran = ctx.execute_pending_job()
                except Exception as exc:
                    raise SandboxError(
                        f"pending job failed: {exc}"
                    ) from exc
                if not ran:
                    break
                ran_jobs += 1
                total_js_jobs += 1
                if total_js_jobs > _MAX_JS_JOBS:
                    raise SandboxError("too many pending jobs")

            started_agents = start_agents_upto_cap()
            delivered_agents = deliver_ready_agents()
            started_workflows = start_pending_workflows()
            done, error, active_children = read_state()

            if error:
                raise SandboxError(error)
            if (
                done
                and active_children == 0
                and not pending_agents
                and not pending_workflows
                and not inflight
                and done_q.empty()
            ):
                break
            if (
                ran_jobs
                or started_agents
                or delivered_agents
                or started_workflows
            ):
                continue
            if inflight:
                try:
                    job_id, packed = done_q.get(timeout=_WAIT_SECONDS)
                except queue.Empty:
                    continue
                deliver_agent(job_id, packed)
                continue
            if pending_agents or pending_workflows:
                continue
            if not done or active_children:
                raise SandboxError(
                    "script stalled with no in-flight agents or workflows"
                )
    except BaseException:
        if on_cancel is not None:
            try:
                on_cancel()
            except Exception:
                pass
        raise
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
        return _error_envelope(
            f"agent result is not JSON-serializable: {exc}"
        )


def _error_envelope(message: str) -> str:
    return json.dumps(
        {"ok": False, "error": message},
        ensure_ascii=False,
        allow_nan=False,
    )


def _error_text(exc: BaseException) -> str:
    text = str(exc)
    return text if text else exc.__class__.__name__
