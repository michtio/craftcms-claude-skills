#!/usr/bin/env python3
"""Fail when a pack file names a model or vendor as a builder.

Usage: python3 bin/neutral_check.py <path>...

Each path is a file or a directory (recursed; .md .json .txt .yml .yaml .tsv).
Deny list: bin/data/builder-names.txt (one term per line, whole word, case
insensitive). Allowlist: bin/data/builder-names-allow.tsv (phrase TAB reason;
a line containing the phrase is exempt). Exit 1 with path:line messages on a
hit, 0 when clean, 2 on a usage error. Standard library only.
"""

import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
EXTS = {".md", ".json", ".txt", ".yml", ".yaml", ".tsv"}


def data_lines(path):
    for raw in path.read_text().splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            yield raw


def files(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*") if f.is_file() and f.suffix in EXTS)
        elif p.is_file():
            yield p
        else:
            print(f"{p}: no such file or directory", file=sys.stderr)
            sys.exit(2)


def main(argv):
    if len(argv) < 2:
        print("usage: neutral_check.py <path>...", file=sys.stderr)
        return 2
    terms = [l.strip() for l in data_lines(DATA / "builder-names.txt")]
    rx = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.I)
    allow = []
    for l in data_lines(DATA / "builder-names-allow.tsv"):
        parts = l.split("\t")
        if len(parts) != 2 or not parts[1].strip():
            print(f"allowlist entry without a reason: {l}", file=sys.stderr)
            return 2
        allow.append(parts[0].lower())
    hits = 0
    for f in files(argv[1:]):
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            m = rx.search(line)
            if m and not any(a in line.lower() for a in allow):
                print(f"{f}:{n}: names '{m.group(1)}' (builder names are never hardcoded)")
                hits = 1
    return hits


if __name__ == "__main__":
    sys.exit(main(sys.argv))
