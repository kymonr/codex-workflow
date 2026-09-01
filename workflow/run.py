from __future__ import annotations

import json
import re
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from workflow.argv import ALLOWED_EFFORTS, DEFAULT_EFFORT, build_codex_argv
from workflow.errors import AgentError, ArgvError
from workflow.executor import CodexExecutor, MockExecutor
from workflow.journal import JOURNAL_VERSION, Journal
from workflow.sandbox import run_script
from workflow.schema import validate_schema

_ALLOWED_OPT_KEYS = {"label", "schema", "model", "effort"}
_BLOCKED_OPTS = {
    "isolation": "isolation/worktree is not available in PR1",
    "agentType": "agentType is not available in PR1",
    "argv": "agent() cannot set argv",
    "sandbox": "agent() cannot set sandbox",
}
_LABEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_MAX_SCHEMA_CHARS = 64_000


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
    slot: Path
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
        }
    )

    agent_index = 0
    agent_index_lock = threading.Lock()

    def prepare_agent(prompt: str, opts: dict[str, Any]) -> PreparedAgentCall:
        nonlocal agent_index

        with agent_index_lock:
            index = agent_index
            agent_index += 1

        requested_opts = dict(opts)
        record: dict[str, Any] = {
            "event": "agent",
            "index": index,
            "prompt": prompt,
            "requested_opts": requested_opts,
        }
        stage = "options"
        try:
            parsed = parse_agent_opts(requested_opts)
            label = parsed["label"] or f"agent-{index:03d}"
            model = config.model if parsed["model"] is None else parsed["model"]
            effort = config.effort if parsed["effort"] is None else parsed["effort"]
            schema = parsed["schema"]
            record["label"] = label
            record["opts"] = {
                "label": parsed["label"],
                "schema": schema,
                "model": model,
                "effort": effort,
            }

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
                workdir=workdir,
                last_message_path=last_path,
                schema_path=schema_path,
                effort=effort,
                model=model,
                codex_bin=codex_bin,
            )
            record["argv"] = argv

            stage = "artifacts"
            (slot / "argv.json").write_text(
                json.dumps(argv, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
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
            slot=slot,
            argv=tuple(argv),
        )

    def execute_agent(call: PreparedAgentCall) -> Any:
        record: dict[str, Any] = {
            "event": "agent",
            "index": call.index,
            "label": call.label,
            "prompt": call.prompt,
            "requested_opts": call.requested_opts,
            "opts": {
                "label": call.requested_opts.get("label"),
                "schema": call.schema,
                "model": call.model,
                "effort": call.effort,
            },
            "argv": list(call.argv),
        }
        try:
            value = executor.run(
                argv=list(call.argv),
                slot=call.slot,
                schema=call.schema,
                prompt=call.prompt,
                opts=call.requested_opts,
            )
        except Exception as exc:
            record["ok"] = False
            record["stage"] = "executor"
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

    try:
        run_script(
            source,
            prepare_agent=prepare_agent,
            execute_agent=execute_agent,
            on_log=on_log,
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

    return {
        "label": label,
        "schema": schema,
        "model": model,
        "effort": effort,
    }


def _make_run_dir(runs_root: Path, script_path: Path) -> Path:
    runs_root = runs_root.expanduser().resolve()
    runs_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"^[A-Za-z0-9._-]+", "-", script_path.stem)[:40] or "run"
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
