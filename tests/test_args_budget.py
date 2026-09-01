from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.cli import load_args
from workflow.errors import AgentError, SandboxError
from workflow.journal import read_events
from workflow.run import RunConfig, run_workflow
from workflow.sandbox import run_script


class ArgsBudgetTests(unittest.TestCase):
    def test_args_are_available_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "args.js"
            script.write_text('log(String(args.q));\n', encoding="utf-8")
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    args={"q": 1},
                    codex_bin="codex",
                )
            )
            events = read_events(result.journal_path)
            self.assertEqual(events[0]["args"], {"q": 1})
            logs = [e["message"] for e in events if e.get("event") == "log"]
            self.assertEqual(logs, ["1"])

    def test_args_text_and_file_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "args.json"
            path.write_text('{"q":2}', encoding="utf-8")
            with self.assertRaises(AgentError):
                load_args('{"q":1}', path)

    def test_invalid_args_json_fails_closed(self) -> None:
        with self.assertRaises(AgentError):
            load_args("{bad", None)

    def test_args_file_is_loaded_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "args.json"
            path.write_text('{"q":2}', encoding="utf-8")
            self.assertEqual(load_args(None, path), {"q": 2})

    def test_default_budget_is_honest(self) -> None:
        logs: list[str] = []
        run_script(
            """
            log(String(budget.total));
            log(String(budget.spent()));
            log(String(budget.remaining()));
            """,
            on_agent=lambda prompt, opts: prompt,
            on_log=logs.append,
        )
        self.assertEqual(logs, ["null", "0", "Infinity"])

    def test_configured_budget_does_not_fake_spend(self) -> None:
        logs: list[str] = []
        run_script(
            """
            log(String(budget.total));
            log(String(budget.spent()));
            log(String(budget.remaining()));
            """,
            on_agent=lambda prompt, opts: prompt,
            on_log=logs.append,
            budget_tokens=500,
        )
        self.assertEqual(logs, ["500", "0", "500"])

    def test_max_agents_rejects_third_live_call(self) -> None:
        calls: list[str] = []
        with self.assertRaises(SandboxError) as raised:
            run_script(
                """
                await agent("a");
                await agent("b");
                await agent("c");
                """,
                on_agent=lambda prompt, opts: calls.append(prompt) or prompt,
                max_agents=2,
            )
        self.assertIn("max-agents", str(raised.exception))
        self.assertEqual(calls, ["a", "b"])

    def test_run_started_records_budget_and_max_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "config.js"
            script.write_text('log("ok");\n', encoding="utf-8")
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    budget_tokens=123,
                    max_agents=7,
                    codex_bin="codex",
                )
            )
            started = read_events(result.journal_path)[0]
            self.assertEqual(started["budget_tokens"], 123)
            self.assertEqual(started["max_agents"], 7)

    def test_invalid_budget_and_max_agents_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "bad.js"
            script.write_text("", encoding="utf-8")
            for budget in [0, -1, True]:
                with self.subTest(budget=budget):
                    with self.assertRaises(AgentError):
                        run_workflow(
                            RunConfig(
                                script_path=script,
                                runs_root=root / "runs",
                                workdir=ROOT,
                                mock=True,
                                budget_tokens=budget,
                                codex_bin="codex",
                            )
                        )
            for limit in [0, 1001, True]:
                with self.subTest(limit=limit):
                    with self.assertRaises(AgentError):
                        run_workflow(
                            RunConfig(
                                script_path=script,
                                runs_root=root / "runs",
                                workdir=ROOT,
                                mock=True,
                                max_agents=limit,
                                codex_bin="codex",
                            )
                        )


    def test_max_agents_rejection_is_journaled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "limit.js"
            script.write_text(
                """
                await parallel([
                  function () { return agent("a"); },
                  function () { return agent("b"); },
                  function () { return agent("c"); }
                ]);
                """,
                encoding="utf-8",
            )
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    max_agents=2,
                    mock_handler=lambda prompt, opts: prompt,
                    codex_bin="codex",
                )
            )
            agents = [
                event
                for event in read_events(result.journal_path)
                if event.get("event") == "agent"
            ]
            self.assertEqual(len(agents), 3)
            rejected = next(event for event in agents if not event.get("ok"))
            self.assertEqual(rejected["stage"], "limit")
            self.assertIn("max-agents", rejected["error"])



    def test_preflight_failure_does_not_consume_live_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "preflight-limit.js"
            script.write_text(
                """
                await parallel([function () { return agent("-bad"); }]);
                await agent("good", { label: "good" });
                """,
                encoding="utf-8",
            )
            calls: list[str] = []
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    mock_handler=lambda prompt, opts: calls.append(prompt) or prompt,
                    max_agents=1,
                    codex_bin="codex",
                )
            )
            self.assertEqual(calls, ["good"])
            agents = [
                event for event in read_events(result.journal_path)
                if event.get("event") == "agent"
            ]
            self.assertEqual(len(agents), 2)
            self.assertTrue(any(event.get("ok") for event in agents))


if __name__ == "__main__":
    unittest.main()
