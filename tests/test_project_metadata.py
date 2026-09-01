from __future__ import annotations

import json
import re
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow import __version__


class ProjectMetadataTests(unittest.TestCase):
    def test_package_metadata_and_version_are_in_sync(self) -> None:
        data = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        project = data["project"]
        self.assertEqual(project["name"], "codex-workflow")
        self.assertEqual(project["version"], __version__)
        self.assertEqual(
            project["scripts"]["codex-workflow"],
            "workflow.cli:main",
        )
        self.assertEqual(project["readme"]["file"], "README.md")

    def test_readme_local_links_exist(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
        local = [
            link.split("#", 1)[0]
            for link in links
            if link and not link.startswith(("http://", "https://", "#"))
        ]
        self.assertTrue(local)
        missing = [link for link in local if not (ROOT / link).exists()]
        self.assertEqual(missing, [])

    def test_markdown_fences_are_balanced(self) -> None:
        markdown = [ROOT / "README.md"]
        markdown.extend((ROOT / "docs").glob("*.md"))
        markdown.extend(
            [
                ROOT / "CHANGELOG.md",
                ROOT / "CONTRIBUTING.md",
                ROOT / "RELEASE_CHECKLIST.md",
                ROOT / "SECURITY.md",
            ]
        )
        for path in markdown:
            with self.subTest(path=path.name):
                lines = path.read_text(encoding="utf-8").splitlines()
                fences = sum(line.startswith("```") for line in lines)
                self.assertEqual(fences % 2, 0, path)

    def test_github_actions_are_pinned_and_least_privilege(self) -> None:
        path = ROOT / ".github" / "workflows" / "tests.yml"
        text = path.read_text(encoding="utf-8")
        uses = re.findall(r"uses:\s+([^@\s]+)@([^\s#]+)", text)
        self.assertGreaterEqual(len(uses), 2)
        for action, reference in uses:
            with self.subTest(action=action):
                self.assertRegex(reference, r"^[0-9a-f]{40}$")
        self.assertNotIn("actions/checkout@v", text)
        self.assertNotIn("actions/setup-python@v", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("persist-credentials: false", text)

    def test_nested_smoke_uses_portable_args_file(self) -> None:
        args_path = ROOT / "examples" / "nested-args.json"
        self.assertEqual(
            json.loads(args_path.read_text(encoding="utf-8")),
            {"q": 7},
        )
        ci = (
            ROOT / ".github" / "workflows" / "tests.yml"
        ).read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        marker = "--args-file examples/nested-args.json"
        self.assertIn(marker, ci)
        self.assertIn(marker, contributing)
        self.assertIn(marker, readme)


if __name__ == "__main__":
    unittest.main()
