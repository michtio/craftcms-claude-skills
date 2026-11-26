#!/usr/bin/env python3
"""Lexical routing check: BM25 of every trigger-set query against every skill listing.

No model calls. A model routes on far more than shared words, so this is a proxy,
but it is a stable one: a listing edit that drops the words a query needs, or one
that floods a listing with another skill's vocabulary, shows up here first.

Listing = description + " - " + when_to_use from each skills/*/SKILL.md, the text
Claude Code puts in the skill listing. Queries come from evals/trigger-sets/<skill>.json.

Checks against evals/routing-baseline.json:
  - positive (should_trigger: true): its own skill's rank must stay within
    max(baseline rank, TOP) where TOP = 3
  - negative (should_trigger: false): its skill must not newly rank #1

Usage:
    python3 evals/lexical_route.py              # check against the baseline
    python3 evals/lexical_route.py --baseline   # rewrite the baseline (review the diff)
    python3 evals/lexical_route.py --report     # per-skill recall@1 / @3, no check
    python3 evals/lexical_route.py --listings DIR   # read SKILL.md files from DIR/<skill>/ instead
    python3 evals/lexical_route.py --self-test  # must exit 1: proves the check bites

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = REPO / "evals" / "routing-baseline.json"
TOP = 3
K1, B = 1.2, 0.75

STOP = set("""a an and are as at be but by can do does for from how i if in into is it its my
not of on or our so that the their them then there these this to use used using via was we what
when where which while who why will with you your craft cms 5 don't do not""".split())


def tokens(text: str) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9][a-z0-9_.\-/]*[a-z0-9]|[a-z0-9]", text.lower()):
        parts = [t] + (re.split(r"[._\-/]", t) if re.search(r"[._\-/]", t) else [])
        for p in parts:
            if not p or p in STOP:
                continue
            if len(p) > 4 and p.endswith("s") and not p.endswith("ss"):
                p = p[:-1]
            out.append(p)
    return out


def frontmatter_value(text: str, key: str) -> str:
    m = re.search(rf'^{key}:\s*(.*)$', text, re.M)
    if not m:
        return ""
    raw = m.group(1).strip()
    if raw.startswith('"'):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip('"')
    return raw.strip("'")


def listings(root: Path) -> dict[str, str]:
    out = {}
    for md in sorted(root.glob("*/SKILL.md")):
        head = md.read_text(encoding="utf-8").split("\n---", 1)[0]
        desc, wtu = frontmatter_value(head, "description"), frontmatter_value(head, "when_to_use")
        out[md.parent.name] = desc + (" - " + wtu if wtu else "")
    return out


class BM25:
    def __init__(self, docs: dict[str, str]):
        self.names = list(docs)
        self.tf = {n: Counter(tokens(d)) for n, d in docs.items()}
        self.len = {n: sum(c.values()) for n, c in self.tf.items()}
        self.avg = sum(self.len.values()) / len(self.len)
        df = Counter(t for c in self.tf.values() for t in c)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def rank(self, query: str) -> list[tuple[str, float]]:
        q = set(tokens(query))
        scores = {}
        for name in self.names:
            tf, dl, s = self.tf[name], self.len[name], 0.0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avg))
            scores[name] = s
        return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def evaluate(root: Path, docs: dict[str, str] | None = None) -> dict:
    docs = docs if docs is not None else listings(root)
    bm = BM25(docs)
    result = {}
    for ts in sorted((REPO / "evals" / "trigger-sets").glob("*.json")):
        skill = ts.stem
        if skill not in docs:
            continue
        for case in json.loads(ts.read_text(encoding="utf-8")):
            ranked = [n for n, _ in bm.rank(case["query"])]
            result[f"{skill}\t{case['query']}"] = {
                "skill": skill,
                "positive": bool(case["should_trigger"]),
                "rank": ranked.index(skill) + 1,
                "top": ranked[0],
            }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", action="store_true", help="rewrite evals/routing-baseline.json")
    ap.add_argument("--report", action="store_true", help="print recall per skill, don't check")
    ap.add_argument("--listings", help="directory holding <skill>/SKILL.md (default: skills/)")
    ap.add_argument("--self-test", action="store_true",
                    help="flood the ddev listing with craftcms's text; the check must fail")
    args = ap.parse_args()
    root = Path(args.listings).resolve() if args.listings else REPO / "skills"
    docs = None
    if args.self_test:
        docs = listings(root)
        docs["ddev"] += " " + docs["craftcms"]
    now = evaluate(root, docs)

    per = {}
    for r in now.values():
        if r["positive"]:
            p = per.setdefault(r["skill"], [0, 0, 0])
            p[0] += 1
            p[1] += r["rank"] == 1
            p[2] += r["rank"] <= TOP
    pos = sum(p[0] for p in per.values())
    r1, r3 = sum(p[1] for p in per.values()), sum(p[2] for p in per.values())

    if args.report or args.baseline:
        for skill, (n, a, b) in sorted(per.items()):
            print(f"{skill:24} recall@1 {a:2}/{n:<2}  recall@{TOP} {b:2}/{n}")
    if args.baseline:
        BASELINE.write_text(json.dumps({k: {"rank": v["rank"], "top": v["top"]} for k, v in sorted(now.items())},
                                       indent=1, ensure_ascii=False) + "\n")
        print(f"baseline written: {len(now)} queries, recall@1 {r1}/{pos}, recall@{TOP} {r3}/{pos}")
        return 0
    if args.report:
        print(f"total recall@1 {r1}/{pos}, recall@{TOP} {r3}/{pos}")
        return 0

    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    failures = []
    for key, r in sorted(now.items()):
        b = base.get(key)
        skill, query = key.split("\t", 1)
        if r["positive"]:
            limit = max(b["rank"] if b else TOP, TOP)
            if r["rank"] > limit:
                failures.append(f"{skill}: positive ranks #{r['rank']} (allowed #{limit}, top is {r['top']}): {query}")
        elif r["rank"] == 1 and (b is None or b["rank"] != 1):
            failures.append(f"{skill}: negative now ranks #1 (new collision): {query}")
    for f in failures:
        print(f)
    print(f"{len(failures)} routing regression(s); recall@1 {r1}/{pos}, recall@{TOP} {r3}/{pos} (lexical)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
