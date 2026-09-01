from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.errors import SchemaError
from workflow.schema import validate_instance, validate_schema


class SchemaTests(unittest.TestCase):
    def test_hello_schema_accepts_name(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        validate_schema(schema)
        validate_instance({"name": "codex-workflow"}, schema)

    def test_rejects_extra_property(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        with self.assertRaises(SchemaError):
            validate_instance({"name": "x", "extra": 1}, schema)

    def test_rejects_unknown_schema_key(self) -> None:
        with self.assertRaises(SchemaError):
            validate_schema({"type": "object", "$ref": "#/defs/x"})


if __name__ == "__main__":
    unittest.main()
