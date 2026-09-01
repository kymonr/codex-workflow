from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from workflow.errors import AgentError

_GIT_WORKTREE_LOCK = threading.Lock()
_SAFE_RUN_ID = re.compile(r"[^A-Za-z0-9._-]+")


def default_worktree_root() -> Path:
    day = datetime.now().strftime("%Y%m%d")
    if os.name == "nt":
        return Path(
            f"D:/.codex-tmp/{day}-codex-workflow-wt"
        ).resolve()
    return (
        Path(tempfile.gettempdir())
        / ".codex-tmp"
        / f"{day}-codex-workflow-wt"
    ).resolve()


def allocate_worktree_path(
    *,
    run_id: str,
    index: int,
    root: Path | None = None,
) -> Path:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise AgentError("worktree agent index must be a non-negative integer")
    safe_run_id = _SAFE_RUN_ID.sub("-", run_id).strip("-") or "run"
    base = (
        default_worktree_root()
        if root is None
        else root.expanduser().resolve()
    )
    return (base / safe_run_id / f"agent-{index:03d}").resolve()


def create_worktree(*, repository: Path, target: Path) -> Path:
    repository = repository.expanduser().resolve()
    target = target.expanduser().resolve()
    root = _repository_root(repository)
    if target == root or root in target.parents:
        raise AgentError("worktree path must be outside the main repository")
    if target.exists():
        raise AgentError(f"worktree path already exists: {target}")

    with _GIT_WORKTREE_LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "worktree",
                "add",
                "--detach",
                str(target),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:500]
            raise AgentError(f"git worktree add failed: {detail}")

    if not target.is_dir():
        raise AgentError(f"git worktree was not created: {target}")
    return target


def _repository_root(path: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise AgentError(f"workdir is not a git repository: {path}")
    output = completed.stdout.strip()
    if not output:
        raise AgentError(f"git repository root is unreadable: {path}")
    return Path(output).resolve()
