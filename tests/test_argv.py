from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.argv import FORBIDDEN_SUBSTRINGS, build_codex_argv, validate_codex_argv
from workflow.errors import ArgvError


class ArgvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workdir = Path("D:/codex/projects/codex-workflow")
        self.last = Path("D:/codex/projects/codex-workflow/runs/last.txt")
        self.schema = Path("D:/codex/projects/codex-workflow/runs/schema.json")

    def test_builder_locks_read_only_and_effort(self) -> None:
        argv = build_codex_argv(
            prompt="hello",
            workdir=self.workdir,
            last_message_path=self.last,
            schema_path=self.schema,
            effort="medium",
            model="gpt-5.6-luna",
            codex_bin="codex",
        )
        blob = " ".join(argv).lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(forbidden, blob)
        self.assertEqual(argv[0], "codex")
        self.assertEqual(argv[1], "exec")
        self.assertEqual(argv[argv.index("-s") + 1], "read-only")
        self.assertEqual(
            argv[argv.index("-c") + 1],
            "model_reasoning_effort=medium",
        )
        self.assertEqual(argv[argv.index("--color") + 1], "never")
        self.assertEqual(argv[-1], "hello")
        self.assertIn("--output-schema", argv)
        self.assertIn("-m", argv)

    def test_rejects_workspace_write(self) -> None:
        with self.assertRaises(ArgvError):
            validate_codex_argv(
                ["codex", "exec", "-s", "workspace-write", "hello"]
            )

    def test_rejects_danger_full_access(self) -> None:
        with self.assertRaises(ArgvError):
            validate_codex_argv(
                ["codex", "exec", "-s", "danger-full-access", "hello"]
            )

    def test_rejects_full_auto(self) -> None:
        with self.assertRaises(ArgvError):
            validate_codex_argv(
                ["codex", "exec", "-s", "read-only", "--full-auto", "hello"]
            )

    def test_rejects_approval_policy(self) -> None:
        with self.assertRaises(ArgvError):
            validate_codex_argv(
                [
                    "codex",
                    "exec",
                    "-s",
                    "read-only",
                    "--approval-policy",
                    "never",
                    "hello",
                ]
            )

    def test_rejects_extra_c_config(self) -> None:
        with self.assertRaises(ArgvError):
            validate_codex_argv(
                [
                    "codex",
                    "exec",
                    "-s",
                    "read-only",
                    "-C",
                    str(self.workdir),
                    "-c",
                    "model_reasoning_effort=medium",
                    "-c",
                    "sandbox=danger-full-access",
                    "--color",
                    "never",
                    "--output-last-message",
                    str(self.last),
                    "hello",
                ]
            )

    def test_rejects_invalid_effort(self) -> None:
        with self.assertRaises(ArgvError):
            build_codex_argv(
                prompt="hello",
                workdir=self.workdir,
                last_message_path=self.last,
                effort="unlimited",
            )

    def test_rejects_model_looking_like_flag(self) -> None:
        with self.assertRaises(ArgvError):
            build_codex_argv(
                prompt="hello",
                workdir=self.workdir,
                last_message_path=self.last,
                model="--full-auto",
            )


if __name__ == "__main__":
    unittest.main()
