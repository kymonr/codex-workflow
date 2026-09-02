from __future__ import annotations

import json
import re
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from workflow.argv import (
    ALLOWED_EFFORTS,
    DEFAULT_EFFORT,
    build_codex_argv,
    validate_model_name,
)
from workflow.errors import AgentError, ArgvError
from workflow.executor import CodexExecutor, MockExecutor
from workflow.journal import JOURNAL_VERSION, Journal
from workflow.pump import DEFAULT_MAX_AGENTS, PreparedWorkflow
from workflow.resume import ResumeCursor, agent_identity
from workflow.sandbox import prepare_script, run_script, wrap_user_script
from workflow.schema import validate_instance, validate_schema
from workflow.worktree import allocate_worktree_path, create_worktree

_ALLOWED_OPT_KEYS = {"label", "schema", "model", "effort", "isolation"}
_BLOCKED_OPTS = {
    "agentType": "agentType is not available in PR1",
    "argv": "agent() cannot set argv",
    "sandbox": "agent() cannot set sandbox",
}
_LABEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_MAX_SCHEMA_CHARS = 64_000
_MAX_CHILD_ARGS_CHARS = 128_000
_MAX_CHILD_PATH_CHARS = 4096


@dataclass
class RunConfig:
    script_path: Path
    runs_root: Path
    workdir: Path
    mock: bool = False
    mock_payload: Any = None
    mock_handler: Callable[[str, dict[str, Any]], Any] | None = None
    mock_delay_s: float = 0.0
    model: str | None = None
    effort: str = DEFAULT_EFFORT
    args: Any = field(default_factory=dict)
    budget_tokens: int | None = None
    max_agents: int = DEFAULT_MAX_AGENTS
    resume_from: Path | None = None
    worktree_root: Path | None = None
    codex_bin: str | None = None


@dataclass
class RunResult:
    run_dir: Path
    journal_path: Path
    mock: bool


@dataclass(frozen=True)
class PreparedAgentCall:
    index: int
    prompt: str
    requested_opts: dict[str, Any]
    label: str
    schema: dict[str, Any] | None
    model: str | None
    effort: str
    isolation: str | None
    phase: str | None
    identity: str
    cache: bool
    cached_value: Any
    worktree_path: Path | None
    slot: Path | None
    argv: tuple[str, ...]


