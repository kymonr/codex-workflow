"""Locked argv for PR1: only `codex exec -s read-only` plus a closed option set.

This module is the sandbox boundary for the child process. Unknown flags,
sandbox-changing values, and extra `-c` keys are rejected even if a caller
constructs the list by hand.
"""

from __future__ import annotations

import re
from pathlib import Path

from workflow.errors import ArgvError

ALLOWED_EFFORTS = ("low", "medium", "high", "xhigh")
DEFAULT_EFFORT = "medium"

# Basename only. The resolved path may be codex.cmd on Windows.
_CODEX_NAMES = {"codex", "codex.exe", "codex.cmd", "codex.bat"}

_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_EFFORT_C_RE = re.compile(
    r"^model_reasoning_effort=(low|medium|high|xhigh)$"
)

# Matched case-insensitively against every argv token.
FORBIDDEN_SUBSTRINGS = (
    "danger-full-access",
    "workspace-write",
    "--full-auto",
    "--approval-policy",
    "--ask-for-approval",
    "--dangerously-bypass",
    "--config",
)

# Builder emits only these flags. Each consumes exactly one value.
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
) -> list[str]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ArgvError("agent() prompt must be a non-empty string")
    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ArgvError("agent() prompt exceeds PR1 size limit")
    if prompt.lstrip().startswith("-"):
        raise ArgvError("agent() prompt must not start with -")
    if effort not in ALLOWED_EFFORTS:
        raise ArgvError("effort must be low, medium, high, or xhigh")
    if model is not None:
        _check_model(model)

    workdir_s = _absolute_path(workdir, "workdir")
    last_s = _absolute_path(last_message_path, "last-message path")

    argv = [
        codex_bin,
        "exec",
        "-s",
        "read-only",
        "-C",
        workdir_s,
        "-c",
        f"model_reasoning_effort={effort}",
        "--color",
        "never",
        "--output-last-message",
        last_s,
    ]
    if schema_path is not None:
        argv.extend(["--output-schema", _absolute_path(schema_path, "schema path")])
    if model is not None:
        argv.extend(["-m", model])
    argv.append(prompt)
    validate_codex_argv(argv)
    return argv


def validate_codex_argv(argv: list[str]) -> None:
    if not argv or not isinstance(argv, list):
        raise ArgvError("argv must be a non-empty list")
    if any(not isinstance(tok, str) or tok == "" for tok in argv):
        raise ArgvError("argv tokens must be non-empty strings")

    for tok in argv:
        lower = tok.lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            if forbidden in lower:
                raise ArgvError(f"forbidden argv token: {forbidden}")

    exe = Path(argv[0]).name.lower()
    if exe not in _CODEX_NAMES:
        raise ArgvError("argv[0] must be the codex executable")
    if len(argv) < 3 or argv[1] != "exec":
        raise ArgvError("argv must start with <codex> exec")

    seen: dict[str, str] = {}
    i = 2
    while i < len(argv):
        tok = argv[i]
        if not tok.startswith("-"):
            break
        if tok not in _FLAG_ARITY:
            raise ArgvError(f"flag not allowed in PR1: {tok}")
        if tok in seen:
            raise ArgvError(f"duplicate flag: {tok}")
        if i + 1 >= len(argv):
            raise ArgvError(f"flag missing value: {tok}")
        value = argv[i + 1]
        if value.startswith("-") and tok != "-c":
            raise ArgvError(f"flag value looks like a flag: {tok} {value}")
        _validate_flag_value(tok, value)
        seen[tok] = value
        i += 2

    rest = argv[i:]
    if len(rest) != 1:
        raise ArgvError("argv must end with exactly one prompt positional")
    prompt = rest[0]
    if prompt.startswith("-"):
        raise ArgvError("prompt must not start with -")
    if not prompt.strip():
        raise ArgvError("prompt must be non-empty")
    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ArgvError("agent() prompt exceeds PR2 size limit")

    if seen.get("-s") != "read-only":
        raise ArgvError("PR1 argv must contain -s read-only")
    if "-c" not in seen or not _EFFORT_C_RE.fullmatch(seen["-c"]):
        raise ArgvError("PR1 argv must contain -c model_reasoning_effort=<allowed>")
    if "--output-last-message" not in seen:
        raise ArgvError("PR1 argv must contain --output-last-message")
    if "-C" not in seen:
        raise ArgvError("PR1 argv must contain -C <workdir>")
    if seen.get("--color") != "never":
        raise ArgvError("PR1 argv must contain --color never")


def _validate_flag_value(flag: str, value: str) -> None:
    if flag == "-s":
        if value != "read-only":
            raise ArgvError("sandbox must be read-only in PR1")
        return
    if flag == "-c":
        if not _EFFORT_C_RE.fullmatch(value):
            raise ArgvError("only -c model_reasoning_effort=<low|medium|high|xhigh> is allowed")
        return
    if flag == "-m":
        _check_model(value)
        return
    if flag == "--color":
        if value != "never":
            raise ArgvError("--color must be never")
        return
    if flag in {"-C", "--output-last-message", "--output-schema"}:
        path = Path(value)
        if not path.is_absolute():
            raise ArgvError(f"{flag} path must be absolute")
        return


def _check_model(model: str) -> None:
    if not _MODEL_RE.fullmatch(model) or model.startswith("-"):
        raise ArgvError("model name is not allowed")


def _absolute_path(path: Path, label: str) -> str:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = resolved.resolve()
    if not resolved.is_absolute():
        raise ArgvError(f"{label} must be an absolute path")
    return str(resolved)
