from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.cli import main
from workflow.run import RunResult


class CliTests(unittest.TestCase):
    def test_successful_agents_are_printed_in_registration_order(self) -> None:
        result = RunResult(
            run_dir=Path("run"),
            journal_path=Path("journal.jsonl"),
            mock=True,
        )
        events = [
            {
                "event": "agent",
                "ok": True,
                "index": 2,
                "label": "third",
                "return": "third",
            },
            {
                "event": "agent",
                "ok": True,
                "index": 0,
                "label": "first",
                "return": "first",
            },
            {
                "event": "agent",
                "ok": False,
                "index": 1,
                "label": "failed",
            },
        ]

        stdout = io.StringIO()
        with (
            patch(
                "workflow.cli.supervise_workflow",
                return_value=result,
            ) as run,
            patch("workflow.cli.read_events", return_value=events),
            redirect_stdout(stdout),
        ):
            exit_code = main(["run", "ignored.js", "--mock"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertLess(
            output.index('agent first: "first"'),
            output.index('agent third: "third"'),
        )
        self.assertNotIn("failed", output)
        run.assert_called_once()
        self.assertEqual(
            run.call_args.kwargs["timeout_seconds"],
            3600.0,
        )


if __name__ == "__main__":
    unittest.main()
