from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.journal import read_events
from workflow.run import RunConfig
from workflow.supervisor import SupervisorError, supervise_workflow


class SupervisorTests(unittest.TestCase):
    def test_supervisor_completes_a_mock_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "ok.js"
            script.write_text(
                'await agent("ok", { label: "ok" });\n',
                encoding="utf-8",
            )
            result = supervise_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    codex_bin="codex",
                ),
                timeout_seconds=10,
            )
            agents = [
                event
                for event in read_events(result.journal_path)
                if event.get("event") == "agent"
            ]
            self.assertEqual(len(agents), 1)
            self.assertTrue(agents[0]["ok"])

    def test_supervisor_terminates_a_synchronous_infinite_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "loop.js"
            script.write_text("while (true) {}\n", encoding="utf-8")
            started = time.perf_counter()
            with self.assertRaises(SupervisorError) as raised:
                supervise_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=root / "runs",
                        workdir=ROOT,
                        mock=True,
                        codex_bin="codex",
                    ),
                    timeout_seconds=0.5,
                )
            elapsed = time.perf_counter() - started
            self.assertIn("timed out", str(raised.exception))
            self.assertLess(elapsed, 5.0)

    def test_timeout_must_be_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "empty.js"
            script.write_text("", encoding="utf-8")
            with self.assertRaises(SupervisorError):
                supervise_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=root / "runs",
                        workdir=ROOT,
                        mock=True,
                        codex_bin="codex",
                    ),
                    timeout_seconds=0,
                )


if __name__ == "__main__":
    unittest.main()
