from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workflow.errors import AgentError
from workflow.journal import JOURNAL_VERSION, read_events


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise AgentError("resume identity must be valid JSON") from exc


def agent_identity(
    *,
    prompt: str,
    label: str | None,
    schema: dict[str, Any] | None,
    model: str | None,
    effort: str,
    isolation: str | None = None,
) -> str:
    return canonical_json(
        {
            "prompt": prompt,
            "opts": {
                "label": label,
                "schema": schema,
                "model": model,
                "effort": effort,
                "isolation": isolation,
            },
        }
    )


@dataclass(frozen=True)
class ResumeMatch:
    hit: bool
    value: Any = None


@dataclass(frozen=True)
class _CacheEntry:
    identity: str
    value: Any


class ResumeCursor:
    def __init__(
        self,
        entries: list[_CacheEntry],
        *,
        active: bool,
        source_run: Path | None,
    ) -> None:
        self._entries = entries
        self._active = active
        self._position = 0
        self.source_run = source_run

    @classmethod
    def disabled(cls) -> "ResumeCursor":
        return cls([], active=False, source_run=None)

    @classmethod
    def load(cls, run_dir: Path, current_args: Any) -> "ResumeCursor":
        resolved = run_dir.expanduser().resolve()
        if not resolved.is_dir():
            raise AgentError(f"resume run directory does not exist: {resolved}")
        journal_path = resolved / "journal.jsonl"
        if not journal_path.is_file():
            raise AgentError(f"resume journal does not exist: {journal_path}")
        try:
            events = read_events(journal_path)
        except (OSError, ValueError) as exc:
            raise AgentError(f"cannot read resume journal: {exc}") from exc

        started = next(
            (event for event in events if event.get("event") == "run.started"),
            None,
        )
        if started is None:
            raise AgentError("resume journal has no run.started event")
        version = started.get("journal_version")
        if version != JOURNAL_VERSION:
            raise AgentError(
                "resume journal version is unsupported: "
                f"{version!r}; expected {JOURNAL_VERSION}"
            )
        args_match = canonical_json(started.get("args", {})) == canonical_json(
            current_args
        )

        agent_events = sorted(
            (
                event
                for event in events
                if event.get("event") == "agent"
                and isinstance(event.get("index"), int)
            ),
            key=lambda event: event["index"],
        )
        entries: list[_CacheEntry] = []
        expected_index = 0
        for event in agent_events:
            if event["index"] != expected_index or not event.get("ok"):
                break
            if "return" not in event:
                break
            identity = event.get("identity")
            if not isinstance(identity, str):
                identity = _identity_from_event(event)
            entries.append(_CacheEntry(identity=identity, value=event["return"]))
            expected_index += 1

        return cls(entries, active=args_match, source_run=resolved)

    def match(self, identity: str) -> ResumeMatch:
        if not self._active or self._position >= len(self._entries):
            self._active = False
            return ResumeMatch(False)
        entry = self._entries[self._position]
        if entry.identity != identity:
            self._active = False
            return ResumeMatch(False)
        self._position += 1
        return ResumeMatch(True, entry.value)


def _identity_from_event(event: dict[str, Any]) -> str:
    prompt = event.get("prompt")
    opts = event.get("opts")
    if not isinstance(prompt, str) or not isinstance(opts, dict):
        raise AgentError("resume agent record has no usable identity")
    effort = opts.get("effort")
    if not isinstance(effort, str):
        raise AgentError("resume agent record has no usable effort")
    schema = opts.get("schema")
    if schema is not None and not isinstance(schema, dict):
        raise AgentError("resume agent record has invalid schema")
    label = opts.get("label")
    if label is not None and not isinstance(label, str):
        raise AgentError("resume agent record has invalid label")
    model = opts.get("model")
    if model is not None and not isinstance(model, str):
        raise AgentError("resume agent record has invalid model")
    isolation = opts.get("isolation")
    if isolation is not None and not isinstance(isolation, str):
        raise AgentError("resume agent record has invalid isolation")
    return agent_identity(
        prompt=prompt,
        label=label,
        schema=schema,
        model=model,
        effort=effort,
        isolation=isolation,
    )
