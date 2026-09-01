from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow.argv import ALLOWED_EFFORTS, DEFAULT_EFFORT
from workflow.errors import WorkflowError
from workflow.journal import read_events
from workflow.run import RunConfig, run_workflow


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
        prog="workflow",
        description="在隔离 JS 沙箱里跑工作流脚本；每个 agent() 变成一次 codex exec。",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="执行一份 JavaScript 工作流")
    run_p.add_argument("script", help="JavaScript 工作流脚本路径")
    run_p.add_argument(
        "--mock",
        action="store_true",
        help="不启动真实 codex exec，只记录将要使用的锁定 argv",
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
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.error("unknown command")

    workdir = Path(args.workdir) if args.workdir else Path.cwd()
    try:
        result = run_workflow(
            RunConfig(
                script_path=Path(args.script),
                runs_root=Path(args.runs_root),
                workdir=workdir,
                mock=args.mock,
                model=args.model,
                effort=args.effort,
            )
        )
    except WorkflowError as exc:
        print(f"失败: {exc}", file=sys.stderr)
        return 1

    print(f"运行目录: {result.run_dir}")
    print(f"journal: {result.journal_path}")
    if result.mock:
        print("模式: mock（没有启动真实 codex exec）")
    events = read_events(result.journal_path)
    agents = [event for event in events if event.get("event") == "agent" and event.get("ok")]
    for event in agents:
        returned = json.dumps(event.get("return"), ensure_ascii=False)
        print(f"agent {event.get('label')}: {returned}")
    return 0
