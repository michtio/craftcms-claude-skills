#!/usr/bin/env python3
"""Startup budget for the pack's agents (R11).

An agent starts with its own file plus every skill in its `skills:` frontmatter
preloaded in full. Startup bytes = agents/<agent>.md + skills/<s>/SKILL.md for
each preloaded skill; the budget is 48 KB (~12K tokens at ~4 bytes per token).
Skills not preloaded are loaded on demand with the Skill tool.

Usage:
    python3 bin/agent_budget.py           # table; exit 1 if any agent is over budget

Python 3.9+, standard library only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUDGET = 48 * 1024


def preloads(agent: Path) -> list[str]:
    head = agent.read_text(encoding="utf-8").split("\n---", 1)[0]
    m = re.search(r"^skills:\s*(.+)$", head, re.M)
    return [s.strip() for s in m.group(1).split(",") if s.strip()] if m else []


def main() -> int:
    over = 0
    for agent in sorted((REPO / "agents").glob("*.md")):
        skills = preloads(agent)
        sizes = {s: (REPO / "skills" / s / "SKILL.md").stat().st_size for s in skills}
        total = agent.stat().st_size + sum(sizes.values())
        flag = "ok  " if total <= BUDGET else "OVER"
        over += total > BUDGET
        parts = ", ".join(f"{s} {b / 1024:.1f}" for s, b in sizes.items())
        print(f"{flag} {agent.stem:26} {total / 1024:5.1f} KB (~{total // 4 // 1000}K tokens) = "
              f"agent {agent.stat().st_size / 1024:.1f} + {parts or 'no preloads'}")
    print(f"budget {BUDGET // 1024} KB per agent; {over} over")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
