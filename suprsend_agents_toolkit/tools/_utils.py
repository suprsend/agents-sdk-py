import json
from typing import Union


def evaluate_jsonnet(value: Union[str, dict]) -> dict:
    """
    If value is a Jsonnet string, evaluate it and return the resulting dict.
    If value is already a dict, return it unchanged.
    Raises ValueError with a clear message on Jsonnet syntax errors.
    """
    if isinstance(value, dict):
        return value
    try:
        import _gojsonnet as jsonnet  # jsonnet package exposes _gojsonnet
    except ImportError:
        raise ImportError("Install 'jsonnet' to use Jsonnet template support.")

    def _block_import(base: str, rel: str) -> tuple[str, str]:
        raise RuntimeError(
            f"Jsonnet import not permitted: '{rel}'. "
            "File system and network imports are disabled for security."
        )

    try:
        evaluated = jsonnet.evaluate_snippet("payload", value, import_callback=_block_import)
    except Exception as e:
        raise ValueError(f"Jsonnet evaluation error: {e}")
    return json.loads(evaluated)


_MISSING = object()  # sentinel for missing values


def validate_with_jsonpath(data: dict, schema: dict) -> str | None:
    """
    Validate data against schema with JSONPath-aware field navigation.

    Schema shapes supported:
    - Flat:        { field_name: { type, required, description } }
    - JSON Schema: { properties: { field_name: { type, required } } }
    - JSONPath:    field names starting with "$." are resolved via jsonpath-ng
                   e.g. "$.user.email" extracts data["user"]["email"] for validation

    Returns None if valid, or a descriptive error string.
    """
    from jsonpath_ng import parse as jp_parse

    fields = schema.get("properties") or schema
    missing, wrong_type = [], []

    type_map = {
        "string": str, "str": str,
        "integer": int, "int": int,
        "number": (int, float), "float": float,
        "boolean": bool, "bool": bool,
        "array": list, "list": list,
        "object": dict, "dict": dict,
    }

    for field_name, field_def in fields.items():
        if not isinstance(field_def, dict):
            continue
        required = field_def.get("required", False)
        expected_type = field_def.get("type", "")

        # Resolve value — plain key or JSONPath expression
        if field_name.startswith("$."):
            matches = jp_parse(field_name).find(data)
            value = matches[0].value if matches else _MISSING
        else:
            value = data.get(field_name, _MISSING)

        if required and value is _MISSING:
            missing.append(field_name)
            continue
        if expected_type and value is not _MISSING:
            expected_py = type_map.get(expected_type.lower())
            if expected_py and not isinstance(value, expected_py):
                wrong_type.append(
                    f"  {field_name}: expected {expected_type}, got {type(value).__name__}"
                )

    errors = []
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if wrong_type:
        errors.append("Type mismatches:\n" + "\n".join(wrong_type))
    return "\n".join(errors) if errors else None