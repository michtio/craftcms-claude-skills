#!/usr/bin/env python3
"""Answer-content check against the REAL installed skill set.

trigger_check.py answers "did the skill fire?"; this answers "did the answer
contain what the skill teaches?". Each case runs one `claude -p` with the
production skills installed (no isolation, read-only tools), then scores the
final answer text against regex assertions:

  - must_match:         every group must match; a group is a list of
                        alternatives, any one of which satisfies it
  - must_not_match:     none of these may match
  - must_appear_before: [[a, b], ...] inside fenced code blocks only, the
                        first match of a must precede the first match of b;
                        passes when b never appears in code (the answer
                        never runs that step)

Cases live in evals/behavior-sets/<skill>.json:
  [{"id", "prompt", "must_match": [[...]], "must_not_match": [...],
    "must_appear_before": [[a, b]]}, ...]

Because the skills are symlinked from this working tree, a run measures the
working tree as it is on disk. Run it before an edit for the baseline and
after for the result; don't edit skill files while a run is in flight.

Usage:
    python3 evals/behavior_check.py evals/behavior-sets/craftcms.json
    python3 evals/behavior_check.py evals/behavior-sets/craftcms.json --only define-rules-nested-guard --runs 2

Run in the FOREGROUND. Each case is a full agentic answer (it may load the
skill and read references), so expect a minute or two per case.
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def answer(claude_bin: str, prompt: str, timeout: int, max_turns: int) -> tuple[str, set[str], str]:
    """Runs the prompt through claude -p and returns (final text, skills invoked, error)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    cmd = [
        claude_bin,
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", str(max_turns),
        "--allowed-tools", "Skill,Read,Grep,Glob",
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=timeout, env=env,
            stdin=subprocess.DEVNULL, cwd="/tmp",
        )
    except subprocess.TimeoutExpired:
        return "", set(), "timeout"

    text_parts: list[str] = []
    skills: set[str] = set()
    result_text = ""

    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "result":
            result_text = event.get("result") or ""
            continue

        if event.get("type") != "assistant":
            continue

        for item in event.get("message", {}).get("content", []):
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "tool_use" and item.get("name") == "Skill":
                skill = item.get("input", {}).get("skill", "")
                if skill:
                    skills.add(skill.split(":")[-1])

    err = "" if proc.returncode == 0 else f"exit={proc.returncode}"

    return result_text or "\n".join(text_parts), skills, err


def score(case: dict, text: str) -> list[str]:
    """Returns the list of failed assertions (empty means pass)."""
    failures: list[str] = []

    for group in case.get("must_match", []):
        if not any(re.search(p, text, re.I | re.S) for p in group):
            failures.append(f"missing one of {group}")

    for pattern in case.get("must_not_match", []):
        if re.search(pattern, text, re.I | re.S):
            failures.append(f"matched forbidden {pattern}")

    code = "\n".join(re.findall(r"```[^\n]*\n(.*?)```", text, re.S))

    for first, second in case.get("must_appear_before", []):
        b = re.search(second, code, re.I | re.S)
        if not b:
            continue
        a = re.search(first, code, re.I | re.S)
        if not a or a.start() > b.start():
            failures.append(f"{first} not before {second} in code")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", help="Path to a behavior-set JSON file")
    parser.add_argument("--only", default=None, help="Run a single case by id")
    parser.add_argument("--runs", type=int, default=1, help="Runs per case (default: 1)")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent claude -p invocations (default: 3)")
    parser.add_argument("--timeout", type=int, default=600, help="Per-run subprocess timeout in seconds (default: 600)")
    parser.add_argument("--max-turns", type=int, default=12, help="Agent turns per run (default: 12)")
    parser.add_argument("--claude-bin", default=None, help="Path to the claude binary (default: autodetect via PATH)")
    args = parser.parse_args()

    claude_bin = args.claude_bin or shutil.which("claude") or "/opt/homebrew/bin/claude"
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]

    jobs = [(c, n) for c in cases for n in range(args.runs)]

    def run(job):
        case, n = job
        text, skills, err = answer(claude_bin, case["prompt"], args.timeout, args.max_turns)
        failures = score(case, text) if text else ["no answer text"]

        return {
            "id": case["id"],
            "run": n + 1,
            "pass": not failures,
            "failures": failures,
            "skills_invoked": sorted(skills),
            "error": err,
            "answer": text,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = sorted(pool.map(run, jobs), key=lambda r: (r["id"], r["run"]))

    passed = sum(1 for r in results if r["pass"])

    print(json.dumps({"summary": {"total": len(results), "passed": passed}, "results": results}, indent=2))

    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(
            f"  [{mark}] {r['id']} (run {r['run']})  skills: {', '.join(r['skills_invoked']) or 'none'}"
            + (f"  ERR:{r['error']}" if r["error"] else ""),
            file=sys.stderr,
        )
        for f in r["failures"]:
            print(f"         - {f}", file=sys.stderr)

    print(f"\n{passed}/{len(results)} passed", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
