from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import SandboxError
from workflow.sandbox import run_script


def _run(source: str, on_agent=None, on_log=None) -> None:
    def default_agent(prompt, opts):
        raise AssertionError(f"agent() should not run: {prompt!r} {opts!r}")

    run_script(source, on_agent=on_agent or default_agent, on_log=on_log)


class SandboxTests(unittest.TestCase):
    def test_date_now_is_disabled(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run("Date.now();")
        self.assertIn("Date.now", str(raised.exception))

    def test_new_date_is_disabled(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run("new Date();")
        self.assertIn("Date is disabled", str(raised.exception))

    def test_math_random_is_disabled(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run("Math.random();")
        self.assertIn("Math.random", str(raised.exception))

    def test_std_is_not_defined(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run('std.open("C:/Windows/win.ini");')
        self.assertRegex(str(raised.exception), r"std is not defined|not defined")

    def test_os_is_not_defined(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run("os.open();")
        self.assertRegex(str(raised.exception), r"os is not defined|not defined")

    def test_require_is_not_defined(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run('require("fs");')
        self.assertRegex(str(raised.exception), r"require is not defined|not defined")

    def test_export_const_meta_is_rewritten(self) -> None:
        _run('export const meta = { name: "t", description: "d" };')

    def test_other_export_is_rejected(self) -> None:
        with self.assertRaises(SandboxError):
            _run("export default {};")

    def test_pipeline_accepts_empty_items(self) -> None:
        _run(
            """
            const values = await pipeline([]);
            if (!Array.isArray(values) || values.length !== 0) {
              throw new Error("unexpected empty pipeline result");
            }
            """
        )

    def test_parallel_rejects_non_function_entries(self) -> None:
        with self.assertRaises(SandboxError) as raised:
            _run("await parallel([function () { return 1; }, 2]);")
        self.assertIn("functions", str(raised.exception))

    def test_workflow_and_phase_stay_unavailable_in_pr2(self) -> None:
        for source, name in [
            ('workflow({ scriptPath: "child.js" });', "workflow()"),
            ('phase("scan");', "phase()"),
        ]:
            with self.subTest(name=name):
                with self.assertRaises(SandboxError) as raised:
                    _run(source)
                self.assertIn("not available in PR2", str(raised.exception))

    def test_agent_returns_parsed_json(self) -> None:
        seen = {}

        def on_agent(prompt, opts):
            seen["prompt"] = prompt
            seen["opts"] = opts
            return {"name": "codex-workflow"}

        _run(
            """
            const result = await agent("who", { label: "hello" });
            if (result.name !== "codex-workflow") {
              throw new Error("unexpected " + result.name);
            }
            """,
            on_agent=on_agent,
        )
        self.assertEqual(seen["prompt"], "who")
        self.assertEqual(seen["opts"]["label"], "hello")


if __name__ == "__main__":
    unittest.main()
