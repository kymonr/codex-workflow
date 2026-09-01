from __future__ import annotations

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


def validate_schema(schema: object, *, path: str = "$") -> None:
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: schema must be an object")
    unknown = set(schema) - _ALLOWED_KEYS
    if unknown:
        raise SchemaError(f"{path}: unsupported schema keys: {', '.join(sorted(unknown))}")
    type_name = schema.get("type")
    if type_name not in _ALLOWED_TYPES:
        raise SchemaError(f"{path}: type must be one of {sorted(_ALLOWED_TYPES)}")
    if "properties" in schema:
        props = schema["properties"]
        if not isinstance(props, dict):
            raise SchemaError(f"{path}.properties must be an object")
        for key, sub in props.items():
            if not isinstance(key, str) or not key:
                raise SchemaError(f"{path}.properties keys must be non-empty strings")
            validate_schema(sub, path=f"{path}.properties.{key}")
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or any(not isinstance(item, str) or not item for item in required):
            raise SchemaError(f"{path}.required must be an array of non-empty strings")
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        raise SchemaError(f"{path}.additionalProperties must be a boolean in PR1")
    if "items" in schema:
        validate_schema(schema["items"], path=f"{path}.items")
    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or not enum:
            raise SchemaError(f"{path}.enum must be a non-empty array")


def validate_instance(instance: object, schema: dict, *, path: str = "$") -> None:
    validate_schema(schema, path=path)
    type_name = schema["type"]
    if type_name == "object":
        if not isinstance(instance, dict):
            raise SchemaError(f"{path}: expected object")
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        additional = schema.get("additionalProperties", True)
        for key in required:
            if key not in instance:
                raise SchemaError(f"{path}: missing required property {key}")
        for key, value in instance.items():
            if key in props:
                validate_instance(value, props[key], path=f"{path}.{key}")
            elif additional is False:
                raise SchemaError(f"{path}: additional property not allowed: {key}")
        return
    if type_name == "string":
        if not isinstance(instance, str):
            raise SchemaError(f"{path}: expected string")
        _check_bounds(schema, instance, path, length=len(instance))
        _check_enum(schema, instance, path)
        return
    if type_name == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            raise SchemaError(f"{path}: expected integer")
        _check_numeric(schema, instance, path)
        _check_enum(schema, instance, path)
        return
    if type_name == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            raise SchemaError(f"{path}: expected number")
        _check_numeric(schema, instance, path)
        _check_enum(schema, instance, path)
        return
    if type_name == "boolean":
        if not isinstance(instance, bool):
            raise SchemaError(f"{path}: expected boolean")
        _check_enum(schema, instance, path)
        return
    if type_name == "array":
        if not isinstance(instance, list):
            raise SchemaError(f"{path}: expected array")
        _check_bounds(schema, instance, path, length=len(instance), items=True)
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(instance):
                validate_instance(item, item_schema, path=f"{path}[{index}]")
        return
    if instance is not None:
        raise SchemaError(f"{path}: expected null")


def _check_enum(schema: dict, instance: object, path: str) -> None:
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(f"{path}: value not in enum")


def _check_numeric(schema: dict, instance: int | float, path: str) -> None:
    if "minimum" in schema and instance < schema["minimum"]:
        raise SchemaError(f"{path}: below minimum")
    if "maximum" in schema and instance > schema["maximum"]:
        raise SchemaError(f"{path}: above maximum")


def _check_bounds(
    schema: dict,
    instance: object,
    path: str,
    *,
    length: int,
    items: bool = False,
) -> None:
    if items:
        if "minItems" in schema and length < schema["minItems"]:
            raise SchemaError(f"{path}: below minItems")
        if "maxItems" in schema and length > schema["maxItems"]:
            raise SchemaError(f"{path}: above maxItems")
        return
    if "minLength" in schema and length < schema["minLength"]:
        raise SchemaError(f"{path}: below minLength")
    if "maxLength" in schema and length > schema["maxLength"]:
        raise SchemaError(f"{path}: above maxLength")
