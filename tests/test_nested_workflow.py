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


class NestedWorkflowTests(unittest.TestCase):
    def _write_pair(
        self,
        root: Path,
        *,
        parent_source: str,
        child_source: str,
    ) -> tuple[Path, Path]:
        workdir = root / "workspace"
        workdir.mkdir()
        parent = workdir / "parent.js"
        child = workdir / "child.js"
        parent.write_text(parent_source, encoding="utf-8")
        child.write_text(child_source, encoding="utf-8")
        return workdir, parent

    def test_parent_and_child_share_index_journal_and_child_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir, parent = self._write_pair(
                root,
                parent_source="""
                await agent("parent", { label: "parent" });
                const result = await workflow(
                  { scriptPath: "child.js" },
                  { q: 1 }
                );
                log("result=" + String(result));
                """,
                child_source="""
                log("q=" + String(args.q));
                await agent("child:" + args.q, { label: "child" });
                """,
            )
            result = run_workflow(
                RunConfig(
                    script_path=parent,
                    runs_root=root / "runs",
                    workdir=workdir,
                    mock=True,
                    mock_handler=lambda prompt, opts: prompt,
                    codex_bin="codex",
                )
            )
            events = read_events(result.journal_path)
            agents = sorted(
                (event for event in events if event.get("event") == "agent"),
                key=lambda event: event["index"],
            )
            self.assertEqual(
                [(event["index"], event["label"]) for event in agents],
                [(0, "parent"), (1, "child")],
            )
            self.assertEqual(
                [event["return"] for event in agents],
                ["parent", "child:1"],
            )
            logs = [
                event["message"]
                for event in events
                if event.get("event") == "log"
            ]
            self.assertIn("q=1", logs)
            self.assertIn("result=null", logs)

    def test_child_cannot_start_a_nested_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir, parent = self._write_pair(
                root,
                parent_source='await workflow({ scriptPath: "child.js" });\n',
                child_source='await workflow({ scriptPath: "grandchild.js" });\n',
            )
            (workdir / "grandchild.js").write_text(
                'await agent("must-not-run");\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=parent,
                        runs_root=root / "runs",
                        workdir=workdir,
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("nested workflow", str(raised.exception).lower())
            run_dir = next((root / "runs").iterdir())
            self.assertFalse(
                any(
                    event.get("event") == "agent"
                    for event in read_events(run_dir / "journal.jsonl")
                )
            )

    def test_child_path_must_remain_inside_workdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir, parent = self._write_pair(
                root,
                parent_source='await workflow({ scriptPath: "../outside.js" });\n',
                child_source="",
            )
            (root / "outside.js").write_text(
                'await agent("outside");\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=parent,
                        runs_root=root / "runs",
                        workdir=workdir,
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("workdir", str(raised.exception).lower())

    def test_workflow_spec_is_strict(self) -> None:
        sources = [
            'await workflow("child.js");',
            'await workflow({ scriptPath: "child.js", extra: true });',
            'await workflow({ scriptPath: "" });',
            'await workflow({});',
        ]
        for source in sources:
            with self.subTest(source=source):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    workdir, parent = self._write_pair(
                        root,
                        parent_source=source,
                        child_source="",
                    )
                    with self.assertRaises(SandboxError):
                        run_workflow(
                            RunConfig(
                                script_path=parent,
                                runs_root=root / "runs",
                                workdir=workdir,
                                mock=True,
                                codex_bin="codex",
                            )
                        )

    def test_resume_pointer_is_shared_with_child_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir, parent = self._write_pair(
                root,
                parent_source="""
                await agent("parent", { label: "parent" });
                await workflow({ scriptPath: "child.js" }, { q: 2 });
                """,
                child_source="""
                await agent("child:" + args.q, { label: "child" });
                """,
            )
            first = run_workflow(
                RunConfig(
                    script_path=parent,
                    runs_root=root / "runs",
                    workdir=workdir,
                    mock=True,
                    mock_handler=lambda prompt, opts: prompt,
                    codex_bin="codex",
                )
            )
            calls: list[str] = []
            second = run_workflow(
                RunConfig(
                    script_path=parent,
                    runs_root=root / "runs",
                    workdir=workdir,
                    mock=True,
                    mock_handler=lambda prompt, opts: calls.append(prompt) or prompt,
                    resume_from=first.run_dir,
                    codex_bin="codex",
                )
            )
            agents = [
                event
                for event in read_events(second.journal_path)
                if event.get("event") == "agent"
            ]
            self.assertEqual(calls, [])
            self.assertEqual([event.get("cache") for event in agents], [True, True])

    def test_max_agents_is_shared_with_child_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir, parent = self._write_pair(
                root,
                parent_source="""
                await agent("parent");
                await workflow({ scriptPath: "child.js" });
                """,
                child_source='await agent("child");\n',
            )
            calls: list[str] = []
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=parent,
                        runs_root=root / "runs",
                        workdir=workdir,
                        mock=True,
                        mock_handler=lambda prompt, opts: calls.append(prompt) or prompt,
                        max_agents=1,
                        codex_bin="codex",
                    )
                )
            self.assertIn("max-agents", str(raised.exception))
            self.assertEqual(calls, ["parent"])

    def test_child_uses_the_same_sandbox_restrictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir, parent = self._write_pair(
                root,
                parent_source='await workflow({ scriptPath: "child.js" });\n',
                child_source="Date.now();\n",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=parent,
                        runs_root=root / "runs",
                        workdir=workdir,
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("Date.now", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
