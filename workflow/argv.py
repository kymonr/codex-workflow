"""Locked argv construction for Codex workflow agents.

Normal agents are always read-only. ``workspace-write`` is accepted only when
Python host code explicitly marks a host-created Git worktree as authorized.
"""

from __future__ import annotations

import re
from pathlib import Path

from workflow.errors import ArgvError

ALLOWED_EFFORTS = ("low", "medium", "high", "xhigh")
DEFAULT_EFFORT = "medium"

_CODEX_NAMES = {"codex", "codex.exe", "codex.cmd", "codex.bat"}
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_EFFORT_C_RE = re.compile(
    r"^model_reasoning_effort=(low|medium|high|xhigh)$"
)

FORBIDDEN_SUBSTRINGS = (
    "danger-full-access",
    "workspace-write",
    "--full-auto",
    "--approval-policy",
    "--ask-for-approval",
    "--dangerously-bypass",
    "--config",
)

_FLAG_ARITY = {
    "-s": 1,
    "-C": 1,
    "-c": 1,
    "-m": 1,
    "--color": 1,
    "--output-last-message": 1,
    "--output-schema": 1,
}

_MAX_PROMPT_CHARS = 24_000


def build_codex_argv(
    *,
    prompt: str,
    workdir: Path,
    last_message_path: Path,
    schema_path: Path | None = None,
    effort: str = DEFAULT_EFFORT,
    model: str | None = None,
    codex_bin: str = "codex",
    sandbox: str = "read-only",
    worktree_authorized: bool = False,
) -> list[str]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ArgvError("agent() prompt must be a non-empty string")
    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ArgvError("agent() prompt exceeds PR6 size limit")
    if prompt.lstrip().startswith("-"):
        raise ArgvError("agent() prompt must not start with -")
    if effort not in ALLOWED_EFFORTS:
        raise ArgvError("effort must be low, medium, high, or xhigh")
    if model is not None:
        _check_model(model)
    _check_sandbox(sandbox, worktree_authorized=worktree_authorized)

    argv = [
        codex_bin,
        "exec",
        "-s",
        sandbox,
        "-C",
        _absolute_path(workdir, "workdir"),
        "-c",
        f"model_reasoning_effort={effort}",
        "--color",
        "never",
        "--output-last-message",
        _absolute_path(last_message_path, "last-message path"),
    ]
    if schema_path is not None:
        argv.extend(
            ["--output-schema", _absolute_path(schema_path, "schema path")]
        )
    if model is not None:
        argv.extend(["-m", model])
    argv.append(prompt)
    validate_codex_argv(
        argv,
        worktree_authorized=worktree_authorized,
    )
    return argv


def validate_codex_argv(
    argv: list[str],
    *,
    worktree_authorized: bool = False,
) -> None:
    if not argv or not isinstance(argv, list):
        raise ArgvError("argv must be a non-empty list")
    if any(not isinstance(token, str) or token == "" for token in argv):
        raise ArgvError("argv tokens must be non-empty strings")

    for index, token in enumerate(argv):
        forbidden = _find_forbidden_substring(token)
        if forbidden is None:
            continue
        if (
            forbidden == "workspace-write"
            and worktree_authorized
            and token == "workspace-write"
            and index > 0
            and argv[index - 1] == "-s"
        ):
            continue
        raise ArgvError(f"forbidden argv token: {forbidden}")

    executable = Path(argv[0]).name.lower()
    if executable not in _CODEX_NAMES:
        raise ArgvError("argv[0] must be the codex executable")
    if len(argv) < 3 or argv[1] != "exec":
        raise ArgvError("argv must start with <codex> exec")

    seen: dict[str, str] = {}
    index = 2
    while index < len(argv):
        token = argv[index]
        if not token.startswith("-"):
            break
        if token not in _FLAG_ARITY:
            raise ArgvError(f"flag not allowed: {token}")
        if token in seen:
            raise ArgvError(f"duplicate flag: {token}")
        if index + 1 >= len(argv):
            raise ArgvError(f"flag missing value: {token}")
        value = argv[index + 1]
        if value.startswith("-") and token != "-c":
            raise ArgvError(f"flag value looks like a flag: {token} {value}")
        _validate_flag_value(
            token,
            value,
            worktree_authorized=worktree_authorized,
        )
        seen[token] = value
        index += 2

    rest = argv[index:]
    if len(rest) != 1:
        raise ArgvError("argv must end with exactly one prompt positional")
    prompt = rest[0]
    if prompt.startswith("-"):
        raise ArgvError("prompt must not start with -")
    if not prompt.strip():
        raise ArgvError("prompt must be non-empty")
    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ArgvError("agent() prompt exceeds PR6 size limit")

    sandbox = seen.get("-s")
    _check_sandbox(sandbox, worktree_authorized=worktree_authorized)
    if "-c" not in seen or not _EFFORT_C_RE.fullmatch(seen["-c"]):
        raise ArgvError(
            "argv must contain -c model_reasoning_effort=<allowed>"
        )
    if "--output-last-message" not in seen:
        raise ArgvError("argv must contain --output-last-message")
    if "-C" not in seen:
        raise ArgvError("argv must contain -C <workdir>")
    if seen.get("--color") != "never":
        raise ArgvError("argv must contain --color never")


def _validate_flag_value(
    flag: str,
    value: str,
    *,
    worktree_authorized: bool,
) -> None:
    if flag == "-s":
        _check_sandbox(value, worktree_authorized=worktree_authorized)
        return
    if flag == "-c":
        if not _EFFORT_C_RE.fullmatch(value):
            raise ArgvError(
                "only -c model_reasoning_effort="
                "<low|medium|high|xhigh> is allowed"
            )
        return
    if flag == "-m":
        _check_model(value)
        return
    if flag == "--color":
        if value != "never":
            raise ArgvError("--color must be never")
        return
    if flag in {"-C", "--output-last-message", "--output-schema"}:
        if not Path(value).is_absolute():
            raise ArgvError(f"{flag} path must be absolute")


def _check_sandbox(
    sandbox: str | None,
    *,
    worktree_authorized: bool,
) -> None:
    if sandbox == "read-only":
        return
    if sandbox == "workspace-write" and worktree_authorized:
        return
    if sandbox == "workspace-write":
        raise ArgvError("workspace-write requires host worktree authorization")
    raise ArgvError("sandbox must be read-only or an authorized workspace-write")


def validate_model_name(model: object) -> str:
    if (
        not isinstance(model, str)
        or not _MODEL_RE.fullmatch(model)
        or model.startswith("-")
    ):
        raise ArgvError("model name is not allowed")
    forbidden = _find_forbidden_substring(model)
    if forbidden is not None:
        raise ArgvError(f"forbidden model token: {forbidden}")
    return model


def _find_forbidden_substring(token: str) -> str | None:
    lower = token.lower()
    return next(
        (forbidden for forbidden in FORBIDDEN_SUBSTRINGS if forbidden in lower),
        None,
    )


def _check_model(model: object) -> None:
    validate_model_name(model)


def _absolute_path(path: Path, label: str) -> str:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = resolved.resolve()
    if not resolved.is_absolute():
        raise ArgvError(f"{label} must be an absolute path")
    return str(resolved)
