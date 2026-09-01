from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import SandboxError
from workflow.journal import read_events
from workflow.run import RunConfig, run_workflow
from workflow.sandbox import run_script


class PhaseTests(unittest.TestCase):
    def test_phase_is_snapshot_at_agent_registration_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "phase.js"
            script.write_text(
                """
                phase("Scan");
                const a = agent("a", { label: "a" });
                phase("Verify");
                const b = agent("b", { label: "b" });
                await parallel([function () { return a; }, function () { return b; }]);
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
                    mock_delay_s=0.05,
                    codex_bin="codex",
                )
            )
            agents = sorted(
                (e for e in read_events(result.journal_path) if e.get("event") == "agent"),
                key=lambda e: e["index"],
            )
            self.assertEqual(
                [(e["label"], e.get("phase")) for e in agents],
                [("a", "Scan"), ("b", "Verify")],
            )

    def test_phase_does_not_create_a_barrier(self) -> None:
        logs: list[str] = []
        run_script(
            """
            phase("A");
            const values = await parallel([
              function () { return agent("one"); },
              function () { phase("B"); return agent("two"); }
            ]);
            log(JSON.stringify(values));
            """,
            on_agent=lambda prompt, opts: prompt,
            on_log=logs.append,
        )
        self.assertEqual(logs, ['["one","two"]'])

    def test_invalid_phase_titles_fail_closed(self) -> None:
        sources = [
            "phase();",
            'phase("");',
            '  phase("   ");',
            "phase(1)+",
            'phase("' + "x" * 81 + '");',
        ]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(SandboxError):
                    run_script(source, on_agent=lambda p, o: p)

    def test_phase_remains_an_unknown_agent_opt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "bad-phase-opt.js"
            script.write_text(
                'await agent("x", { phase: "Scan" });\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=root / "runs",
                        workdir=ROOT,
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("unknown agent() opts", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
