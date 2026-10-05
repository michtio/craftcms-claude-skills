#!/usr/bin/env python3
"""
Token budget measurement for Claude Code skills.

Counts tokens per file using tiktoken's cl100k_base encoding (closest
publicly available approximation to Claude's tokenizer). Reports:

  - Per-file token counts and line counts
  - Per-skill totals (SKILL.md + all references)
  - The always-loaded listing cost per skill (description + " - " +
    when_to_use, parsed from YAML frontmatter) vs the on-demand cost
    (SKILL.md body + references), since only the former is paid on
    every session regardless of whether the skill ever triggers
  - Agent definition costs, plus each agent's preload cost (its own
    body + the full SKILL.md of every skill named in its `skills:`
    frontmatter)
  - CLAUDE.md / rules costs
  - Heaviest files ranked
  - Load scenarios (which files load together for common tasks)

Frontmatter is parsed with the system `ruby` interpreter (the same
parser `bin/validate-skills.sh` uses) rather than a Python YAML
library, since this host has no `pyyaml` and ruby is already a hard
requirement for this repo's tooling (ships with macOS and every GitHub
ubuntu runner).

Usage:
    uv run --with tiktoken python3 evals/measure_tokens.py
    uv run --with tiktoken python3 evals/measure_tokens.py --json  # machine-readable
    uv run --with tiktoken python3 evals/measure_tokens.py --compare evals/snapshot-2026-05-04-post.json
    uv run --with tiktoken python3 evals/measure_tokens.py --compare evals/snapshot-2026-05-04-post.json --json
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")
ROOT = Path(__file__).resolve().parent.parent

FRONTMATTER_RE = re.compile(r"(?m)^---\s*$")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def parse_frontmatter(path: Path) -> dict:
    """Parse a file's YAML frontmatter block via system ruby.

    Mirrors bin/validate-skills.sh's own parsing: split the file on a
    line containing only `---`, take the first block as YAML. Returns
    {} if there's no frontmatter block or it fails to parse — callers
    treat that as "no description/when_to_use/skills field available"
    rather than crashing the whole measurement run.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    parts = FRONTMATTER_RE.split(text, maxsplit=2)
    if len(parts) < 3 or parts[0].strip():
        return {}

    try:
        proc = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e", "puts YAML.safe_load(STDIN.read).to_json"],
            input=parts[1],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}

    if proc.returncode != 0 or not proc.stdout.strip():
        return {}

    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def normalize_skills_field(value) -> list[str]:
    """Agent frontmatter's `skills:` accepts either a comma-separated
    scalar string or a YAML list. Normalize both to a list of names."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def measure_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    tokens = count_tokens(text)
    return {
        "path": str(path.relative_to(ROOT)),
        "lines": lines,
        "tokens": tokens,
        "tokens_per_line": round(tokens / max(lines, 1), 1),
    }


def measure_dir(directory: Path, pattern: str = "*.md") -> list[dict]:
    results = []
    for f in sorted(directory.rglob(pattern)):
        if f.is_file():
            results.append(measure_file(f))
    return results


def print_table(title: str, rows: list[dict], sort_by: str = "tokens"):
    if not rows:
        return
    sorted_rows = sorted(rows, key=lambda r: r[sort_by], reverse=True)
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    print(f"  {'File':<52} {'Lines':>6} {'Tokens':>7}")
    print(f"  {'-' * 52} {'-' * 6} {'-' * 7}")
    total_tokens = 0
    total_lines = 0
    for row in sorted_rows:
        name = row["path"]
        # Shorten path for readability
        if "references/" in name:
            name = "  refs/" + name.split("references/")[-1]
        elif "skills/" in name:
            parts = name.split("/")
            name = "/".join(parts[1:])
        elif "agents/" in name:
            name = name
        print(f"  {name:<52} {row['lines']:>6} {row['tokens']:>7}")
        total_tokens += row["tokens"]
        total_lines += row["lines"]
    print(f"  {'-' * 52} {'-' * 6} {'-' * 7}")
    print(f"  {'TOTAL':<52} {total_lines:>6} {total_tokens:>7}")
    return total_tokens


def measure_skill(skill_dir: Path) -> dict:
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    refs_dir = skill_dir / "references"

    result = {"name": skill_name, "skill_md": None, "references": [], "total_tokens": 0}

    if skill_md.exists():
        m = measure_file(skill_md)
        result["skill_md"] = m
        result["total_tokens"] += m["tokens"]

        fm = parse_frontmatter(skill_md)
        description = str(fm.get("description") or "")
        when_to_use = str(fm.get("when_to_use") or "")
        listing_text = f"{description} - {when_to_use}" if when_to_use else description
        result["always_loaded"] = {
            "description_chars": len(description),
            "when_to_use_chars": len(when_to_use),
            "listing_chars": len(listing_text),
            "listing_tokens": count_tokens(listing_text) if listing_text else 0,
        }
    else:
        result["always_loaded"] = {
            "description_chars": 0,
            "when_to_use_chars": 0,
            "listing_chars": 0,
            "listing_tokens": 0,
        }

    if refs_dir.exists():
        for f in sorted(refs_dir.glob("*.md")):
            m = measure_file(f)
            result["references"].append(m)
            result["total_tokens"] += m["tokens"]

    return result


def measure_agent_preload(agent_path: Path, skills_by_name: dict) -> dict:
    """An agent's real preload cost: its own body plus the full
    SKILL.md (not references — those still load on demand within the
    agent's run) of every skill named in its `skills:` frontmatter."""
    fm = parse_frontmatter(agent_path)
    skill_names = normalize_skills_field(fm.get("skills"))
    body_tokens = count_tokens(agent_path.read_text(encoding="utf-8"))

    skills_tokens = 0
    missing = []
    for name in skill_names:
        skill = skills_by_name.get(name)
        if skill and skill.get("skill_md"):
            skills_tokens += skill["skill_md"]["tokens"]
        else:
            missing.append(name)

    return {
        "name": agent_path.stem,
        "body_tokens": body_tokens,
        "skills": skill_names,
        "skills_preload_tokens": skills_tokens,
        "total_preload_tokens": body_tokens + skills_tokens,
        "missing_skills": missing,
    }


# Common task scenarios — which files load together. Every path is
# verified to exist at measurement time (see verify_scenarios());
# a scenario referencing a renamed/removed file is reported, not
# silently dropped.
LOAD_SCENARIOS = {
    "Build custom element type": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/elements.md",
        "skills/craftcms/references/element-index.md",
        "skills/craftcms/references/fields.md",
        "skills/craftcms/references/migrations.md",
        "skills/craftcms/references/cp.md",
    ],
    "Add webhook endpoint": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/controllers.md",
        "skills/craftcms/references/events.md",
    ],
    "Build settings page": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/controllers.md",
        "skills/craftcms/references/cp.md",
        "skills/craftcms/references/architecture.md",
    ],
    "Write Twig templates": [
        "skills/craft-twig-guidelines/SKILL.md",
        "skills/craft-site/SKILL.md",
    ],
    "Create queue job + element sync": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/queue-jobs.md",
        "skills/craftcms/references/elements.md",
        "skills/craftcms/references/debugging.md",
    ],
    "Custom field type": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/field-types-custom.md",
        "skills/craftcms/references/fields.md",
        "skills/craftcms/references/events.md",
    ],
    "Configure Redis + caching": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/config-app.md",
        "skills/craftcms/references/caching.md",
    ],
    "Element authorization": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/element-authorization.md",
        "skills/craftcms/references/permissions.md",
    ],
    "Write Pest tests for a new element type": [
        "skills/craft-pest/SKILL.md",
        "skills/craft-pest/references/patterns.md",
        "skills/craft-pest/references/isolation.md",
        "skills/craft-pest/references/craft-state.md",
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/elements.md",
        "skills/craftcms/references/testing.md",
    ],
    "Cut a plugin release": [
        "skills/craft-plugin-release/SKILL.md",
        "skills/craft-plugin-release/references/history-rewrites.md",
        "skills/craft-plugin-release/references/path-repositories.md",
    ],
    "Deploy to Craft Cloud": [
        "skills/craft-cloud/SKILL.md",
        "skills/craft-cloud/references/deploy-pipeline.md",
        "skills/craft-cloud/references/config-file.md",
        "skills/craft-cloud/references/database.md",
        "skills/craft-cloud/references/commands-and-cron.md",
    ],
    "Configure Servd hosting": [
        "skills/servd/SKILL.md",
        "skills/servd/references/deploy-and-environments.md",
        "skills/servd/references/asset-storage.md",
        "skills/servd/references/database-and-queue.md",
    ],
    "Configure Formie + Blitz": [
        "skills/craft-plugins/SKILL.md",
        "skills/craft-plugins/references/formie.md",
        "skills/craft-plugins/references/blitz.md",
    ],
    "CP JS modal (Garnish)": [
        "skills/craft-garnish/SKILL.md",
        "skills/craft-garnish/references/ui-widgets.md",
        "skills/craft-garnish/references/class-system.md",
        "skills/craft-garnish/references/utilities.md",
    ],
    "Headless GraphQL + session auth + console command": [
        "skills/craftcms/SKILL.md",
        "skills/craftcms/references/graphql.md",
        "skills/craftcms/references/sessions-and-auth.md",
        "skills/craftcms/references/console-commands.md",
    ],
}


