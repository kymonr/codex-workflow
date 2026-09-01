from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import SandboxError
from workflow.journal import read_events
from workflow.run import RunConfig, run_workflow


class PipelineTests(unittest.TestCase):
    def test_items_advance_without_a_stage_barrier(self) -> None:
        timeline: list[str] = []
        timeline_lock = threading.Lock()

        def handler(prompt: str, opts: dict) -> str:
            del opts
            with timeline_lock:
                timeline.append("start:" + prompt)
            if prompt == "s1:a":
                time.sleep(0.25)
            else:
                time.sleep(0.02)
            with timeline_lock:
                timeline.append("end:" + prompt)
            return prompt

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "pipeline.js"
            script.write_text(
                """
                const values = await pipeline(
                  ["a", "b"],
                  function (prev, item) {
                    return agent("s1:" + item, { label: "s1-" + item });
                  },
                  function (prev, item) {
                    return agent("s2:" + item, { label: "s2-" + item });
                  }
                );
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

            self.assertLess(
                timeline.index("start:s2:b"),
                timeline.index("end:s1:a"),
                timeline,
            )
            events = read_events(result.journal_path)
            agents = [event for event in events if event.get("event") == "agent"]
            self.assertEqual(len(agents), 4)
            logs = [event for event in events if event.get("event") == "log"]
            self.assertEqual(json.loads(logs[-1]["message"]), ["s2:a", "s2:b"])

    def test_failed_item_becomes_null_and_skips_later_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "pipeline-error.js"
            script.write_text(
                """
                const values = await pipeline(
                  ["a", "bad", "c"],
                  function (prev, item) {
                    if (item === "bad") throw new Error("bad item");
                    return agent("s1:" + item, { label: "s1-" + item });
                  },
                  function (prev, item) {
                    return agent("s2:" + item, { label: "s2-" + item });
                  }
                );
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
            self.assertEqual(
                {event["prompt"] for event in agents},
                {"s1:a", "s1:c", "s2:a", "s2:c"},
            )
            logs = [event for event in events if event.get("event") == "log"]
            self.assertEqual(
                json.loads(logs[-1]["message"]),
                ["s2:a", None, "s2:c"],
            )

    def test_more_than_4096_items_fails_without_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs_root = root / "runs"
            script = root / "pipeline-too-large.js"
            script.write_text(
                """
                const items = [];
                for (let i = 0; i < 4097; i += 1) items.push(i);
                await pipeline(items, function (prev, item) {
                  return agent("should-not-run:" + item);
                });
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
