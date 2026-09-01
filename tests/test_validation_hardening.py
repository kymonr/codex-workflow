from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.argv import build_codex_argv, validate_codex_argv
from workflow.errors import ArgvError, SchemaError
from workflow.journal import Journal, read_events
from workflow.schema import validate_instance, validate_schema


class ValidationHardeningTests(unittest.TestCase):
    def test_direct_argv_validator_enforces_prompt_limit(self) -> None:
        argv = build_codex_argv(
            prompt="ok",
            workdir=ROOT,
            last_message_path=ROOT / "runs" / "last.txt",
            codex_bin="codex",
        )
        argv[-1] = "x" * 24_001
        with self.assertRaises(ArgvError):
            validate_codex_argv(argv)

    def test_schema_rejects_invalid_keyword_types(self) -> None:
        bad_schemas = [
            {"type": "number", "minimum": "x"},
            {"type": "number", "maximum": True},
            {"type": "string", "minLength": -1},
            {"type": "string", "maxLength": 1.5},
            {"type": "array", "minItems": True},
            {"type": "array", "maxItems": -1},
            {"type": "object", "required": ["x", "x"]},
            {"type": "string", "description": 7},
            {"type": "number", "minimum": 5, "maximum": 4},
            {"type": "array", "minItems": 3, "maxItems": 2},
            {"type": "string", "minLength": 3, "maxLength": 2},
        ]
        for schema in bad_schemas:
            with self.subTest(schema=schema):
                with self.assertRaises(SchemaError):
                    validate_schema(schema)

    def test_schema_rejects_keywords_for_wrong_type(self) -> None:
        bad_schemas = [
            {"type": "string", "properties": {}},
            {"type": "object", "items": {"type": "string"}},
            {"type": "array", "minimum": 0},
            {"type": "number", "minLength": 1},
        ]
        for schema in bad_schemas:
            with self.subTest(schema=schema):
                with self.assertRaises(SchemaError):
                    validate_schema(schema)

    def test_schema_rejects_non_finite_numbers(self) -> None:
        for value in [math.nan, math.inf, -math.inf]:
            with self.subTest(value=value):
                with self.assertRaises(SchemaError):
                    validate_schema({"type": "number", "minimum": value})
                with self.assertRaises(SchemaError):
                    validate_instance(value, {"type": "number"})

    def test_schema_depth_is_bounded(self) -> None:
        schema: dict = {"type": "string"}
        for _ in range(70):
            schema = {"type": "array", "items": schema}
        with self.assertRaises(SchemaError):
            validate_schema(schema)

    def test_huge_integers_are_finite_numbers(self) -> None:
        value = 10**10_000
        validate_schema({"type": "number", "minimum": value})
        validate_instance(value, {"type": "number"})

    def test_journal_constructor_does_not_truncate_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.jsonl"
            path.write_text('{"event":"kept"}\n', encoding="utf-8")
            Journal(path)
            self.assertEqual(read_events(path), [{"event": "kept"}])

    def test_journal_new_writer_explicitly_truncates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.jsonl"
            path.write_text('{"event":"old"}\n', encoding="utf-8")
            journal = Journal(path, truncate=True)
            journal.append({"event": "new"})
            self.assertEqual(read_events(path), [{"event": "new"}])


if __name__ == "__main__":
    unittest.main()
