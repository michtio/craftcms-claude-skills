#!/usr/bin/env python3
"""Validate skills profile files against schema/skills-profile.schema.json.

Usage: python3 bin/profile_check.py <file>...

Exit 0 when every file is valid, 1 when one is invalid (messages name the
key), 2 on a usage error. Standard library only. Implements the subset of JSON
Schema 2020-12 the schema uses: type, const, enum, required, properties,
items, exclusiveMinimum. Unknown keys are never rejected.
"""

import json
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "skills-profile.schema.json"


def type_ok(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def check(value, schema, path, errors):
    """Append a message naming `path` for every rule the value breaks."""
    where = path or "(root)"
    t = schema.get("type")
    if t and not type_ok(value, t):
        errors.append(f"{where}: must be of type {t}")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: must be one of {', '.join(map(str, schema['enum']))}")
    if "exclusiveMinimum" in schema and type_ok(value, "number") \
            and value <= schema["exclusiveMinimum"]:
        errors.append(f"{where}: must be greater than {schema['exclusiveMinimum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path + '.' if path else ''}{key}: required key is missing")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                check(value[key], sub, f"{path + '.' if path else ''}{key}", errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            check(item, schema["items"], f"{path}[{i}]", errors)


def main(argv):
    files = argv[1:]
    if not files:
        print(__doc__.split("\n\n")[1].strip(), file=sys.stderr)
        return 2
    try:
        schema = json.loads(SCHEMA.read_text())
    except (OSError, ValueError) as e:
        print(f"cannot read schema {SCHEMA}: {e}", file=sys.stderr)
        return 2
    bad = 0
    for f in files:
        try:
            data = json.loads(Path(f).read_text())
        except OSError as e:
            print(f"{f}: cannot read: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"{f}: invalid JSON: {e}")
            bad = 1
            continue
        errors = []
        check(data, schema, "", errors)
        for e in errors:
            print(f"{f}: {e}")
        if errors:
            bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
