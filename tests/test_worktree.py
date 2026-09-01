from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.argv import build_codex_argv, validate_codex_argv
from workflow.errors import AgentError, ArgvError, SandboxError
from workflow.journal import read_events
from workflow.run import RunConfig, parse_agent_opts, run_workflow
from workflow.worktree import default_worktree_root


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def _init_repo(path: Path) -> None:
    path.mkdir()
    _git("init", cwd=path)
    _git("config", "user.email", "tests@example.invalid", cwd=path)
    _git("config", "user.name", "Workflow Tests", cwd=path)
    (path / "base.txt").write_text("base\n", encoding="utf-8")
    _git("add", "base.txt", cwd=path)
    _git("commit", "-m", "base", cwd=path)


class WorktreeTests(unittest.TestCase):
    def test_default_worktree_root_is_platform_appropriate(self) -> None:
        root = default_worktree_root()
        self.assertTrue(root.is_absolute())
        if os.name == "nt":
            self.assertEqual(root.drive.upper(), "D:")
        else:
            self.assertIn(".codex-tmp", root.parts)

    def test_workspace_write_requires_host_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            argv = build_codex_argv(
                prompt="edit",
                workdir=root,
                last_message_path=root / "last.txt",
                sandbox="workspace-write",
                worktree_authorized=True,
                codex_bin="codex",
            )
            self.assertEqual(argv[argv.index("-s") + 1], "workspace-write")
            validate_codex_argv(argv, worktree_authorized=True)
            with self.assertRaises(ArgvError):
                validate_codex_argv(argv)
            with self.assertRaises(ArgvError):
                build_codex_argv(
                    prompt="edit",
                    workdir=root,
                    last_message_path=root / "last.txt",
                    sandbox="workspace-write",
                    codex_bin="codex",
                )

    def test_workspace_write_token_is_rejected_outside_sandbox_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaises(ArgvError):
                build_codex_argv(
                    prompt="mention workspace-write",
                    workdir=root,
                    last_message_path=root / "last.txt",
                    sandbox="workspace-write",
                    worktree_authorized=True,
                    codex_bin="codex",
                )

    def test_isolation_option_only_accepts_worktree(self) -> None:
        self.assertEqual(
            parse_agent_opts({"isolation": "worktree"})["isolation"],
            "worktree",
        )
        for value in ["", "none", "read-only", 1, True, {}]:
            with self.subTest(value=value):
                with self.assertRaises(AgentError):
                    parse_agent_opts({"isolation": value})

    def test_worktree_agent_uses_host_path_and_workspace_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            _init_repo(repo)
            script = root / "worktree.js"
            script.write_text(
                'await agent("edit", { isolation: "worktree", label: "writer" });\n',
                encoding="utf-8",
            )
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=repo,
                    worktree_root=root / "worktrees",
                    mock=True,
                    mock_handler=lambda prompt, opts: prompt,
                    codex_bin="codex",
                )
            )
            agent = next(
                event
                for event in read_events(result.journal_path)
                if event.get("event") == "agent"
            )
            self.assertTrue(agent["ok"])
            self.assertEqual(agent["opts"]["isolation"], "worktree")
            argv = agent["argv"]
            self.assertEqual(argv[argv.index("-s") + 1], "workspace-write")
            worktree = Path(argv[argv.index("-C") + 1])
            self.assertTrue(worktree.is_dir())
            self.assertNotEqual(worktree.resolve(), repo.resolve())
            inside = _git("rev-parse", "--is-inside-work-tree", cwd=worktree)
            self.assertEqual(inside.stdout.strip(), "true")
            self.assertEqual((repo / "base.txt").read_text(encoding="utf-8"), "base\n")
            _git("worktree", "remove", "--force", str(worktree), cwd=repo)

    def test_default_agent_remains_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "readonly.js"
            script.write_text('await agent("read");\n', encoding="utf-8")
            result = run_workflow(
                RunConfig(
                    script_path=script,
                    runs_root=root / "runs",
                    workdir=ROOT,
                    mock=True,
                    codex_bin="codex",
                )
            )
            agent = next(
                event
                for event in read_events(result.journal_path)
                if event.get("event") == "agent"
            )
            argv = agent["argv"]
            self.assertEqual(argv[argv.index("-s") + 1], "read-only")
            self.assertNotIn("workspace-write", argv)

    def test_worktree_requires_a_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workdir = root / "not-git"
            workdir.mkdir()
            script = root / "bad.js"
            script.write_text(
                'await agent("edit", { isolation: "worktree" });\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=root / "runs",
                        workdir=workdir,
                        worktree_root=root / "worktrees",
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("git repository", str(raised.exception).lower())


    def test_worktree_root_cannot_be_inside_git_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            _init_repo(repo)
            subdir = repo / "subdir"
            subdir.mkdir()
            script = root / "inside.js"
            script.write_text(
                'await agent("edit", { isolation: "worktree" });\n',
                encoding="utf-8",
            )
            with self.assertRaises(SandboxError) as raised:
                run_workflow(
                    RunConfig(
                        script_path=script,
                        runs_root=root / "runs",
                        workdir=subdir,
                        worktree_root=repo / "forbidden-worktrees",
                        mock=True,
                        codex_bin="codex",
                    )
                )
            self.assertIn("outside the main repository", str(raised.exception))



if __name__ == "__main__":
    unittest.main()
