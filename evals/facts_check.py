#!/usr/bin/env python3
"""Deterministic fact assertions for the behaviour eval cases. No model calls.

Each case in evals/behavior-sets/*.json carries a "facts" list naming the text
its answer depends on:

  "facts": [{"file": "skills/craft-mcp/SKILL.md",
             "contains": ["regex", ...],        # each must match somewhere
             "not_contains": ["regex", ...]}]   # none may match

Patterns are Python regexes, matched with re.MULTILINE against the whole file.
A case without "facts" fails: every behaviour case must pin the facts it tests,
so an edit that drops or contradicts them fails CI before any model run.

Usage:
    python3 evals/facts_check.py                       # every set
    python3 evals/facts_check.py evals/behavior-sets/craft-5.12.json
    python3 evals/facts_check.py --root /tmp/copy      # resolve "file" under another tree

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def check_case(case: dict, root: Path) -> list[str]:
    cid = case.get("id", "?")
    facts = case.get("facts")
    if not facts:
        return [f"{cid}: no facts (every behaviour case must pin the text its answer depends on)"]
    errors = []
    for fact in facts:
        path = root / fact["file"]
        if not path.is_file():
            errors.append(f"{cid}: {fact['file']} does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        for pat in fact.get("contains", []):
            if not re.search(pat, text, re.M):
                errors.append(f"{cid}: {fact['file']} no longer contains /{pat}/")
        for pat in fact.get("not_contains", []):
            m = re.search(pat, text, re.M)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                errors.append(f"{cid}: {fact['file']}:{line} contains forbidden /{pat}/")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sets", nargs="*", help="behaviour-set JSON files (default: evals/behavior-sets/*.json)")
    ap.add_argument("--root", help="tree to resolve fact files against (default: this repo)")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else REPO
    sets = [Path(s) for s in args.sets] or sorted((REPO / "evals" / "behavior-sets").glob("*.json"))

    errors, cases = [], 0
    for s in sets:
        for case in json.loads(s.read_text(encoding="utf-8")):
            cases += 1
            errors += check_case(case, root)
    for e in errors:
        print(e)
    print(f"{len(errors)} fact failure(s) across {cases} case(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
