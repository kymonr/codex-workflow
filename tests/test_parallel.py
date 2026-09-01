from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.argv import FORBIDDEN_SUBSTRINGS
from workflow.errors import SandboxError
from workflow.journal import read_events
from workflow.run import RunConfig, run_workflow


class ParallelTests(unittest.TestCase):
    def test_three_agents_overlap_and_keep_locked_argv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "parallel.js"
            script.write_text(
                """
                const values = await parallel([
                  function () { return agent("p0", { label: "p0" }); },
                  function () { return agent("p1", { label: "p1" }); },
                  function () { return agent("p2", { label: "p2" }); }
                ]);
                log(JSON.stringify(values));
                """,
                encoding="utf-8",
            )

            started = time.perf_counter()
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    mock_handler=lambda prompt, opts: prompt,
                    mock_delay_s=0.2,
                    codex_bin="codex",
                )
            )
            elapsed = time.perf_counter() - started

            self.assertLess(elapsed, 0.5, f"parallel agents took {elapsed:.3f}s")
            events = read_events(result.journal_path)
            agents = [event for event in events if event.get("event") == "agent"]
            self.assertEqual(len(agents), 3)
            self.assertTrue(all(event.get("ok") for event in agents))
            logs = [event for event in events if event.get("event") == "log"]
            self.assertEqual(json.loads(logs[-1]["message"]), ["p0", "p1", "p2"])

            for event in agents:
                argv = event["argv"]
                self.assertEqual(argv[argv.index("-s") + 1], "read-only")
                blob = " ".join(argv).lower()
                for forbidden in FORBIDDEN_SUBSTRINGS:
                    self.assertNotIn(forbidden, blob)

    def test_throwing_thunk_becomes_null_and_siblings_continue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "parallel-error.js"
            script.write_text(
                """
                const values = await parallel([
                  function () { return agent("left", { label: "left" }); },
                  function () { throw new Error("boom"); },
                  function () { return agent("right", { label: "right" }); }
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
                    mock_handler=lambda prompt, opts: prompt,
                    codex_bin="codex",
                )
            )

            events = read_events(result.journal_path)
            agents = [event for event in events if event.get("event") == "agent"]
            self.assertEqual({event["label"] for event in agents}, {"left", "right"})
            self.assertTrue(all(event.get("ok") for event in agents))
            logs = [event for event in events if event.get("event") == "log"]
            self.assertEqual(json.loads(logs[-1]["message"]), ["left", None, "right"])

    def test_rejected_agent_becomes_null_and_siblings_continue(self) -> None:
        def handler(prompt: str, opts: dict) -> str:
            del opts
            if prompt == "bad":
                raise RuntimeError("mock failure")
            return prompt

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "parallel-rejection.js"
            script.write_text(
                """
                const values = await parallel([
                  function () { return agent("left", { label: "left" }); },
                  function () { return agent("bad", { label: "bad" }); },
                  function () { return agent("right", { label: "right" }); }
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
                    mock_handler=handler,
                    codex_bin="codex",
                )
            )

            events = read_events(result.journal_path)
            agents = [event for event in events if event.get("event") == "agent"]
            self.assertEqual(len(agents), 3)
            self.assertEqual(sum(1 for event in agents if not event.get("ok")), 1)
            logs = [event for event in events if event.get("event") == "log"]
            self.assertEqual(json.loads(logs[-1]["message"]), ["left", None, "right"])
            self.assertTrue(events[-1]["ok"])

    def test_more_than_4096_thunks_fail_without_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs_root = root / "runs"
            script = root / "parallel-too-large.js"
            script.write_text(
                """
                const thunks = [];
                for (let i = 0; i < 4097; i += 1) {
                  thunks.push(function () { return agent("should-not-run"); });
                }
                await parallel(thunks);
                """,
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=runs_root,
                        workdir=ROOT,
                        mock=True,
                        mock_handler=lambda prompt, opts: prompt,
                        codex_bin="codex",
                    )
                )
            self.assertIn("4096", str(raised.exception))

            run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            events = read_events(run_dirs[0] / "journal.jsonl")
            self.assertFalse(any(event.get("event") == "agent" for event in events))
            self.assertEqual(events[-1]["event"], "run.finished")
            self.assertFalse(events[-1]["ok"])


if __name__ == "__main__":
    unittest.main()
