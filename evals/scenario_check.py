#!/usr/bin/env python3
"""Real-life routing scenarios: a handful of realistic prompts, each run inside a
fixture project, passing when one of the expected skills loads.

A cheap routing smoke test for listing changes (one model call per scenario),
in place of a full trigger-set or route.py A/B run. Scenarios live in
evals/scenarios.json: [{"id", "cwd", "prompt", "expect_any": [skill, ...]}].

Usage:
    python3 evals/scenario_check.py                 # every scenario
    python3 evals/scenario_check.py --only ddev-port-conflict
    python3 evals/scenario_check.py --dry-run

Only the Skill tool is offered (as in the trigger runs), with three turns so a
prompt can load more than one skill. A usage-limit message stops the run.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))
from release_evals import Runner  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated scenario ids")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--claude-bin", default=None)
    args = ap.parse_args()

    scenarios = json.loads((REPO / "evals" / "scenarios.json").read_text(encoding="utf-8"))
    if args.only:
        scenarios = [s for s in scenarios if s["id"] in set(args.only.split(","))]
    print(f"{len(scenarios)} scenario(s), {len(scenarios)} model call(s)")
    if args.dry_run:
        for s in scenarios:
            print(f"  {s['id']:26} expects any of {', '.join(s['expect_any'])}")
        return 0

    claude_bin = str(Path(args.claude_bin).resolve()) if args.claude_bin else (shutil.which("claude") or "/opt/homebrew/bin/claude")
    runner = Runner(claude_bin, args.model, 300, plugin_dir=True)
    failed = 0
    for s in scenarios:
        _, skills, err, _ = runner.claude(s["prompt"], str(REPO / s["cwd"]), "Skill", 3)
        if err:
            print(f"  ERROR {s['id']}: {err}")
            if err == "usage limit":
                print("stopped at a usage limit")
                return 3
            failed += 1
            continue
        ok = bool(set(s["expect_any"]) & skills)
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {s['id']:26} loaded: {', '.join(sorted(skills)) or 'none'}")
    print(f"{len(scenarios) - failed}/{len(scenarios)} passed | model calls: {runner.calls}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
