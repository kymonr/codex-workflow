from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.argv import FORBIDDEN_SUBSTRINGS
from workflow.errors import SandboxError
from workflow.journal import JOURNAL_VERSION, read_events
from workflow.run import RunConfig, run_workflow


class RunTests(unittest.TestCase):
    def test_hello_mock_writes_locked_journal(self) -> None:
        hello = ROOT / "examples" / "hello.js"
        with tempfile.TemporaryDirectory() as tmp:
            result = run_workflow(
                RunConfig(
                    script_path=hello,
                    runs_root=Path(tmp) / "runs",
                    workdir=ROOT,
                    mock=True,
                    codex_bin="codex",
                )
            )
            events = read_events(result.journal_path)
            kinds = [event["event"] for event in events]
            self.assertEqual(kinds[0], "run.started")
            self.assertEqual(events[0]["journal_version"], JOURNAL_VERSION)
            self.assertEqual(kinds[-1], "run.finished")
            self.assertTrue(events[-1]["ok"])
            agents = [event for event in events if event["event"] == "agent"]
            self.assertEqual(len(agents), 1)
            agent = agents[0]
            self.assertEqual(agent["label"], "hello")
            self.assertEqual(agent["return"], {"name": "codex-workflow"})
            argv = agent["argv"]
            blob = " ".join(argv).lower()
            for forbidden in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(forbidden, blob)
            self.assertEqual(argv[argv.index("-s") + 1], "read-only")
            self.assertEqual(
                argv[argv.index("-c") + 1],
                "model_reasoning_effort=medium",
            )
            self.assertNotIn("workspace-write", argv)
            self.assertNotIn("danger-full-access", argv)
            self.assertNotIn("--full-auto", argv)
            self.assertNotIn("--approval-policy", argv)
            copied = list((result.run_dir).glob("script.*"))
            self.assertEqual(len(copied), 1)
            self.assertTrue((result.run_dir / "agents").is_dir())

    def test_invalid_isolation_opt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "iso.js"
            script.write_text(
                'await agent("x", { isolation: "main" });\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=Path(tmp) / "runs",
                        workdir=ROOT,
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("isolation must be", str(raised.exception))

    def test_unknown_opt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "unknown.js"
            script.write_text(
                'await agent("x", { argv: ["codex"] });\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=Path(tmp) / "runs",
                        workdir=ROOT,
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("agent() cannot set argv", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
