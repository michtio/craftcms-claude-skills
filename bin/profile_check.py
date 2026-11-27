#!/usr/bin/env python3
"""Validate skills profile files against schema/skills-profile.schema.json.

Usage: python3 bin/profile_check.py [--schema <file>] <file>...

Exit 0 when every file is valid, 1 when one is invalid (messages name the
key), 2 on a usage error or a schema that uses an unsupported keyword. Standard library only. Implements the subset of JSON
Schema 2020-12 the schema uses: type, const, enum, required, properties,
items, exclusiveMinimum. Unknown keys are never rejected.
"""

import json
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "skills-profile.schema.json"
USAGE = "usage: profile_check.py [--schema <file>] <file>..."
ANNOTATIONS = {"$schema", "$id", "title", "description"}
SUPPORTED = {"type", "const", "enum", "required", "properties", "items", "exclusiveMinimum"}
TYPES = {"object", "array", "string", "boolean", "integer", "number", "null"}


class SchemaError(Exception):
    """The schema uses something this checker does not support."""


def vet(schema, path="schema"):
    """Raise SchemaError naming any unsupported keyword or malformed type."""
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: a schema must be an object")
    for kw, val in schema.items():
        if kw in ANNOTATIONS:
            continue
        if kw not in SUPPORTED:
            raise SchemaError(f"{path}: unsupported keyword '{kw}'")
        if kw == "type":
            names = val if isinstance(val, list) else [val]
            for n in names:
                if n not in TYPES:
                    raise SchemaError(f"{path}: unsupported type {n!r}")
        elif kw == "properties":
            if not isinstance(val, dict):
                raise SchemaError(f"{path}.properties: must be an object")
            for k, sub in val.items():
                vet(sub, f"{path}.properties.{k}")
        elif kw == "items":
            vet(val, f"{path}.items")
        elif kw == "required" and not isinstance(val, list):
            raise SchemaError(f"{path}.required: must be a list")
        elif kw == "enum" and not isinstance(val, list):
            raise SchemaError(f"{path}.enum: must be a list")


def type_ok(value, name):
    if isinstance(name, list):
        return any(type_ok(value, n) for n in name)
    if name == "null":
        return value is None
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
        errors.append(f"{where}: must be of type {t if isinstance(t, str) else ' or '.join(t)}")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: must be one of {', '.join(map(str, schema['enum']))}")
    if "exclusiveMinimum" in schema and type_ok(value, "number") \
            and value <= schema["exclusiveMinimum"]:
        errors.append(f"{where}: must be greater than {schema['exclusiveMinimum']}")
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        errors.append(f"{where}: NaN and Infinity are not valid")
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
    args = argv[1:]
    schema_path = SCHEMA
    if args[:1] == ["--schema"]:
        if len(args) < 2:
            print(USAGE, file=sys.stderr)
            return 2
        schema_path = Path(args[1])
        args = args[2:]
    if not args or args[0].startswith("--"):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        schema = json.loads(schema_path.read_text())
        vet(schema)
    except (OSError, ValueError) as e:
        print(f"cannot read schema {schema_path}: {e}", file=sys.stderr)
        return 2
    except SchemaError as e:
        print(f"{schema_path}: {e}", file=sys.stderr)
        return 2
    bad = 0
    for f in args:
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
