#!/usr/bin/env python3
"""
Forced-choice skill routing harness.

First used to A/B the 1.18.x description/when_to_use split
(191/258 vs 192/258 before/after).

What it does
------------
For a given "condition" (either the working tree, or a git ref such as
`main`), writes every skill's always-loaded listing (`description` +
`when_to_use`, parsed from YAML frontmatter) as a throwaway slash
command `<name>-x.md` under an isolated temp project directory, with a
`.claude/settings.json` that disables the installed
`craftcms-claude-skills` plugin and turns every real skill name's
`skillOverrides` to `"off"` — so the only thing competing for the
model's routing choice is the synthesized listing text, not the real
installed skill set.

For every query in `evals/trigger-sets/*.json`, it then asks
`claude -p` (no tools, forced single-token answer: the chosen skill
name or NONE) which ONE skill it would load, and scores the answer
(with a trailing `-x` stripped) against that query's `should_trigger`
flag: a positive passes if the chosen skill matches the set's skill; a
negative passes if it does NOT.

This measures routing/triggering quality, independent of whatever the
real installed skill is actually doing — useful for A/B-ing a
description rewrite before merging it (`--compare-ref main`), without
needing the production skill set installed or touched.

IMPORTANT: this makes real `claude -p` model calls (one per query per
run per condition) unless `--dry-run` is passed. Costs add up fast with
13 skills x ~16 queries x --runs x 2 conditions. Always sanity-check
a new invocation with `--dry-run` first.

Usage
-----
    # Dry run: sets up the isolated project dir(s) and command files,
    # prints what it WOULD ask, makes zero model calls.
    python3 evals/route.py --dry-run
    python3 evals/route.py --dry-run --compare-ref main

    # Single condition against the working tree
    python3 evals/route.py --ref working --runs 2 --workers 10

    # A/B: working tree vs main (the main use case)
    python3 evals/route.py --compare-ref main --runs 2

    # Narrow to one trigger set, write full results to a file
    python3 evals/route.py --sets evals/trigger-sets --out evals/route-results.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SETS_DIR = REPO / "evals" / "trigger-sets"

# The installed plugin's marketplace@plugin key, as it appears in a
# real ~/.claude*/settings.json enabledPlugins block. Disabling it is
# what forces the model to choose among the synthesized -x commands
# instead of the real installed skills.
PLUGIN_KEY = "craftcms-claude-skills@craftcms-claude-skills"

PROMPT_PREFIX = (
    "Do not use any tools and do not do the task. Look at the skills available to you. "
    "Which ONE skill would you load first to handle the request below? "
    "Reply with only the exact skill name, or NONE if no skill fits.\n\nRequest: "
)


def discover_skill_names() -> list[str]:
    skills_dir = REPO / "skills"
    return sorted(p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def parse_frontmatter(text: str) -> dict:
    """Parse a SKILL.md's YAML frontmatter via system ruby (same parser
    bin/validate-skills.sh and evals/measure_tokens.py use)."""
    m = re.split(r"(?m)^---\s*$", text, maxsplit=2)
    if len(m) < 3 or m[0].strip():
        return {}
    proc = subprocess.run(
        ["ruby", "-ryaml", "-rjson", "-e", "puts YAML.safe_load(STDIN.read).to_json"],
        input=m[1],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def skill_md_text(name: str, ref: str) -> str:
    path = f"skills/{name}/SKILL.md"
    if ref == "working":
        return (REPO / path).read_text(encoding="utf-8")
    proc = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git show {ref}:{path} failed: {proc.stderr.strip()}")
    return proc.stdout


def indent(text: str) -> str:
    return "  " + "\n  ".join(text.split("\n"))


def write_condition(root: Path, ref: str, skill_names: list[str]) -> Path:
    """Write <name>-x.md command files + settings.json for one condition.
    Returns the settings.json path."""
    cmd_dir = root / ".claude" / "commands"
    if cmd_dir.exists():
        shutil.rmtree(cmd_dir)
    cmd_dir.mkdir(parents=True)

    for name in skill_names:
        src = skill_md_text(name, ref)
        fm = parse_frontmatter(src)
        description = str(fm.get("description") or "")
        when_to_use = str(fm.get("when_to_use") or "")
        body = f"---\ndescription: |\n{indent(description)}\n"
        if when_to_use:
            body += f"when_to_use: |\n{indent(when_to_use)}\n"
        body += f"---\n\n# {name}\n"
        (cmd_dir / f"{name}-x.md").write_text(body, encoding="utf-8")

    settings = {
        "enabledPlugins": {PLUGIN_KEY: False},
        "skillOverrides": {name: "off" for name in skill_names},
    }
    settings_path = root / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings_path


def load_queries(sets_dir: Path) -> list[dict]:
    items = []
    for f in sorted(Path(sets_dir).glob("*.json")):
        skill = f.stem
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"warning: skipping unparsable trigger set {f}: {e}", file=sys.stderr)
            continue
        for it in data:
            items.append({"skill": skill, "query": it["query"], "should_trigger": it["should_trigger"]})
    return items


def build_claude_cmd(claude_bin: str, query: str, model: str, settings_path: Path) -> list[str]:
    return [
        claude_bin,
        "-p",
        PROMPT_PREFIX + query,
        "--output-format",
        "json",
        "--model",
        model,
        "--max-turns",
        "1",
        "--settings",
        str(settings_path),
    ]


def ask(claude_bin: str, root: Path, settings_path: Path, model: str, query: str, timeout: int) -> str:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    cmd = build_claude_cmd(claude_bin, query, model, settings_path)
    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "ERR"

    result = (data.get("result") or "").strip()
    if not result:
        return ""
    token = result.split()[0].strip("`*/.,").lower()
    return token


def score(item: dict, answer: str) -> dict:
    chosen = answer[:-2] if answer.endswith("-x") else answer
    fired = chosen == item["skill"]
    passed = fired == item["should_trigger"]
    return {**item, "answer": answer, "chosen": chosen, "fired": fired, "pass": passed}


def run_condition(
    claude_bin: str,
    root: Path,
    settings_path: Path,
    model: str,
    runs: int,
    workers: int,
    items: list[dict],
    timeout: int,
) -> list[dict]:
    jobs = [item for item in items for _ in range(runs)]

    def work(item: dict) -> dict:
        answer = ask(claude_bin, root, settings_path, model, item["query"], timeout)
        return score(item, answer)

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, item) for item in jobs]
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def summarize(results: list[dict]) -> dict:
    by_skill = defaultdict(lambda: {"pass": 0, "total": 0})
    for r in results:
        by_skill[r["skill"]]["total"] += 1
        by_skill[r["skill"]]["pass"] += 1 if r["pass"] else 0
    overall_pass = sum(1 for r in results if r["pass"])
    return {
        "overall_pass": overall_pass,
        "overall_total": len(results),
        "overall": f"{overall_pass}/{len(results)}",
        "by_skill": {k: f"{v['pass']}/{v['total']}" for k, v in sorted(by_skill.items())},
    }


def print_summary(label: str, summary: dict):
    print(f"\n=== {label} ===")
    print(f"Overall: {summary['overall']}")
    for skill, s in summary["by_skill"].items():
        print(f"  {skill:<28} {s}")


def print_ab_delta(ref_a: str, ref_b: str, summary_a: dict, summary_b: dict):
    print(f"\n=== A/B DELTA ({ref_a} -> {ref_b}) ===")
    print(f"Overall: {summary_a['overall']} -> {summary_b['overall']}")
    all_skills = sorted(set(summary_a["by_skill"]) | set(summary_b["by_skill"]))
    for skill in all_skills:
        a = summary_a["by_skill"].get(skill, "-")
        b = summary_b["by_skill"].get(skill, "-")
        flag = "  <-- changed" if a != b else ""
        print(f"  {skill:<28} {a:>7} -> {b:<7}{flag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--ref",
        default="working",
        help="Git ref to read SKILL.md frontmatter from, or 'working' for the working tree (default: working)",
    )
    parser.add_argument(
        "--compare-ref",
        default=None,
        metavar="REF",
        help="Second condition for an A/B comparison (e.g. 'main'). When set, --ref is condition A and this is condition B.",
    )
    parser.add_argument("--model", default="sonnet", help="Model alias to pass to claude -p (default: sonnet)")
    parser.add_argument("--runs", type=int, default=1, help="Repeat every query this many times per condition (default: 1)")
    parser.add_argument("--workers", type=int, default=10, help="Thread pool size (default: 10)")
    parser.add_argument("--sets", default=str(DEFAULT_SETS_DIR), help="Directory of trigger-set JSON files (default: evals/trigger-sets)")
    parser.add_argument("--out", default=None, help="Write full per-query results as JSON to this path (default: don't write)")
    parser.add_argument("--timeout", type=int, default=180, help="Per-query subprocess timeout in seconds (default: 180)")
    parser.add_argument("--claude-bin", default=None, help="Path to the claude binary (default: autodetect via PATH)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Set up command files + settings.json and print what would be asked. Makes ZERO model calls.",
    )
    args = parser.parse_args()

    skill_names = discover_skill_names()
    items = load_queries(Path(args.sets))
    if not items:
        print(f"error: no trigger-set queries found under {args.sets}", file=sys.stderr)
        sys.exit(1)

    conditions = [args.ref] + ([args.compare_ref] if args.compare_ref else [])

    claude_bin = args.claude_bin or shutil.which("claude") or "/opt/homebrew/bin/claude"

    tmp_root = Path(tempfile.mkdtemp(prefix="route-harness-"))
    cond_roots: dict[str, Path] = {}
    cond_settings: dict[str, Path] = {}
    for cond in conditions:
        root = tmp_root / cond.replace("/", "_")
        root.mkdir(parents=True, exist_ok=True)
        try:
            cond_settings[cond] = write_condition(root, cond, skill_names)
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        cond_roots[cond] = root

    if args.dry_run:
        print(f"Discovered {len(skill_names)} skills: {', '.join(skill_names)}")
        print(f"Isolated project dir(s) under: {tmp_root}")
        for cond in conditions:
            cmd_files = sorted((cond_roots[cond] / ".claude" / "commands").glob("*.md"))
            print(f"\nCondition '{cond}':")
            print(f"  root:     {cond_roots[cond]}")
            print(f"  settings: {cond_settings[cond]}")
            print(f"  command files ({len(cmd_files)}): {[f.name for f in cmd_files]}")

        print(f"\n{len(items)} queries loaded from {args.sets}")
        pos = sum(1 for i in items if i["should_trigger"])
        print(f"  {pos} positive / {len(items) - pos} negative, across {len({i['skill'] for i in items})} skills")
        print(f"Would run {len(items)} queries x {args.runs} run(s) x {len(conditions)} condition(s) "
              f"= {len(items) * args.runs * len(conditions)} total claude -p calls (model={args.model}, workers={args.workers})")

        example_settings = cond_settings[conditions[0]]
        example_cmd = build_claude_cmd(claude_bin, items[0]["query"], args.model, example_settings)
        print("\nExample claude -p invocation that WOULD run (not executed):")
        print("  " + " ".join(c if " " not in c else repr(c) for c in example_cmd))
        print(f"  cwd={cond_roots[conditions[0]]}  stdin=DEVNULL  timeout={args.timeout}s")

        print("\nFirst 5 prompts that would be sent:")
        for item in items[:5]:
            print(f"  [{item['skill']:<26} expect_trigger={item['should_trigger']!s:5}] "
                  f"{PROMPT_PREFIX.splitlines()[0]} ... Request: {item['query'][:70]}...")
        print(f"\n(Isolated project dir left on disk for inspection: {tmp_root})")
        return

    all_results: dict[str, list[dict]] = {}
    summaries: dict[str, dict] = {}
    for cond in conditions:
        print(f"Running condition '{cond}': {len(items)} queries x {args.runs} run(s)...", file=sys.stderr)
        results = run_condition(
            claude_bin, cond_roots[cond], cond_settings[cond], args.model, args.runs, args.workers, items, args.timeout
        )
        all_results[cond] = results
        summaries[cond] = summarize(results)
        print_summary(cond, summaries[cond])

        errs = sum(1 for r in results if r["answer"] in ("ERR", "TIMEOUT", ""))
        if errs:
            print(f"  ({errs} empty/error/timeout responses out of {len(results)})", file=sys.stderr)

    if len(conditions) == 2:
        print_ab_delta(conditions[0], conditions[1], summaries[conditions[0]], summaries[conditions[1]])

    if args.out:
        Path(args.out).write_text(
            json.dumps({"summaries": summaries, "results": all_results}, indent=2), encoding="utf-8"
        )
        print(f"\nWrote full results to {args.out}")


if __name__ == "__main__":
    main()
