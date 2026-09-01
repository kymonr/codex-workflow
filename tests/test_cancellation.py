from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import AgentError, SandboxError
from workflow.executor import CodexExecutor, MockExecutor
from workflow.sandbox import run_script


class CancellationTests(unittest.TestCase):
    def test_script_failure_cancels_other_inflight_agents(self) -> None:
        slow_started = threading.Event()
        cancelled = threading.Event()

        def on_agent(prompt: str, opts: dict) -> str:
            del opts
            if prompt == "slow":
                slow_started.set()
                if not cancelled.wait(5):
                    raise AssertionError("slow agent was not cancelled")
                raise AgentError("slow agent cancelled")
            if not slow_started.wait(2):
                raise AssertionError("slow agent did not start")
            raise AgentError("primary failure")

        started = time.perf_counter()
        with self.assertRaises(SandboxError) as raised:
            run_script(
                """
                const slow = agent("slow");
                await agent("bad");
                await slow;
                """,
                on_agent=on_agent,
                on_cancel=cancelled.set,
                max_concurrency=2,
            )
        elapsed = time.perf_counter() - started
        self.assertIn("primary failure", str(raised.exception))
        self.assertTrue(cancelled.is_set())
        self.assertLess(elapsed, 3.0)

    def test_mock_executor_delay_is_interruptible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slot = Path(tmp)
            executor = MockExecutor("ok", delay_s=30)
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    executor.run,
                    argv=["codex"],
                    slot=slot,
                    schema=None,
                    prompt="mock",
                    opts={},
                )
                time.sleep(0.05)
                executor.cancel_all()
                with self.assertRaises(AgentError):
                    future.result(timeout=3)
            self.assertLess(time.perf_counter() - started, 3.0)

    def test_real_executor_cancels_its_process_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slot = Path(tmp)
            ready = slot / "ready.txt"
            code = (
                "from pathlib import Path\n"
                f"Path({str(ready)!r}).write_text('ready', encoding='utf-8')\n"
                "import time\n"
                "time.sleep(30)\n"
            )
            executor = CodexExecutor(timeout_seconds=30)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    executor.run,
                    argv=[sys.executable, "-c", code],
                    slot=slot,
                    schema=None,
                    prompt="fake",
                    opts={},
                )
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists(), "fake process did not start")
                started = time.perf_counter()
                executor.cancel_all()
                with self.assertRaises(AgentError) as raised:
                    future.result(timeout=5)
            self.assertIn("cancel", str(raised.exception).lower())
            self.assertLess(time.perf_counter() - started, 5.0)


if __name__ == "__main__":
    unittest.main()
