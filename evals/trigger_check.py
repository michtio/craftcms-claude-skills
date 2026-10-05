#!/usr/bin/env python3
"""Single-skill recall/precision check against the REAL installed skill set.

Generalized from craft-pest-workspace/trigger_check.py (which hard-coded
TARGET = "craft-pest"). See craft-pest-workspace/EVAL-NOTES.md for why this
approach exists instead of skill-creator's own `scripts/run_eval.py`:

skill-creator's run_eval.py synthesizes a throwaway slash command and scores
a trigger only if the model's *first* tool call is Skill/Read naming that
throwaway command. Because the real skills are installed globally on this
machine (symlinked into ~/.claude/skills **and** registered via the plugin),
the model calls the *real* skill instead, whose name lacks the synthesized
suffix, and the harness scores a false negative on every query -- confirmed
with a control run against a mature skill (craft-garnish) and a near-verbatim
copy of its own README example prompt, which also scored 0.

This script instead measures the real thing: run `claude -p` against the
actually-installed production skill set (no isolation, no synthesized
commands), collect every Skill tool call from the stream-json transcript,
and check whether TARGET is among them. It is a stricter test than the
forced-choice proxy in route.py, not a weaker one -- it is what a user's
session actually does, competing against all other installed skills
(including ones from OTHER plugins/marketplaces, not just this pack's 13).

Where this differs from evals/route.py:
  - route.py isolates the 13 real skills into synthesized -x commands with
    only their listing text, and FORCES a single-token answer with no
    tools -- a controlled A/B instrument for comparing description/
    when_to_use text across two refs (e.g. working tree vs main).
  - trigger_check.py makes no changes to the environment at all: it is a
    recall/precision spot-check of one skill's real-world triggering,
    useful as a final sanity check after a route.py-driven description
    change, or whenever route.py's isolation feels too synthetic for the
    question being asked.

Usage:
    python3 evals/trigger_check.py evals/trigger-sets/craft-pest.json --target craft-pest
    python3 evals/trigger_check.py evals/trigger-sets/craft-cloud.json --target craft-cloud > results.json

Run in the FOREGROUND; backgrounding it has produced empty output before.
Expect several minutes per ~20-30 queries (one `claude -p` subprocess per
query, --workers concurrent at a time). The `ERR:exit=1` that shows up on
every row in the human-readable stderr output is `--max-turns 2` cutting the
run short deliberately -- harmless, since the stream is parsed before exit.
"""

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def skills_invoked(claude_bin: str, query: str, timeout: int) -> tuple[set[str], str]:
    """Runs the query through claude -p and returns (skills invoked, error)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    cmd = [
        claude_bin,
        "-p", query,
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", "2",
        "--allowed-tools", "Skill",
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=timeout, env=env,
            stdin=subprocess.DEVNULL, cwd="/tmp",
        )
    except subprocess.TimeoutExpired:
        return set(), "timeout"

    found: set[str] = set()

    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") != "assistant":
            continue

        for item in event.get("message", {}).get("content", []):
            if item.get("type") == "tool_use" and item.get("name") == "Skill":
                skill = item.get("input", {}).get("skill", "")
                if skill:
                    found.add(skill)

    err = "" if proc.returncode == 0 else f"exit={proc.returncode}"

    return found, err


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("eval_set", help="Path to a trigger-set JSON file: [{query, should_trigger}, ...]")
    parser.add_argument("--target", required=True, help="Skill name to check for (e.g. craft-pest, craft-cloud)")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent claude -p invocations (default: 5)")
    parser.add_argument("--timeout", type=int, default=240, help="Per-query subprocess timeout in seconds (default: 240)")
    parser.add_argument("--claude-bin", default=None, help="Path to the claude binary (default: autodetect via PATH)")
    args = parser.parse_args()

    claude_bin = args.claude_bin or shutil.which("claude") or "/opt/homebrew/bin/claude"
    eval_set = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))

    def run(idx_item):
        idx, item = idx_item
        found, err = skills_invoked(claude_bin, item["query"], args.timeout)
        # A skill may be namespaced (craftcms-claude-skills:craft-pest).
        hit = any(s.split(":")[-1] == args.target for s in found)

        return {
            "idx": idx,
            "query": item["query"][:90],
            "should_trigger": item["should_trigger"],
            "triggered": hit,
            "pass": hit == item["should_trigger"],
            "skills_invoked": sorted(found),
            "error": err,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = sorted(pool.map(run, enumerate(eval_set)), key=lambda r: r["idx"])

    passed = sum(1 for r in results if r["pass"])
    pos = [r for r in results if r["should_trigger"]]
    neg = [r for r in results if not r["should_trigger"]]

    summary = {
        "target": args.target,
        "total": len(results),
        "passed": passed,
        "recall": f"{sum(1 for r in pos if r['triggered'])}/{len(pos)}",
        "precision_negatives_correct": f"{sum(1 for r in neg if not r['triggered'])}/{len(neg)}",
    }

    print(json.dumps({"summary": summary, "results": results}, indent=2))

    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(
            f"  [{mark}] expected={r['should_trigger']!s:5} got={r['triggered']!s:5} "
            f"{r['query']}"
            + (f"  (skills: {', '.join(r['skills_invoked']) or 'none'})" if not r["pass"] else "")
            + (f"  ERR:{r['error']}" if r["error"] else ""),
            file=sys.stderr,
        )

    print(f"\n{passed}/{len(results)} passed | recall {summary['recall']} | "
          f"negatives correct {summary['precision_negatives_correct']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
