from __future__ import annotations

import json
import re
from pathlib import Path

_SPEC_PATH = Path(__file__).parent.parent.parent / "openapi.json"
_spec_cache: dict | None = None


def _load_spec() -> dict | None:
    global _spec_cache
    if _spec_cache is not None:
        return _spec_cache
    if _SPEC_PATH.exists():
        try:
            _spec_cache = json.loads(_SPEC_PATH.read_text())
        except Exception:
            pass
    return _spec_cache


def _match_template(concrete: str, template: str) -> bool:
    pattern = re.sub(r"\{[^}]+\}", "[^/]+", re.escape(template))
    return bool(re.fullmatch(pattern, concrete))


def validate_request_body(method: str, path: str, body: object) -> None:
    spec = _load_spec()
    if not spec:
        return
    try:
        import jsonschema
    except ImportError:
        return

    paths = spec.get("paths", {})
    schema = None
    for template, path_item in paths.items():
        if _match_template(path, template):
            op = path_item.get(method.lower(), {})
            rb = op.get("requestBody", {})
            content = rb.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema")
            break

    if schema is None:
        return

    components = spec.get("components", {})

    def resolve_ref(s: dict) -> dict:
        ref = s.get("$ref", "")
        if not ref.startswith("#/"):
            return s
        parts = ref.lstrip("#/").split("/")
        node = spec
        for p in parts:
            node = node.get(p, {})
        return node

    try:
        resolved = resolve_ref(schema)
        jsonschema.validate(body, resolved)
    except jsonschema.ValidationError as exc:
        from netcup_cli.errors import CLIError
        field = ".".join(str(p) for p in exc.absolute_path) or "(root)"
        raise CLIError(f"Invalid request body at '{field}': {exc.message}")
