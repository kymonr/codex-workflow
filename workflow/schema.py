from __future__ import annotations

import math
from typing import Any

from workflow.errors import SchemaError

_ALLOWED_KEYS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
    "description",
    "title",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
}

_ALLOWED_TYPES = {
    "object",
    "string",
    "number",
    "integer",
    "boolean",
    "array",
    "null",
}

_OBJECT_KEYS = {"properties", "required", "additionalProperties"}
_ARRAY_KEYS = {"items", "minItems", "maxItems"}
_STRING_KEYS = {"minLength", "maxLength"}
_NUMERIC_KEYS = {"minimum", "maximum"}
_MAX_SCHEMA_DEPTH = 64


def validate_schema(schema: object, *, path: str = "$") -> None:
    _validate_schema(schema, path=path, depth=0, active=set())


def _validate_schema(
    schema: object,
    *,
    path: str,
    depth: int,
    active: set[int],
) -> None:
    if depth > _MAX_SCHEMA_DEPTH:
        raise SchemaError(f"{path}: schema nesting exceeds {_MAX_SCHEMA_DEPTH}")
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: schema must be an object")

    schema_id = id(schema)
    if schema_id in active:
        raise SchemaError(f"{path}: cyclic schema is not supported")
    active.add(schema_id)
    try:
        unknown = set(schema) - _ALLOWED_KEYS
        if unknown:
            raise SchemaError(
                f"{path}: unsupported schema keys: {', '.join(sorted(unknown))}"
            )

        type_name = schema.get("type")
        if type_name not in _ALLOWED_TYPES:
            raise SchemaError(f"{path}: type must be one of {sorted(_ALLOWED_TYPES)}")

        for text_key in ("title", "description"):
            if text_key in schema and not isinstance(schema[text_key], str):
                raise SchemaError(f"{path}.{text_key} must be a string")

        _reject_inapplicable_keywords(schema, type_name, path)

        if type_name == "object":
            _validate_object_keywords(schema, path, depth, active)
        elif type_name == "array":
            _validate_array_keywords(schema, path, depth, active)
        elif type_name == "string":
            _validate_length_keywords(schema, path)
        elif type_name in {"number", "integer"}:
            _validate_numeric_keywords(schema, path)

        if "enum" in schema:
            enum = schema["enum"]
            if not isinstance(enum, list) or not enum:
                raise SchemaError(f"{path}.enum must be a non-empty array")
            for index, value in enumerate(enum):
                if not _matches_type(value, type_name):
                    raise SchemaError(
                        f"{path}.enum[{index}] does not match type {type_name}"
                    )
    finally:
        active.remove(schema_id)


def _reject_inapplicable_keywords(
    schema: dict[str, Any],
    type_name: str,
    path: str,
) -> None:
    groups = [
        (_OBJECT_KEYS, "object"),
        (_ARRAY_KEYS, "array"),
        (_STRING_KEYS, "string"),
        (_NUMERIC_KEYS, "number or integer"),
    ]
    for keys, expected in groups:
        present = keys.intersection(schema)
        if not present:
            continue
        valid = (
            type_name == expected
            if expected != "number or integer"
            else type_name in {"number", "integer"}
        )
        if not valid:
            names = ", ".join(sorted(present))
            raise SchemaError(
                f"{path}: {names} only valid for type {expected}"
            )


def _validate_object_keywords(
    schema: dict[str, Any],
    path: str,
    depth: int,
    active: set[int],
) -> None:
    if "properties" in schema:
        props = schema["properties"]
        if not isinstance(props, dict):
            raise SchemaError(f"{path}.properties must be an object")
        for key, sub in props.items():
            if not isinstance(key, str) or not key:
                raise SchemaError(
                    f"{path}.properties keys must be non-empty strings"
                )
            _validate_schema(
                sub,
                path=f"{path}.properties.{key}",
                depth=depth + 1,
                active=active,
            )

    if "required" in schema:
        required = schema["required"]
        if (
            not isinstance(required, list)
            or any(not isinstance(item, str) or not item for item in required)
        ):
            raise SchemaError(
                f"{path}.required must be an array of non-empty strings"
            )
        if len(set(required)) != len(required):
            raise SchemaError(f"{path}.required must not contain duplicates")

    if (
        "additionalProperties" in schema
        and not isinstance(schema["additionalProperties"], bool)
    ):
        raise SchemaError(f"{path}.additionalProperties must be a boolean")


