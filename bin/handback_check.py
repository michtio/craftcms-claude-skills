#!/usr/bin/env python3
"""Check that a builder hand-back has every required line.

Usage: python3 bin/handback_check.py --brief <brief> <handback>

Exit 0: well formed. Exit 1: a required line is missing or bad (one message
per problem). Exit 2: usage error, unreadable file, or a brief with no R ids.
Validates form only: a FAIL or PENDING status is well formed. Whether the
slice passed is the caller's decision. Standard library only.
"""

import re
import sys

USAGE = "usage: handback_check.py --brief <brief> <handback>"
FLOW = re.compile(r"^Gate flow: (?:locked \(([0-9a-fA-F]{7,40})\)|builder-written \((\S.*)\))$")
STATUSES = ("PASS", "FAIL", "PENDING")


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as err:
        print(f"cannot read {path}: {err}", file=sys.stderr)
        sys.exit(2)


def main(argv):
    args = argv[1:]
    if len(args) != 3 or args[0] != "--brief":
        print(USAGE, file=sys.stderr)
        return 2
    brief, handback = read(args[1]), read(args[2])
    ids = []
    for m in re.finditer(r"(?m)^#{2,4}\s+R(\d+)\b", brief):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    if not ids:
        print(f"{args[1]}: no R ids (## R<n> headings) in the brief", file=sys.stderr)
        return 2

    lines = handback.splitlines()
    problems = []

    flow = [m for m in (FLOW.match(l) for l in lines) if m]
    if not flow:
        bad = [l for l in lines if l.startswith("Gate flow:")]
        problems.append("bad line: Gate flow" if bad else "missing line: Gate flow")
    locked = bool(flow) and flow[0].group(1) is not None

    if locked:
        for label, what in (("committed", "committed"), ("working tree", "working tree")):
            pat = re.compile(r"^Lock check \(%s\): exit (\d+)$" % re.escape(label))
            hits = [pat.match(l) for l in lines if pat.match(l)]
            if not hits:
                problems.append(f"missing line: Lock check ({label})")
            elif hits[0].group(1) != "0":
                problems.append(
                    f"gate touched: Lock check ({what}) exit {hits[0].group(1)}")

    for n in ids:
        pat = re.compile(r"^R%s: (\S+)$" % n)
        hits = [pat.match(l) for l in lines if pat.match(l)]
        if not hits:
            problems.append(f"missing line: R{n}")
        elif hits[0].group(1) not in STATUSES:
            problems.append(f"bad status: R{n}: {hits[0].group(1)}")

    if not any(re.match(r"^Builder: \S.*$", l) for l in lines):
        problems.append("missing line: Builder")

    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
