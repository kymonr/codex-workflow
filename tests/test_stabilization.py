from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import AgentError, SandboxError
from workflow.journal import read_events
from workflow.run import RunConfig, parse_agent_opts, run_workflow
from workflow.sandbox import run_script


class StabilizationTests(unittest.TestCase):
    def test_runtime_state_and_host_callables_are_not_exposed(self) -> None:
        logs: list[str] = []
        run_script(
            """
            const hidden = [
              "__pending", "__deliver", "__done", "__error",
              "__agent_start", "__log"
            ];
            for (const name of hidden) {
              if (typeof globalThis[name] !== "undefined") {
                throw new Error("runtime global exposed: " + name);
              }
            }

            __done = true;
            __error = "forged";
            agent = function () { return "forged"; };

            const value = await agent("real");
            log(value);
            """,
            on_agent=lambda prompt, opts: prompt,
            on_log=logs.append,
        )
        self.assertEqual(logs, ["real"])

    def test_indirect_function_constructors_are_disabled(self) -> None:
        sources = [
            '(function () {}).constructor("return 7")();',
            '({}).constructor.constructor("return 7")();',
            'Object.getPrototypeOf(async function () {}).constructor("return 7")();',
            'Object.getPrototypeOf(function* () {}).constructor("return 7")();',
            'Object.getPrototypeOf(async function* () {}).constructor("return 7")();',
        ]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(SandboxError) as raised:
                    run_script(source, on_agent=lambda prompt, opts: prompt)
                self.assertIn("disabled", str(raised.exception).lower())

    def test_date_cannot_be_replaced(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            run_script(
                'Date = function () { this.value = 9; }; new Date();',
                on_agent=lambda prompt, opts: prompt,
            )
        self.assertIn("Date is disabled", str(raised.exception))

    def test_runtime_uses_captured_intrinsics(self) -> None:
        logs: list[str] = []
        run_script(
            """
            Promise.prototype.then = function () { throw new Error("tampered then"); };
            Promise.prototype.catch = function () { throw new Error("tampered catch"); };
            Array.prototype.map = function () { throw new Error("tampered map"); };
            Array.prototype[Symbol.iterator] = function () {
              throw new Error("tampered iterator");
            };
            JSON.parse = function () { throw new Error("tampered parse"); };
            JSON.stringify = function () { throw new Error("tampered stringify"); };
            String.prototype.trim = function () { return ""; };

            const values = await parallel([
              function () { return agent("safe"); }
            ]);
            log(values[0]);
            """,
            on_agent=lambda prompt, opts: prompt,
            on_log=logs.append,
        )
        self.assertEqual(logs, ["safe"])

    def test_agent_indices_follow_js_registration_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "order.js"
            script.write_text(
                """
                await parallel([
                  function () { return agent("first-prompt", { label: "first" }); },
                  function () { return agent("second-prompt", { label: "second" }); }
                ]);
                """,
                encoding="utf-8",
            )

            from workflow import run as run_module

            original_parse = run_module.parse_agent_opts

            def delayed_parse(opts):
                if opts.get("label") == "first":
                    time.sleep(0.08)
                return original_parse(opts)

            with patch("workflow.run.parse_agent_opts", side_effect=delayed_parse):
                result = run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=root / "runs",
                        workdir=ROOT,
                        mock=True,
                        mock_handler=lambda prompt, opts: prompt,
                        codex_bin="codex",
                    )
                )

            agents = sorted(
                (
                    event
                    for event in read_events(result.journal_path)
                    if event.get("event") == "agent"
                ),
                key=lambda event: event["index"],
            )
            self.assertEqual(
                [(event["index"], event["label"]) for event in agents],
                [(0, "first"), (1, "second")],
            )

    def test_preflight_failure_is_journaled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "bad-prompt.js"
            script.write_text(
                """
                const values = await parallel([
                  function () { return agent("-bad", { label: "bad" }); }
                ]);
                log(JSON.stringify(values));
                """,
                encoding="utf-8",
            )
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    codex_bin="codex",
                )
            )

            events = read_events(result.journal_path)
            agents = [event for event in events if event.get("event") == "agent"]
            self.assertEqual(len(agents), 1)
            self.assertEqual(agents[0]["index"], 0)
            self.assertFalse(agents[0]["ok"])
            self.assertEqual(agents[0]["stage"], "argv")
            self.assertIn("must not start with -", agents[0]["error"])
            self.assertEqual(events[-1]["event"], "run.finished")
            self.assertTrue(events[-1]["ok"])
            self.assertEqual(events[-1]["agents"], 1)

    def test_empty_model_and_effort_fail_closed(self) -> None:
        for opts in [{"model": ""}, {"effort": ""}]:
            with self.subTest(opts=opts):
                with self.assertRaises(AgentError):
                    parse_agent_opts(opts)


if __name__ == "__main__":
    unittest.main()