def verify_scenarios() -> list[str]:
    """Return every (scenario, path) pair referencing a file that
    doesn't exist. Non-fatal — callers decide how loudly to surface it."""
    missing = []
    for name, paths in LOAD_SCENARIOS.items():
        for p in paths:
            if not (ROOT / p).exists():
                missing.append(f"{name}: {p}")
    return missing


def scenario_tokens(paths: list[str]) -> tuple[int, int]:
    total = 0
    count = 0
    for p in paths:
        full = ROOT / p
        if full.exists():
            total += count_tokens(full.read_text(encoding="utf-8"))
            count += 1
    return count, total


def build_report() -> dict:
    skills_dir = ROOT / "skills"
    agents_dir = ROOT / "agents"
    templates_dir = ROOT / "project-template"

    skill_results = []
    all_files = []

    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            result = measure_skill(skill_dir)
            skill_results.append(result)
            if result["skill_md"]:
                all_files.append(result["skill_md"])
            all_files.extend(result["references"])

    skills_by_name = {s["name"]: s for s in skill_results}

    agent_files = []
    agent_preload = []
    if agents_dir.exists():
        agent_files = measure_dir(agents_dir)
        all_files.extend(agent_files)
        for agent_path in sorted(agents_dir.glob("*.md")):
            agent_preload.append(measure_agent_preload(agent_path, skills_by_name))

    template_files = []
    if templates_dir.exists():
        template_files = measure_dir(templates_dir)
        all_files.extend(template_files)

    scenarios = {}
    for name, paths in LOAD_SCENARIOS.items():
        file_count, tokens = scenario_tokens(paths)
        scenarios[name] = {"files": file_count, "tokens": tokens}

    always_loaded_total = sum(s["always_loaded"]["listing_tokens"] for s in skill_results)
    on_demand_skill_md_total = sum(s["skill_md"]["tokens"] for s in skill_results if s["skill_md"])
    on_demand_references_total = sum(
        r["tokens"] for s in skill_results for r in s["references"]
    )

    return {
        "encoding": "cl100k_base",
        "skills": skill_results,
        "agents": agent_files,
        "agent_preload": agent_preload,
        "templates": template_files,
        "scenarios": scenarios,
        "budget_summary": {
            "always_loaded_total_tokens": always_loaded_total,
            "on_demand_skill_md_total_tokens": on_demand_skill_md_total,
            "on_demand_references_total_tokens": on_demand_references_total,
            "on_demand_total_tokens": on_demand_skill_md_total + on_demand_references_total,
        },
        "grand_total": {
            "files": len(all_files),
            "tokens": sum(f["tokens"] for f in all_files),
            "lines": sum(f["lines"] for f in all_files),
        },
    }


