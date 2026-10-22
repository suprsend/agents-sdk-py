import asyncio
import json
from typing import Union

_JSONNET_TIMEOUT = 10  # seconds


def _jsonnet_module():
    """The `jsonnet` extra installs _jsonnet (C++); the `gojsonnet` package installs _gojsonnet."""
    try:
        import _jsonnet as jsonnet
    except ImportError:
        try:
            import _gojsonnet as jsonnet
        except ImportError:
            raise ImportError("Install 'jsonnet' to use Jsonnet template support.")
    return jsonnet


def evaluate_jsonnet(value: Union[str, dict]) -> dict:
    """
    If value is a Jsonnet string, evaluate it and return the resulting dict.
    If value is already a dict, return it unchanged.
    Raises ValueError with a clear message on Jsonnet syntax errors.
    Async callers should use evaluate_jsonnet_async instead.
    """
    if isinstance(value, dict):
        return value
    jsonnet = _jsonnet_module()

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


async def evaluate_jsonnet_async(value: Union[str, dict]) -> dict:
    """
    evaluate_jsonnet off the event loop, with a time limit.

    Jsonnet comes from the LLM and can be arbitrarily expensive. The C extension
    releases the GIL, so other tool calls keep running meanwhile. On timeout the
    worker thread still runs to completion in the background.
    Raises ImportError / ValueError like evaluate_jsonnet.
    """
    if isinstance(value, dict):
        return value
    try:
        return await asyncio.wait_for(asyncio.to_thread(evaluate_jsonnet, value), timeout=_JSONNET_TIMEOUT)
    except TimeoutError:
        raise ValueError(f"Jsonnet evaluation timed out after {_JSONNET_TIMEOUT}s.")


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