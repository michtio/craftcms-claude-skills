#!/usr/bin/env python3
"""
Token budget measurement for Claude Code skills.

Counts tokens per file using tiktoken's cl100k_base encoding (closest
publicly available approximation to Claude's tokenizer). Reports:

  - Per-file token counts and line counts
  - Per-skill totals (SKILL.md + all references)
  - Agent definition costs
  - CLAUDE.md / rules costs
  - Heaviest files ranked
  - Load scenarios (which files load together for common tasks)

Usage:
    uv run --with tiktoken python3 evals/measure_tokens.py
    uv run --with tiktoken python3 evals/measure_tokens.py --json  # machine-readable
"""

import json
import os
import sys
from pathlib import Path

import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")
ROOT = Path(__file__).resolve().parent.parent


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


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

    if refs_dir.exists():
        for f in sorted(refs_dir.glob("*.md")):
            m = measure_file(f)
            result["references"].append(m)
            result["total_tokens"] += m["tokens"]

    return result


# Common task scenarios — which files load together
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
}


def main():
    json_mode = "--json" in sys.argv

    skills_dir = ROOT / "skills"
    agents_dir = ROOT / "agents"
    templates_dir = ROOT / "project-template"

    # Measure all skills
    skill_results = []
    all_files = []

    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            result = measure_skill(skill_dir)
            skill_results.append(result)
            if result["skill_md"]:
                all_files.append(result["skill_md"])
            all_files.extend(result["references"])

    # Measure agents
    agent_files = []
    if agents_dir.exists():
        agent_files = measure_dir(agents_dir)
        all_files.extend(agent_files)

    # Measure project template
    template_files = []
    if templates_dir.exists():
        template_files = measure_dir(templates_dir)
        all_files.extend(template_files)

    if json_mode:
        output = {
            "encoding": "cl100k_base",
            "skills": skill_results,
            "agents": agent_files,
            "templates": template_files,
            "scenarios": {},
            "grand_total": {
                "files": len(all_files),
                "tokens": sum(f["tokens"] for f in all_files),
                "lines": sum(f["lines"] for f in all_files),
            },
        }
        for name, paths in LOAD_SCENARIOS.items():
            scenario_tokens = 0
            for p in paths:
                full = ROOT / p
                if full.exists():
                    scenario_tokens += count_tokens(full.read_text(encoding="utf-8"))
            output["scenarios"][name] = {"files": len(paths), "tokens": scenario_tokens}
        print(json.dumps(output, indent=2))
        return

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
    print(f"  {'Scenario':<40} {'Files':>5} {'Tokens':>8}")
    print(f"  {'-' * 40} {'-' * 5} {'-' * 8}")
    for name, paths in sorted(LOAD_SCENARIOS.items(), key=lambda x: x[0]):
        scenario_tokens = 0
        file_count = 0
        for p in paths:
            full = ROOT / p
            if full.exists():
                scenario_tokens += count_tokens(full.read_text(encoding="utf-8"))
                file_count += 1
        print(f"  {name:<40} {file_count:>5} {scenario_tokens:>8}")

    # Grand total
    grand = sum(f["tokens"] for f in all_files)
    grand_lines = sum(f["lines"] for f in all_files)
    print(f"\n{'=' * 70}")
    print(f"  GRAND TOTAL: {len(all_files)} files, {grand_lines:,} lines, {grand:,} tokens")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
