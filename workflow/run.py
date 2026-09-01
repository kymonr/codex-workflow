from __future__ import annotations

import json
import re
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from workflow.argv import DEFAULT_EFFORT, build_codex_argv
from workflow.errors import AgentError, ArgvError
from workflow.executor import CodexExecutor, MockExecutor
from workflow.journal import Journal
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

    run_dir = _make_run_dir(config.runs_root, script_path)
    copy_path = run_dir / f"script{script_path.suffix or '.js'}"
    copy_path.write_text(source, encoding="utf-8")
    journal = Journal(run_dir / "journal.jsonl")
    journal.append(
        {
            "event": "run.started",
            "script": str(script_path),
            "workdir": str(workdir),
            "mock": config.mock,
        }
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
    agent_index = 0
    agent_index_lock = threading.Lock()

    def on_agent(prompt: str, opts: dict[str, Any]) -> Any:
        nonlocal agent_index
        parsed = parse_agent_opts(opts)
        with agent_index_lock:
            index = agent_index
            agent_index += 1

        label = parsed["label"] or f"agent-{index:03d}"
        slot = run_dir / "agents" / f"{index:03d}-{_safe_label(label)}"
        slot.mkdir(parents=True, exist_ok=False)
        schema = parsed["schema"]
        schema_path = None
        if schema is not None:
            schema_path = slot / "schema.json"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        last_path = slot / "last.txt"
        argv = build_codex_argv(
            prompt=prompt,
            workdir=workdir,
            last_message_path=last_path,
            schema_path=schema_path,
            effort=parsed["effort"] or config.effort,
            model=parsed["model"] or config.model,
            codex_bin=codex_bin,
        )
        (slot / "argv.json").write_text(
            json.dumps(argv, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        record: dict[str, Any] = {
            "event": "agent",
            "index": index,
            "label": label,
            "prompt": prompt,
            "opts": {
                "label": parsed["label"],
                "schema": schema,
                "model": parsed["model"] or config.model,
                "effort": parsed["effort"] or config.effort,
            },
            "argv": argv,
        }
        try:
            value = executor.run(
                argv=argv,
                slot=slot,
                schema=schema,
                prompt=prompt,
                opts=opts,
            )
        except Exception as exc:
            record["ok"] = False
            record["error"] = str(exc)
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
        run_script(source, on_agent=on_agent, on_log=on_log)
    except Exception as exc:
        journal.append({"event": "run.finished", "ok": False, "error": str(exc)})
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
        dumped = json.dumps(schema, ensure_ascii=False)
        if len(dumped) > _MAX_SCHEMA_CHARS:
            raise AgentError("agent() schema exceeds PR1 size limit")
        validate_schema(schema)

    model = opts.get("model")
    if model is not None and not isinstance(model, str):
        raise AgentError("agent() model must be a string")

    effort = opts.get("effort")
    if effort is not None and not isinstance(effort, str):
        raise AgentError("agent() effort must be a string")

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
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", script_path.stem)[:40] or "run"
    path = runs_root / f"{stamp}-{slug}"
    suffix = 2
    while path.exists():
        path = runs_root / f"{stamp}-{slug}-{suffix}"
        suffix += 1
    path.mkdir(parents=False)
    (path / "agents").mkdir()
    return path


def _safe_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return (cleaned or "agent")[:80]
