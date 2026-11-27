#!/usr/bin/env python3
"""Fail when a pack file names a model or vendor as a builder.

Usage: python3 bin/neutral_check.py [--allow <file>] <path>...

Each path is a file or a directory (recursed, every file; files with a NUL
byte or that fail to decode as UTF-8 are skipped). Deny list:
bin/data/builder-names.txt (one term per line, case insensitive, letter-only
boundaries: Qwen3 and gpt_4 hit, Ruglmore does not). Allowlist:
bin/data/builder-names-allow.tsv or the --allow file (phrase TAB reason). An
allowed phrase is removed from the line before the deny terms are matched, so
it exempts only itself. Exit 1 with path:line messages on a
hit, 0 when clean, 2 on a usage error. Standard library only.
"""

import re
import sys
from pathlib import Path

USAGE = "usage: neutral_check.py [--allow <file>] <path>..."
DATA = Path(__file__).resolve().parent / "data"


def data_lines(path):
    for raw in path.read_text().splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            yield raw


def read_text(path):
    """Return the file's text, or None for a binary or undecodable file."""
    raw = path.read_bytes()
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def files(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*") if f.is_file())
        elif p.is_file():
            yield p
        else:
            print(f"{p}: no such file or directory", file=sys.stderr)
            sys.exit(2)


def main(argv):
    args = argv[1:]
    allow_file = DATA / "builder-names-allow.tsv"
    if args[:1] == ["--allow"]:
        if len(args) < 2:
            print(USAGE, file=sys.stderr)
            return 2
        allow_file = Path(args[1])
        args = args[2:]
    if not args:
        print(USAGE, file=sys.stderr)
        return 2
    terms = [l.strip() for l in data_lines(DATA / "builder-names.txt")]
    rx = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in terms) + r")(?![A-Za-z])", re.I)
    allow = []
    for l in data_lines(allow_file):
        parts = l.split("\t")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            print(f"{allow_file}: allowlist entry needs a phrase and a reason: {l!r}", file=sys.stderr)
            return 2
        allow.append(re.compile(re.escape(parts[0].strip()), re.I))
    hits = 0
    for f in files(args):
        text = read_text(f)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for a in allow:
                line = a.sub(" ", line)
            m = rx.search(line)
            if m:
                print(f"{f}:{n}: names '{m.group(1)}' (builder names are never hardcoded)")
                hits = 1
    return hits


if __name__ == "__main__":
    sys.exit(main(sys.argv))
