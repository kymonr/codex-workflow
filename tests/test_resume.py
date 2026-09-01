from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import AgentError, SandboxError
from workflow.journal import JOURNAL_VERSION, read_events
from workflow.resume import ResumeCursor
from workflow.run import RunConfig, run_workflow


class ResumeTests(unittest.TestCase):
    def _write_script(self, path: Path, prompts: list[str]) -> None:
        lines = [
            f'await agent("{prompt}", {{ label: "a{index}" }});'
            for index, prompt in enumerate(prompts)
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_journal(
        self,
        run_dir: Path,
        rows: list[dict[str, object]],
    ) -> None:
        run_dir.mkdir()
        text = "".join(
            json.dumps(row, separators=(",", ":")) + "\n"
            for row in rows
        )
        (run_dir / "journal.jsonl").write_text(text, encoding="utf-8")

    def _run(
        self,
        *,
        script: Path,
        runs_root: Path,
        calls: list[str],
        args: object | None = None,
        resume_from: Path | None = None,
    ):
        config_args = {} if args is None else args
        return run_workflow(
            RunConfig(
                script_path=script,
                runs_root=runs_root,
                workdir=ROOT,
                mock=True,
                mock_handler=(
                    lambda prompt, opts: calls.append(prompt) or prompt
                ),
                args=config_args,
                resume_from=resume_from,
                codex_bin="codex",
            )
        )

    def test_same_script_and_args_are_fully_cached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "same.js"
            self._write_script(script, ["one", "two"])

            first_calls: list[str] = []
            first = self._run(
                script=script,
                runs_root=root / "runs",
                calls=first_calls,
                args={"q": 1},
            )
            self.assertEqual(first_calls, ["one", "two"])

            second_calls: list[str] = []
            second = self._run(
                script=script,
                runs_root=root / "runs",
                calls=second_calls,
                args={"q": 1},
                resume_from=first.run_dir,
            )
            self.assertEqual(second_calls, [])
            agents = [
                event
                for event in read_events(second.journal_path)
                if event.get("event") == "agent"
            ]
            self.assertEqual(
                [event.get("cache") for event in agents],
                [True, True],
            )
            self.assertEqual(
                [event["return"] for event in agents],
                ["one", "two"],
            )
            self.assertNotEqual(first.run_dir, second.run_dir)

    def test_first_mismatch_disables_later_cache_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original.js"
            changed = root / "changed.js"
            self._write_script(original, ["same", "old", "tail"])
            self._write_script(changed, ["same", "new", "tail"])

            first = self._run(
                script=original,
                runs_root=root / "runs",
                calls=[],
            )
            calls: list[str] = []
            second = self._run(
                script=changed,
                runs_root=root / "runs",
                calls=calls,
                resume_from=first.run_dir,
            )
            self.assertEqual(calls, ["new", "tail"])
            agents = sorted(
                (
                    event
                    for event in read_events(second.journal_path)
                    if event.get("event") == "agent"
                ),
                key=lambda event: event["index"],
            )
            self.assertEqual(
                [event.get("cache", False) for event in agents],
                [True, False, False],
            )

    def test_args_are_part_of_resume_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "args-identity.js"
            self._write_script(script, ["same"])
            first = self._run(
                script=script,
                runs_root=root / "runs",
                calls=[],
                args={"q": 1},
            )
            calls: list[str] = []
            second = self._run(
                script=script,
                runs_root=root / "runs",
                calls=calls,
                args={"q": 2},
                resume_from=first.run_dir,
            )
            self.assertEqual(calls, ["same"])
            agent = next(
                event
                for event in read_events(second.journal_path)
                if event.get("event") == "agent"
            )
            self.assertFalse(agent.get("cache", False))

    def test_missing_resume_directory_or_journal_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "one.js"
            self._write_script(script, ["one"])
            for resume_from in [root / "missing", root / "empty"]:
                if resume_from.name == "empty":
                    resume_from.mkdir()
                with self.subTest(resume_from=resume_from):
                    with self.assertRaises(AgentError):
                        self._run(
                            script=script,
                            runs_root=root / "runs",
                            calls=[],
                            resume_from=resume_from,
                        )

    def test_failed_old_agent_ends_the_cacheable_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old"
            rows = [
                {
                    "event": "run.started",
                    "journal_version": JOURNAL_VERSION,
                    "args": {},
                },
                {
                    "event": "agent",
                    "index": 0,
                    "prompt": "a",
                    "opts": {
                        "label": "a0",
                        "schema": None,
                        "model": None,
                        "effort": "medium",
                        "isolation": None,
                    },
                    "ok": True,
                    "return": "a",
                },
                {
                    "event": "agent",
                    "index": 1,
                    "prompt": "b",
                    "opts": {
                        "label": "a1",
                        "schema": None,
                        "model": None,
                        "effort": "medium",
                        "isolation": None,
                    },
                    "ok": False,
                    "error": "boom",
                },
                {
                    "event": "agent",
                    "index": 2,
                    "prompt": "c",
                    "opts": {
                        "label": "a2",
                        "schema": None,
                        "model": None,
                        "effort": "medium",
                        "isolation": None,
                    },
                    "ok": True,
                    "return": "c",
                },
            ]
            self._write_journal(old, rows)

            script = root / "new.js"
            self._write_script(script, ["a", "b", "c"])
            calls: list[str] = []
            result = self._run(
                script=script,
                runs_root=root / "runs",
                calls=calls,
                resume_from=old,
            )
            self.assertEqual(calls, ["b", "c"])
            agents = sorted(
                (
                    event
                    for event in read_events(result.journal_path)
                    if event.get("event") == "agent"
                ),
                key=lambda event: event["index"],
            )
            self.assertEqual(
                [event.get("cache", False) for event in agents],
                [True, False, False],
            )

    def test_unsupported_journal_version_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old"
            self._write_journal(
                old,
                [
                    {
                        "event": "run.started",
                        "journal_version": 999,
                        "args": {},
                    }
                ],
            )
            with self.assertRaises(AgentError) as raised:
                ResumeCursor.load(old, {})
            self.assertIn("version", str(raised.exception))

    def test_cached_value_is_revalidated_against_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old"
            self._write_journal(
                old,
                [
                    {
                        "event": "run.started",
                        "journal_version": JOURNAL_VERSION,
                        "args": {},
                    },
                    {
                        "event": "agent",
                        "index": 0,
                        "prompt": "x",
                        "opts": {
                            "label": "a0",
                            "schema": {"type": "integer"},
                            "model": None,
                            "effort": "medium",
                            "isolation": None,
                        },
                        "ok": True,
                        "return": "not-an-integer",
                    },
                ],
            )
            script = root / "schema-cache.js"
            script.write_text(
                "await agent(\"x\", { label: \"a0\", "
                "schema: { type: \"integer\" } });\n",
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError):
                self._run(
                    script=script,
                    runs_root=root / "runs",
                    calls=[],
                    resume_from=old,
                )


if __name__ == "__main__":
    unittest.main()