def resolve_codex_bin(*, mock: bool, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which("codex")
    if found:
        return found
    if mock:
        return "codex"
    raise ArgvError("PATH 上找不到 codex 可执行文件")


def run_workflow(config: RunConfig) -> RunResult:
    script_path = config.script_path.expanduser().resolve()
    if not script_path.is_file():
        raise AgentError(f"脚本不存在: {script_path}")
    source = script_path.read_text(encoding="utf-8")
    workdir = config.workdir.expanduser().resolve()
    if not workdir.is_dir():
        raise AgentError(f"工作目录不存在: {workdir}")

    args_json = _validate_run_config(config)
    resume = (
        ResumeCursor.load(config.resume_from, config.args)
        if config.resume_from is not None
        else ResumeCursor.disabled()
    )

    mock_payload = config.mock_payload
    if mock_payload is None:
        mock_payload = {"name": "codex-workflow"}
    executor = (
        MockExecutor(
            mock_payload,
            handler=config.mock_handler,
            delay_s=config.mock_delay_s,
        )
        if config.mock
        else CodexExecutor()
    )
    codex_bin = resolve_codex_bin(mock=config.mock, explicit=config.codex_bin)

    run_dir = _make_run_dir(config.runs_root, script_path)
    copy_path = run_dir / f"script{script_path.suffix or '.js'}"
    copy_path.write_text(source, encoding="utf-8")
    journal = Journal(run_dir / "journal.jsonl", truncate=True)
    journal.append(
        {
            "event": "run.started",
            "journal_version": JOURNAL_VERSION,
            "script": str(script_path),
            "workdir": str(workdir),
            "mock": config.mock,
            "args": config.args,
            "budget_tokens": config.budget_tokens,
            "max_agents": config.max_agents,
            "resume_from": (
                str(resume.source_run) if resume.source_run is not None else None
            ),
        }
    )

    agent_index = 0
    live_agent_count = 0
    agent_index_lock = threading.Lock()
    current_phase: str | None = None

    def prepare_agent(prompt: str, opts: dict[str, Any]) -> PreparedAgentCall:
        nonlocal agent_index, live_agent_count

        with agent_index_lock:
            index = agent_index
            agent_index += 1

        requested_opts = dict(opts)
        phase_snapshot = current_phase
        record: dict[str, Any] = {
            "event": "agent",
            "index": index,
            "prompt": prompt,
            "requested_opts": requested_opts,
            "phase": phase_snapshot,
        }
        stage = "options"
        try:
            parsed = parse_agent_opts(requested_opts)
            label = parsed["label"] or f"agent-{index:03d}"
            model = config.model if parsed["model"] is None else parsed["model"]
            effort = config.effort if parsed["effort"] is None else parsed["effort"]
            schema = parsed["schema"]
            isolation = parsed["isolation"]
            identity = agent_identity(
                prompt=prompt,
                label=parsed["label"],
                schema=schema,
                model=model,
                effort=effort,
                isolation=isolation,
            )
            record["label"] = label
            record["identity"] = identity
            record["opts"] = {
                "label": parsed["label"],
                "schema": schema,
                "model": model,
                "effort": effort,
                "isolation": isolation,
            }

            match = resume.match(identity)
            if match.hit:
                return PreparedAgentCall(
                    index=index,
                    prompt=prompt,
                    requested_opts=requested_opts,
                    label=label,
                    schema=schema,
                    model=model,
                    effort=effort,
                    isolation=isolation,
                    phase=phase_snapshot,
                    identity=identity,
                    cache=True,
                    cached_value=match.value,
                    worktree_path=None,
                    slot=None,
                    argv=(),
                )

            stage = "limit"
            if live_agent_count >= config.max_agents:
                raise AgentError(
                    f"max-agents limit exceeded ({config.max_agents})"
                )

            worktree_path = None
            agent_workdir = workdir
            sandbox = "read-only"
            worktree_authorized = False
            if isolation == "worktree":
                worktree_path = allocate_worktree_path(
                    run_id=run_dir.name,
                    index=index,
                    root=config.worktree_root,
                )
                agent_workdir = worktree_path
                sandbox = "workspace-write"
                worktree_authorized = True

            stage = "slot"
            slot = run_dir / "agents" / f"{index:03d}-{_safe_label(label)}"
            slot.mkdir(parents=True, exist_ok=False)

            schema_path = None
            if schema is not None:
                stage = "schema"
                schema_path = slot / "schema.json"
                schema_path.write_text(
                    json.dumps(
                        schema,
                        ensure_ascii=False,
                        indent=2,
                        allow_nan=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            stage = "argv"
            last_path = slot / "last.txt"
            argv = build_codex_argv(
                prompt=prompt,
                workdir=agent_workdir,
                last_message_path=last_path,
                schema_path=schema_path,
                effort=effort,
                model=model,
                codex_bin=codex_bin,
                sandbox=sandbox,
                worktree_authorized=worktree_authorized,
            )
            record["argv"] = argv

            stage = "artifacts"
            (slot / "argv.json").write_text(
                json.dumps(argv, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            live_agent_count += 1
        except Exception as exc:
            record["ok"] = False
            record["stage"] = stage
            record["error"] = _error_text(exc)
            journal.append(record)
            raise

        return PreparedAgentCall(
            index=index,
            prompt=prompt,
            requested_opts=requested_opts,
            label=label,
            schema=schema,
            model=model,
            effort=effort,
            isolation=isolation,
            phase=phase_snapshot,
            identity=identity,
            cache=False,
            cached_value=None,
            worktree_path=worktree_path,
            slot=slot,
            argv=tuple(argv),
        )

    def execute_agent(call: PreparedAgentCall) -> Any:
        record: dict[str, Any] = {
            "event": "agent",
            "index": call.index,
            "label": call.label,
            "prompt": call.prompt,
            "phase": call.phase,
            "identity": call.identity,
            "cache": call.cache,
            "requested_opts": call.requested_opts,
            "opts": {
                "label": call.requested_opts.get("label"),
                "schema": call.schema,
                "model": call.model,
                "effort": call.effort,
                "isolation": call.isolation,
            },
        }
        if call.cache:
            try:
                if call.schema is not None:
                    validate_instance(call.cached_value, call.schema)
            except Exception as exc:
                record["ok"] = False
                record["stage"] = "cache"
                record["error"] = _error_text(exc)
                journal.append(record)
                raise
            record["ok"] = True
            record["return"] = call.cached_value
            journal.append(record)
            return call.cached_value

        if call.slot is None:
            raise AgentError("live agent has no artifact slot")
        record["argv"] = list(call.argv)
        stage = "executor"
        try:
            if call.isolation == "worktree":
                if call.worktree_path is None:
                    raise AgentError("worktree agent has no host path")
                stage = "worktree"
                created = create_worktree(
                    repository=workdir,
                    target=call.worktree_path,
                )
                record["worktree"] = str(created)
                stage = "executor"
            value = executor.run(
                argv=list(call.argv),
                slot=call.slot,
                schema=call.schema,
                prompt=call.prompt,
                opts=call.requested_opts,
            )
        except Exception as exc:
            record["ok"] = False
            record["stage"] = stage
            record["error"] = _error_text(exc)
            journal.append(record)
            raise
        record["ok"] = True
        record["return"] = value
        record["exit_code"] = 0
        journal.append(record)
        return value

    def on_log(message: str) -> None:
        journal.append({"event": "log", "message": message})

    def on_phase(title: str) -> None:
        nonlocal current_phase
        current_phase = title
        journal.append({"event": "phase", "title": title})

    def prepare_workflow(
        spec: dict[str, Any],
        child_args: Any,
    ) -> PreparedWorkflow:
        if set(spec) != {"scriptPath"}:
            raise AgentError(
                "workflow() spec must be exactly {scriptPath: string}"
            )
        raw_path = spec.get("scriptPath")
        if (
            not isinstance(raw_path, str)
            or not raw_path.strip()
            or len(raw_path) > _MAX_CHILD_PATH_CHARS
        ):
            raise AgentError(
                "workflow() scriptPath must be a non-empty string"
            )

        child_path = (script_path.parent / raw_path).resolve()
        try:
            child_path.relative_to(workdir)
        except ValueError as exc:
            raise AgentError(
                "child workflow path must remain within workdir"
            ) from exc
        if not child_path.is_file():
            raise AgentError(
                f"child workflow script does not exist: {child_path}"
            )

        try:
            child_args_json = json.dumps(
                child_args,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise AgentError(
                "child workflow args must be valid JSON"
            ) from exc
        if len(child_args_json) > _MAX_CHILD_ARGS_CHARS:
            raise AgentError("child workflow args are too large")

        child_source = child_path.read_text(encoding="utf-8")
        child_function = wrap_user_script(prepare_script(child_source))
        journal.append(
            {
                "event": "workflow",
                "script": str(child_path),
                "args": child_args,
            }
        )
        return PreparedWorkflow(
            function_source=child_function,
            args_json=child_args_json,
        )

    try:
        run_script(
            source,
            prepare_agent=prepare_agent,
            execute_agent=execute_agent,
            is_cached_agent=lambda call: call.cache,
            prepare_workflow=prepare_workflow,
            on_log=on_log,
            on_phase=on_phase,
            on_cancel=executor.cancel_all,
            args_json=args_json,
            budget_tokens=config.budget_tokens,
            max_agents=config.max_agents,
        )
    except Exception as exc:
        journal.append(
            {
                "event": "run.finished",
                "ok": False,
                "agents": agent_index,
                "error": _error_text(exc),
            }
        )
        raise

    journal.append({"event": "run.finished", "ok": True, "agents": agent_index})
    return RunResult(run_dir=run_dir, journal_path=journal.path, mock=config.mock)


def _validate_run_config(config: RunConfig) -> str:
    if (
        not isinstance(config.effort, str)
        or config.effort not in ALLOWED_EFFORTS
    ):
        raise AgentError(
            "effort must be low, medium, high, or xhigh"
        )
    if config.model is not None:
        try:
            validate_model_name(config.model)
        except ArgvError as exc:
            raise AgentError(str(exc)) from exc
    if (
        config.budget_tokens is not None
        and (
            isinstance(config.budget_tokens, bool)
            or not isinstance(config.budget_tokens, int)
            or config.budget_tokens < 1
        )
    ):
        raise AgentError("budget_tokens must be a positive integer")
    if (
        isinstance(config.max_agents, bool)
        or not isinstance(config.max_agents, int)
        or not 1 <= config.max_agents <= DEFAULT_MAX_AGENTS
    ):
        raise AgentError(
            f"max_agents must be between 1 and {DEFAULT_MAX_AGENTS}"
        )
    try:
        return json.dumps(
            config.args,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise AgentError("args must be valid JSON") from exc


def parse_agent_opts(opts: dict[str, Any] | None) -> dict[str, Any]:
    if opts is None:
        opts = {}
    if not isinstance(opts, dict):
        raise AgentError("agent() opts must be an object")
    for key, message in _BLOCKED_OPTS.items():
        if key in opts:
            raise AgentError(message)
    unknown = set(opts) - _ALLOWED_OPT_KEYS
    if unknown:
        raise AgentError("unknown agent() opts: " + ", ".join(sorted(unknown)))

    label = opts.get("label")
    if label is None:
        label = None
    elif not isinstance(label, str) or not _LABEL_RE.fullmatch(label):
        raise AgentError("agent() label must match [A-Za-z0-9._-]{1,80}")

    schema = opts.get("schema")
    if schema is not None:
        if not isinstance(schema, dict):
            raise AgentError("agent() schema must be an object")
        try:
            dumped = json.dumps(schema, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise AgentError("agent() schema must be valid JSON") from exc
        if len(dumped) > _MAX_SCHEMA_CHARS:
            raise AgentError("agent() schema exceeds PR2 size limit")
        validate_schema(schema)

    model = opts.get("model")
    if model is not None:
        if not isinstance(model, str) or not model:
            raise AgentError("agent() model must be a non-empty string")

    effort = opts.get("effort")
    if effort is not None:
        if not isinstance(effort, str) or effort not in ALLOWED_EFFORTS:
            raise AgentError(
                "agent() effort must be low, medium, high, or xhigh"
            )

    isolation = opts.get("isolation")
    if isolation is not None and isolation != "worktree":
        raise AgentError('agent() isolation must be "worktree"')

    return {
        "label": label,
        "schema": schema,
        "model": model,
        "effort": effort,
        "isolation": isolation,
    }


def _make_run_dir(runs_root: Path, script_path: Path) -> Path:
    runs_root = runs_root.expanduser().resolve()
    runs_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", script_path.stem)[:40] or "run"
    base_name = f"{stamp}-{slug}"
    suffix = 1
    while True:
        name = base_name if suffix == 1 else f"{base_name}-{suffix}"
        path = runs_root / name
        try:
            path.mkdir(parents=False)
        except FileExistsError:
            suffix += 1
            continue
        break
    (path / "agents").mkdir()
    return path


def _safe_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return (cleaned or "agent")[:80]


def _error_text(exc: BaseException) -> str:
    text = str(exc)
    return text if text else exc.__class__.__name__
