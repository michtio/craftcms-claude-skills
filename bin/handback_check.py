#!/usr/bin/env python3
"""Check that a builder hand-back has every required line.

Usage: python3 bin/handback_check.py --brief <brief> <handback>

Exit 0: well formed. Exit 1: a required line is missing, bad, duplicated or
unknown (one message per problem). Exit 2: usage error, unreadable file, or a
brief with no R ids. Validates form only: a FAIL or PENDING status is well
formed. Whether the slice passed is the caller's decision.

Rules: lines inside ``` or ~~~ fences are ignored (hand-back and brief); R ids
come from level-2 "## R<n>" headings, optionally followed by a title after a
colon or dash; the brief's "Gate commit:" line binds the Gate flow line; files
are read as UTF-8 and a BOM is tolerated. Standard library only.
"""

import re
import sys

USAGE = "usage: handback_check.py --brief <brief> <handback>"
FLOW = re.compile(r"^Gate flow: (?:locked \(([0-9a-fA-F]{7,40})\)|builder-written \((\S.*)\))$")
HEADING = re.compile(r"^## +R(\d+)(?:[ \t]*[:\-–—][ \t]*\S.*|[ \t]*)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
STATUSES = ("PASS", "FAIL", "PENDING")


def read(path):
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as err:
        print(f"cannot read {path}: {err}", file=sys.stderr)
        sys.exit(2)


def visible_lines(text):
    """Split on real newlines only and drop fenced lines."""
    out, fence = [], None
    for line in re.split(r"\r\n|\n|\r", text):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            out.append(line)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and not line.strip(" `~"):
            fence = None
    return out


def gate_commit(brief_lines):
    """Return a sha string, 'none', or None when the brief binds nothing."""
    for line in brief_lines:
        m = re.match(r"^Gate commit:[ \t]*(\S+)", line)
        if m:
            v = m.group(1).strip("`")
            if v.lower() == "none":
                return "none"
            if re.fullmatch(r"[0-9a-fA-F]{7,40}", v):
                return v.lower()
            return None
    return None


def main(argv):
    args = argv[1:]
    if len(args) != 3 or args[0] != "--brief":
        print(USAGE, file=sys.stderr)
        return 2
    brief = visible_lines(read(args[1]))
    lines = visible_lines(read(args[2]))
    ids = []
    for line in brief:
        m = HEADING.match(line)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    if not ids:
        print(f"{args[1]}: no R ids (## R<n> headings) in the brief", file=sys.stderr)
        return 2
    bound = gate_commit(brief)
    problems = []

    # Gate flow
    flow_lines = [l for l in lines if l.startswith("Gate flow:")]
    if not flow_lines:
        problems.append("missing line: Gate flow")
    else:
        if len(flow_lines) > 1:
            problems.append("duplicate line: Gate flow")
        m = FLOW.match(flow_lines[0])
        if not m:
            problems.append("bad line: Gate flow")
        elif bound == "none" and m.group(1) is not None:
            problems.append("bad line: Gate flow (the brief has no gate commit, so the flow must be builder-written)")
        elif bound not in (None, "none"):
            sha = (m.group(1) or "").lower()
            if not sha or not (sha.startswith(bound) or bound.startswith(sha)):
                problems.append(f"bad line: Gate flow (must be locked ({bound}) as in the brief)")
    locked = bool(flow_lines) and bool(FLOW.match(flow_lines[0])) \
        and FLOW.match(flow_lines[0]).group(1) is not None

    # Lock checks
    if locked:
        for label in ("committed", "working tree"):
            pat = re.compile(r"^Lock check \(%s\): exit (\d+)$" % re.escape(label))
            hits = [pat.match(l) for l in lines if pat.match(l)]
            if not hits:
                problems.append(f"missing line: Lock check ({label})")
                continue
            if len(hits) > 1:
                problems.append(f"duplicate line: Lock check ({label})")
            if any(h.group(1) != "0" for h in hits):
                code = next(h.group(1) for h in hits if h.group(1) != "0")
                problems.append(f"gate touched: Lock check ({label}) exit {code}")

    # R lines
    for n in ids:
        pat = re.compile(r"^R%s: (\S+)$" % n)
        hits = [pat.match(l) for l in lines if pat.match(l)]
        if not hits:
            problems.append(f"missing line: R{n}")
            continue
        if len(hits) > 1:
            problems.append(f"duplicate line: R{n}")
        for h in hits:
            if h.group(1) not in STATUSES:
                problems.append(f"bad status: R{n}: {h.group(1)}")
                break
    seen = set()
    for l in lines:
        m = re.match(r"^R(\d+): ", l)
        if m and m.group(1) not in ids and m.group(1) not in seen:
            seen.add(m.group(1))
            problems.append(f"unknown line: R{m.group(1)}")

    # Builder
    builders = [l for l in lines if re.match(r"^Builder: \S.*$", l)]
    if not builders:
        problems.append("missing line: Builder")
    elif len(builders) > 1:
        problems.append("duplicate line: Builder")

    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