def print_human_report(report: dict, missing_scenario_paths: list[str]):
    skill_results = report["skills"]
    agent_files = report["agents"]
    template_files = report["templates"]
    all_files = []
    for skill in skill_results:
        if skill["skill_md"]:
            all_files.append(skill["skill_md"])
        all_files.extend(skill["references"])
    all_files.extend(agent_files)
    all_files.extend(template_files)

    # Print skill-by-skill breakdown
    for skill in sorted(skill_results, key=lambda s: s["total_tokens"], reverse=True):
        rows = []
        if skill["skill_md"]:
            rows.append(skill["skill_md"])
        rows.extend(skill["references"])
        print_table(f"Skill: {skill['name']} ({skill['total_tokens']:,} tokens total)", rows)

    # Print agents
    if agent_files:
        print_table("Agent Definitions", agent_files)

    # Print templates
    if template_files:
        print_table("Project Templates", template_files)

    # Always-loaded listing cost (every session, every skill, whether or not it triggers)
    print(f"\n{'=' * 70}")
    print("  ALWAYS-LOADED SKILL LISTING (description + when_to_use)")
    print(f"{'=' * 70}")
    print(f"  {'Skill':<30} {'Chars':>7} {'Tokens':>7}")
    print(f"  {'-' * 30} {'-' * 7} {'-' * 7}")
    for skill in sorted(skill_results, key=lambda s: s["always_loaded"]["listing_tokens"], reverse=True):
        al = skill["always_loaded"]
        print(f"  {skill['name']:<30} {al['listing_chars']:>7} {al['listing_tokens']:>7}")
    print(f"  {'-' * 30} {'-' * 7} {'-' * 7}")
    bs = report["budget_summary"]
    print(f"  {'TOTAL (paid every session)':<30} {'':>7} {bs['always_loaded_total_tokens']:>7}")

    print(f"\n{'=' * 70}")
    print("  BUDGET SUMMARY: always-loaded vs on-demand")
    print(f"{'=' * 70}")
    print(f"  Always-loaded listings (every session) : {bs['always_loaded_total_tokens']:>8,} tokens")
    print(f"  On-demand SKILL.md bodies (when triggered): {bs['on_demand_skill_md_total_tokens']:>8,} tokens")
    print(f"  On-demand references (when read)        : {bs['on_demand_references_total_tokens']:>8,} tokens")
    print(f"  On-demand total                          : {bs['on_demand_total_tokens']:>8,} tokens")

    # Agent preload costs
    if report["agent_preload"]:
        print(f"\n{'=' * 70}")
        print("  AGENT PRELOAD COST (agent body + full SKILL.md of each named skill)")
        print(f"{'=' * 70}")
        print(f"  {'Agent':<28} {'Body':>7} {'+Skills':>8} {'=Total':>8}  Skills")
        print(f"  {'-' * 28} {'-' * 7} {'-' * 8} {'-' * 8}")
        for ap in sorted(report["agent_preload"], key=lambda a: a["total_preload_tokens"], reverse=True):
            skills_str = ", ".join(ap["skills"]) if ap["skills"] else "(none)"
            print(
                f"  {ap['name']:<28} {ap['body_tokens']:>7} {ap['skills_preload_tokens']:>8} "
                f"{ap['total_preload_tokens']:>8}  {skills_str}"
            )
            if ap["missing_skills"]:
                print(f"  {'':<28} WARNING: unmeasured skills (not found): {', '.join(ap['missing_skills'])}")

    # Top 15 heaviest files across everything
    print(f"\n{'=' * 70}")
    print("  TOP 15 HEAVIEST FILES")
    print(f"{'=' * 70}")
    ranked = sorted(all_files, key=lambda f: f["tokens"], reverse=True)[:15]
    print(f"  {'#':<4} {'File':<48} {'Tokens':>7} {'Lines':>6}")
    print(f"  {'-' * 4} {'-' * 48} {'-' * 7} {'-' * 6}")
    for i, f in enumerate(ranked, 1):
        name = f["path"]
        if len(name) > 48:
            name = "..." + name[-45:]
        print(f"  {i:<4} {name:<48} {f['tokens']:>7} {f['lines']:>6}")

    # Load scenarios
    print(f"\n{'=' * 70}")
    print("  LOAD SCENARIOS (files loaded together for common tasks)")
    print(f"{'=' * 70}")
    print(f"  {'Scenario':<48} {'Files':>5} {'Tokens':>8}")
    print(f"  {'-' * 48} {'-' * 5} {'-' * 8}")
    for name, s in sorted(report["scenarios"].items(), key=lambda x: x[0]):
        print(f"  {name:<48} {s['files']:>5} {s['tokens']:>8}")

    if missing_scenario_paths:
        print(f"\n  WARNING: scenario files not found on disk (excluded from totals above):")
        for m in missing_scenario_paths:
            print(f"    - {m}")

    # Grand total
    grand = report["grand_total"]
    print(f"\n{'=' * 70}")
    print(f"  GRAND TOTAL: {grand['files']} files, {grand['lines']:,} lines, {grand['tokens']:,} tokens")
    print(f"{'=' * 70}")


