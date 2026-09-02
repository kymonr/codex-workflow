from __future__ import annotations

import io
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow import __version__
from workflow.argv import build_codex_argv
from workflow.cli import main
from workflow.errors import AgentError, ArgvError, SandboxError
from workflow.executor import CodexExecutor, MockExecutor
from workflow.run import RunConfig, run_workflow
from workflow.sandbox import run_script


class ReleaseHardeningTests(unittest.TestCase):
    def test_executor_timing_values_must_be_finite(self) -> None:
        for value in (math.nan, math.inf, -math.inf, 10**400):
            with self.subTest(executor="mock", value=value):
                with self.assertRaises(ValueError):
                    MockExecutor({}, delay_s=value)
            with self.subTest(executor="codex", value=value):
                with self.assertRaises(ValueError):
                    CodexExecutor(timeout_seconds=value)

    def test_direct_argv_rejects_non_string_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ArgvError):
                build_codex_argv(
                    prompt="inspect",
                    workdir=ROOT,
                    last_message_path=Path(tmp) / "last.txt",
                    model=7,
                    codex_bin="codex",
                )

    def test_run_config_validates_model_and_effort_before_artifacts(self) -> None:
        cases = (
            ("effort", "invalid"),
            ("model", "-bad"),
            ("model", 7),
            ("model", "danger-full-access"),
            ("model", "workspace-write"),
            ("model", "x--config"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = {
                "empty": "",
                "agent": 'await agent("inspect");',
            }
            for script_kind, source in scripts.items():
                script = root / f"{script_kind}.js"
                script.write_text(source, encoding="utf-8")
                for field, value in cases:
                    with self.subTest(
                        script=script_kind,
                        field=field,
                        value=value,
                    ):
                        runs_root = root / f"runs-{script_kind}-{field}-{value}"
                        kwargs = {
                            "script_path": script,
                            "runs_root": runs_root,
                            "workdir": ROOT,
                            "mock": True,
                            "codex_bin": "codex",
                            field: value,
                        }
                        with self.assertRaises(AgentError):
                            run_workflow(RunConfig(**kwargs))
                        self.assertFalse(runs_root.exists())

    def test_phase_limit_counts_unicode_characters(self) -> None:
        run_script(
            "phase(" + repr("😀" * 80) + ");",
            on_agent=lambda prompt, opts: prompt,
        )
        with self.assertRaises(SandboxError):
            run_script(
                "phase(" + repr("😀" * 81) + ");",
                on_agent=lambda prompt, opts: prompt,
            )

    def test_cli_exposes_package_version(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(
            stdout.getvalue().strip(),
            f"codex-workflow {__version__}",
        )


if __name__ == "__main__":
    unittest.main()
