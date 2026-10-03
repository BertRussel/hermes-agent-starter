#!/usr/bin/env python3
"""Validate non-secret onboarding data; never render or install instructions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = Path(__file__).resolve().parents[1] / "templates/customization.schema.json"


def validate_customization(values: dict) -> dict:
    """Return validated data with closed defaults, without changing the input."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if not isinstance(values, dict) or set(values) - set(schema["properties"]):
        raise ValueError("unexpected customization fields")
    if set(schema["required"]) - set(values):
        raise ValueError("missing required customization fields")
    result = dict(values)
    for name, rules in schema["properties"].items():
        if name not in result and "default" in rules:
            result[name] = rules["default"]
        value = result.get(name)
        if not isinstance(value, str):
            raise ValueError(f"{name}: expected string")
        if not rules.get("minLength", 0) <= len(value) <= rules["maxLength"]:
            raise ValueError(f"{name}: invalid length")
        if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError(f"{name}: whitespace/control character")
        if any(token in value for token in ("{{", "}}", "${", "<%", "%>", "```")):
            raise ValueError(f"{name}: template delimiter")
        if "enum" in rules and value not in rules["enum"]:
            raise ValueError(f"{name}: unsupported selection")
        if "pattern" in rules and re.fullmatch(rules["pattern"], value) is None:
            raise ValueError(f"{name}: invalid format")
    try:
        ZoneInfo(result["TIMEZONE"])
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("TIMEZONE: unknown identifier") from error
    root = Path(result["KNOWLEDGE_ROOT"])
    if not root.is_absolute() or ".." in root.parts or "//" in str(result["KNOWLEDGE_ROOT"]):
        raise ValueError("KNOWLEDGE_ROOT: expected absolute non-traversing path")
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError("KNOWLEDGE_ROOT: symlink traversal")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="private non-secret JSON form; never an auth file")
    args = parser.parse_args()
    try:
        validate_customization(json.loads(args.input.read_text(encoding="utf-8")))
    except (ValueError, OSError) as error:
        print(json.dumps({"status": "rejected", "error": str(error)}))
        return 1
    # Deliberately do not echo private identity fields into terminal logs.
    print(json.dumps({"status": "validated", "authority_policy": "local-only", "installed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
