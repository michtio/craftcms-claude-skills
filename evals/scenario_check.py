#!/usr/bin/env python3
"""Real-life routing scenarios: a handful of realistic prompts, each run inside a
fixture project, passing when one of the expected skills loads and none of the
forbidden ones does.

A cheap routing smoke test for listing changes (one model call per scenario),
in place of a full trigger-set or route.py A/B run. Scenarios live in
evals/scenarios.json: [{"id", "cwd", "prompt", "expect_any": [skill, ...],
"expect_none": [skill, ...]}]. "expect_none" is optional: the scenario fails when
any skill in it loads (a negative scenario, such as a plain build request that
must not load a skill keyed on a profile file).

Usage:
    python3 evals/scenario_check.py                 # every scenario
    python3 evals/scenario_check.py --only ddev-port-conflict
    python3 evals/scenario_check.py --dry-run
    python3 evals/scenario_check.py --changed       # only scenarios naming a skill whose listing changed since the last tag

Only the Skill tool is offered (as in the trigger runs), and each call stops at
the routing decision: one turn (a scenario may set "max_turns" when its skill
only loads second). Results print as they arrive. A usage-limit message stops the run.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))
from release_evals import Runner  # noqa: E402

print = functools.partial(print, flush=True)  # noqa: A001  (stream results, not at exit)


def listing(text: str) -> str:
    """The routing listing of a SKILL.md: its name, description and when_to_use frontmatter."""
    head = text.split("\n---", 1)[0] if text.startswith("---") else ""
    return "\n".join(l for l in head.splitlines() if not re.match(r"^\s*(version|metadata|license)\b", l))


def changed_skills(base: str | None) -> tuple[str, set[str]]:
    """Skills whose SKILL.md frontmatter differs between base (default: last tag) and the working tree."""
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)  # noqa: E731
    base = base or git("describe", "--tags", "--abbrev=0").stdout.strip()
    out = set()
    for f in sorted((REPO / "skills").glob("*/SKILL.md")):
        old = git("show", f"{base}:{f.relative_to(REPO)}")
        if old.returncode or listing(old.stdout) != listing(f.read_text(encoding="utf-8")):
            out.add(f.parent.name)
    return base, out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated scenario ids")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--changed", nargs="?", const="", metavar="REF",
                    help="only scenarios naming a skill (expect_any or expect_none) whose listing changed since REF (default: last tag)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--claude-bin", default=None)
    args = ap.parse_args()

    scenarios = json.loads((REPO / "evals" / "scenarios.json").read_text(encoding="utf-8"))
    if args.only:
        scenarios = [s for s in scenarios if s["id"] in set(args.only.split(","))]
    if args.changed is not None:
        base, skills_changed = changed_skills(args.changed or None)
        print(f"listings changed since {base}: {', '.join(sorted(skills_changed)) or 'none'}")
        scenarios = [s for s in scenarios if (set(s["expect_any"]) | set(s.get("expect_none", []))) & skills_changed]
    print(f"{len(scenarios)} scenario(s), {len(scenarios)} model call(s)")
    if args.dry_run:
        for s in scenarios:
            none = f"; none of {', '.join(s['expect_none'])}" if s.get("expect_none") else ""
            print(f"  {s['id']:26} expects any of {', '.join(s['expect_any'])}{none}")
        return 0

    claude_bin = str(Path(args.claude_bin).resolve()) if args.claude_bin else (shutil.which("claude") or "/opt/homebrew/bin/claude")
    runner = Runner(claude_bin, args.model, 300, plugin_dir=True)
    failed = 0
    for s in scenarios:
        _, skills, err, _ = runner.claude(s["prompt"], str(REPO / s["cwd"]), "Skill", s.get("max_turns", 1))
        if err:
            print(f"  ERROR {s['id']}: {err}")
            if err == "usage limit":
                print("stopped at a usage limit")
                return 3
            failed += 1
            continue
        forbidden = set(s.get("expect_none", [])) & skills
        ok = bool(set(s["expect_any"]) & skills) and not forbidden
        failed += not ok
        why = f" (forbidden: {', '.join(sorted(forbidden))})" if forbidden else ""
        print(f"  {'PASS' if ok else 'FAIL'}  {s['id']:26} loaded: {', '.join(sorted(skills)) or 'none'}{why}")
    print(f"{len(scenarios) - failed}/{len(scenarios)} passed | model calls: {runner.calls}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