def compare_snapshots(old: dict, new: dict, json_mode: bool):
    old_by_name = {s["name"]: s for s in old.get("skills", [])}
    new_by_name = {s["name"]: s for s in new.get("skills", [])}
    names = sorted(set(old_by_name) | set(new_by_name))

    rows = []
    for name in names:
        o = old_by_name.get(name)
        n = new_by_name.get(name)
        old_tokens = o["total_tokens"] if o else 0
        new_tokens = n["total_tokens"] if n else 0
        delta = new_tokens - old_tokens
        if old_tokens:
            pct = round(delta / old_tokens * 100, 1)
        else:
            pct = None  # brand new skill, no baseline to divide by
        status = "new" if o is None else ("removed" if n is None else "changed")
        rows.append(
            {
                "skill": name,
                "old_tokens": old_tokens,
                "new_tokens": new_tokens,
                "delta": delta,
                "delta_pct": pct,
                "status": status,
            }
        )

    old_total = old.get("grand_total", {}).get("tokens", 0)
    new_total = new.get("grand_total", {}).get("tokens", 0)
    total_delta = new_total - old_total
    total_pct = round(total_delta / old_total * 100, 1) if old_total else None

    result = {
        "rows": rows,
        "old_grand_total_tokens": old_total,
        "new_grand_total_tokens": new_total,
        "delta": total_delta,
        "delta_pct": total_pct,
    }

    if json_mode:
        print(json.dumps(result, indent=2))
        return

    print(f"\n{'=' * 70}")
    print("  SNAPSHOT COMPARISON")
    print(f"{'=' * 70}")
    print(f"  {'Skill':<28} {'Old':>9} {'New':>9} {'Delta':>9} {'%':>8}")
    print(f"  {'-' * 28} {'-' * 9} {'-' * 9} {'-' * 9} {'-' * 8}")
    for r in sorted(rows, key=lambda r: r["delta"], reverse=True):
        if r["status"] == "new":
            pct_s = "new"
        elif r["status"] == "removed":
            pct_s = "removed"
        else:
            pct_s = f"{r['delta_pct']:+.1f}%"
        print(f"  {r['skill']:<28} {r['old_tokens']:>9} {r['new_tokens']:>9} {r['delta']:>+9} {pct_s:>8}")
    print(f"  {'-' * 28} {'-' * 9} {'-' * 9} {'-' * 9} {'-' * 8}")
    pct_s = f"{total_pct:+.1f}%" if total_pct is not None else "n/a"
    print(f"  {'TOTAL':<28} {old_total:>9} {new_total:>9} {total_delta:>+9} {pct_s:>8}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a human report")
    parser.add_argument(
        "--compare",
        metavar="SNAPSHOT",
        help="Diff a prior snapshot JSON (e.g. evals/snapshot-2026-05-04-post.json) against the current measurement",
    )
    args = parser.parse_args()

    report = build_report()
    missing = verify_scenarios()

    if args.compare:
        try:
            old = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"error: could not read/parse --compare snapshot {args.compare}: {e}", file=sys.stderr)
            sys.exit(1)
        compare_snapshots(old, report, json_mode=args.json)
        return

    if args.json:
        if missing:
            report["scenario_warnings"] = missing
        print(json.dumps(report, indent=2))
        return

    print_human_report(report, missing)


if __name__ == "__main__":
    main()
