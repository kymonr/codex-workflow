from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import SandboxError
from workflow.pump import default_max_concurrency
from workflow.sandbox import run_script


class PumpTests(unittest.TestCase):
    def test_default_concurrency_uses_cpu_count_with_bounds(self) -> None:
        cases = [
            (32, 16),
            (16, 14),
            (4, 2),
            (2, 1),
            (1, 1),
            (None, 1),
        ]
        for cpu_count, expected in cases:
            with self.subTest(cpu_count=cpu_count):
                with patch("workflow.pump.os.cpu_count", return_value=cpu_count):
                    self.assertEqual(default_max_concurrency(), expected)

    def test_inflight_agents_do_not_exceed_cap(self) -> None:
        lock = threading.Lock()
        active = 0
        peak = 0
        calls: list[str] = []

        def on_agent(prompt: str, opts: dict) -> str:
            nonlocal active, peak
            del opts
            with lock:
                active += 1
                peak = max(peak, active)
                calls.append(prompt)
            try:
                time.sleep(0.03)
                return prompt
            finally:
                with lock:
                    active -= 1

        run_script(
            """
            const thunks = [];
            for (let i = 0; i < 6; i += 1) {
              thunks.push(function () { return agent("p" + i); });
            }
            await parallel(thunks);
            """,
            on_agent=on_agent,
            max_concurrency=2,
        )
        self.assertEqual(len(calls), 6)
        self.assertEqual(peak, 2)

    def test_agent_limit_rejects_the_next_call(self) -> None:
        calls: list[str] = []

        def on_agent(prompt: str, opts: dict) -> str:
            del opts
            calls.append(prompt)
            return prompt

        with self.assertRaises(SandboxError) as raised:
            run_script(
                """
                await agent("a");
                await agent("b");
                await agent("c");
                """,
                on_agent=on_agent,
                max_agents=2,
            )
        self.assertIn("max-agents", str(raised.exception))
        self.assertEqual(calls, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
