from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from workflow.argv import ALLOWED_EFFORTS, DEFAULT_EFFORT
from workflow.errors import AgentError, WorkflowError
from workflow.journal import read_events
from workflow.run import RunConfig
from workflow.supervisor import (
    DEFAULT_RUNTIME_TIMEOUT_SECONDS,
    supervise_workflow,
)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def load_args(args_text: str | None, args_file: Path | None) -> object:
    if args_text is not None and args_file is not None:
        raise AgentError("--args and --args-file cannot be used together")
    if args_file is not None:
        try:
            args_text = args_file.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise AgentError(f"cannot read --args-file: {args_file}: {exc}") from exc
    if args_text is None:
        return {}
    try:
        return json.loads(args_text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AgentError(f"invalid args JSON: {exc}") from exc


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "must be a positive number"
        ) from exc
    if parsed <= 0 or not math.isfinite(parsed):
        raise argparse.ArgumentTypeError(
            "must be a positive finite number"
        )
    return parsed


def _max_agents(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 1000:
        raise argparse.ArgumentTypeError("must be between 1 and 1000")
    return parsed


def configure_stdio() -> None:
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(
        prog="codex-workflow",
        description="在隔离 JS 沙箱里跑工作流脚本；每个 agent() 变成一次 codex exec。",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="执行一份 JavaScript 工作流")
    run_p.add_argument("script", help="JavaScript 工作流脚本路径")
    run_p.add_argument(
        "--mock",
        action="store_true",
        help="不启动真实 codex exec；仍执行工作流并写完整运行产物",
    )
    run_p.add_argument(
        "--runs-root",
        default="runs",
        help="运行目录的父目录（默认 ./runs）",
    )
    run_p.add_argument(
        "--cd",
        dest="workdir",
        default=None,
        help="codex exec -C 工作目录（默认当前目录）",
    )
    run_p.add_argument("-m", "--model", default=None, help="可选，传给 codex exec 的 -m")
    run_p.add_argument(
        "--effort",
        default=DEFAULT_EFFORT,
        choices=ALLOWED_EFFORTS,
        help="唯一允许的 -c：model_reasoning_effort",
    )
    run_p.add_argument(
        "--args",
        dest="args_json",
        default=None,
        help="注入为全局 args 的 JSON 文本",
    )
    run_p.add_argument(
        "--args-file",
        type=Path,
        default=None,
        help="从 UTF-8 JSON 文件读取全局 args",
    )
    run_p.add_argument(
        "--budget-tokens",
        type=_positive_int,
        default=None,
        help="可选 token 目标；当前不提供硬 token 停止",
    )
    run_p.add_argument(
        "--max-agents",
        type=_max_agents,
        default=1000,
        help="live agent 硬上限（1..1000，默认 1000）",
    )
    run_p.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="从旧运行目录按 agent 调用顺序做前缀缓存",
    )
    run_p.add_argument(
        "--timeout-seconds",
        type=_positive_float,
        default=DEFAULT_RUNTIME_TIMEOUT_SECONDS,
        help="整个 QuickJS 运行进程的 wall-clock 超时（默认 3600 秒）",
    )
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.error("unknown command")

    workdir = Path(args.workdir) if args.workdir else Path.cwd()
    try:
        workflow_args = load_args(args.args_json, args.args_file)
        result = supervise_workflow(
            RunConfig(
                script_path=Path(args.script),
                runs_root=Path(args.runs_root),
                workdir=workdir,
                mock=args.mock,
                model=args.model,
                effort=args.effort,
                args=workflow_args,
                budget_tokens=args.budget_tokens,
                max_agents=args.max_agents,
                resume_from=args.resume_from,
            ),
            timeout_seconds=args.timeout_seconds,
        )
    except WorkflowError as exc:
        print(f"失败: {exc}", file=sys.stderr)
        return 1

    print(f"运行目录: {result.run_dir}")
    print(f"journal: {result.journal_path}")
    if result.mock:
        print("模式: mock（没有启动真实 codex exec）")
    events = read_events(result.journal_path)
    agents = sorted(
        (
            event
            for event in events
            if event.get("event") == "agent" and event.get("ok")
        ),
        key=lambda event: event.get("index", 0),
    )
    for event in agents:
        returned = json.dumps(event.get("return"), ensure_ascii=False)
        print(f"agent {event.get('label')}: {returned}")
    return 0