def _validate_array_keywords(
    schema: dict[str, Any],
    path: str,
    depth: int,
    active: set[int],
) -> None:
    if "items" in schema:
        _validate_schema(
            schema["items"],
            path=f"{path}.items",
            depth=depth + 1,
            active=active,
        )
    _validate_non_negative_bounds(
        schema,
        path,
        lower_key="minItems",
        upper_key="maxItems",
    )


def _validate_length_keywords(schema: dict[str, Any], path: str) -> None:
    _validate_non_negative_bounds(
        schema,
        path,
        lower_key="minLength",
        upper_key="maxLength",
    )


def _validate_non_negative_bounds(
    schema: dict[str, Any],
    path: str,
    *,
    lower_key: str,
    upper_key: str,
) -> None:
    for key in (lower_key, upper_key):
        if key in schema:
            value = schema[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise SchemaError(f"{path}.{key} must be a non-negative integer")
    if (
        lower_key in schema
        and upper_key in schema
        and schema[lower_key] > schema[upper_key]
    ):
        raise SchemaError(f"{path}: {lower_key} must not exceed {upper_key}")


def _validate_numeric_keywords(schema: dict[str, Any], path: str) -> None:
    for key in ("minimum", "maximum"):
        if key in schema:
            value = schema[key]
            if not _is_finite_number(value):
                raise SchemaError(f"{path}.{key} must be a finite number")
    if (
        "minimum" in schema
        and "maximum" in schema
        and schema["minimum"] > schema["maximum"]
    ):
        raise SchemaError(f"{path}: minimum must not exceed maximum")


def validate_instance(instance: object, schema: dict, *, path: str = "$") -> None:
    validate_schema(schema, path=path)
    _validate_instance(instance, schema, path=path)


def _validate_instance(instance: object, schema: dict, *, path: str) -> None:
    type_name = schema["type"]

    if not _matches_type(instance, type_name):
        raise SchemaError(f"{path}: expected {type_name}")

    if type_name == "object":
        assert isinstance(instance, dict)
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        additional = schema.get("additionalProperties", True)
        for key in required:
            if key not in instance:
                raise SchemaError(f"{path}: missing required property {key}")
        for key, value in instance.items():
            if key in props:
                _validate_instance(value, props[key], path=f"{path}.{key}")
            elif additional is False:
                raise SchemaError(
                    f"{path}: additional property not allowed: {key}"
                )
    elif type_name == "string":
        assert isinstance(instance, str)
        _check_length_bounds(schema, len(instance), path)
    elif type_name in {"integer", "number"}:
        assert isinstance(instance, (int, float)) and not isinstance(instance, bool)
        _check_numeric_bounds(schema, instance, path)
    elif type_name == "array":
        assert isinstance(instance, list)
        _check_item_bounds(schema, len(instance), path)
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(instance):
                _validate_instance(item, item_schema, path=f"{path}[{index}]")

    _check_enum(schema, instance, path)


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value)


def _matches_type(value: object, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return _is_finite_number(value)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "array":
        return isinstance(value, list)
    return value is None


def _check_enum(schema: dict, instance: object, path: str) -> None:
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(f"{path}: value not in enum")


def _check_numeric_bounds(
    schema: dict,
    instance: int | float,
    path: str,
) -> None:
    if not _is_finite_number(instance):
        raise SchemaError(f"{path}: expected finite number")
    if "minimum" in schema and instance < schema["minimum"]:
        raise SchemaError(f"{path}: below minimum")
    if "maximum" in schema and instance > schema["maximum"]:
        raise SchemaError(f"{path}: above maximum")


def _check_length_bounds(schema: dict, length: int, path: str) -> None:
    if "minLength" in schema and length < schema["minLength"]:
        raise SchemaError(f"{path}: below minLength")
    if "maxLength" in schema and length > schema["maxLength"]:
        raise SchemaError(f"{path}: above maxLength")


def _check_item_bounds(schema: dict, length: int, path: str) -> None:
    if "minItems" in schema and length < schema["minItems"]:
        raise SchemaError(f"{path}: below minItems")
    if "maxItems" in schema and length > schema["maxItems"]:
        raise SchemaError(f"{path}: above maxItems")
