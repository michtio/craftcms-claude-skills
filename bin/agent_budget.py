#!/usr/bin/env python3
"""Startup budget for the pack's agents (R11).

An agent starts with its own file plus every skill in its `skills:` frontmatter
preloaded in full. Startup bytes = agents/<agent>.md + skills/<s>/SKILL.md for
each preloaded skill; the budget is 48 KB (~12K tokens at ~4 bytes per token).
Skills not preloaded are loaded on demand with the Skill tool.

Deep-review team rules (spec 2026-11-26-deep-review-team, R7):
  - craft-review-checker starts under 16 KB (it runs once per lens);
  - craft-code-reviewer-deep preloads nothing (it orchestrates, loads on demand);
  - no reviewer or checker agent uses effort: xhigh.

Agent caps (spec 2026-11-26-agent-caps-builder-gate, R1-R3):
  - an agent without Agent in `tools` has cap 0;
  - an agent with Agent declares `At most N agents per <run|review>`, N <= 5;
  - craft-review-checker never has Agent (teams do not nest further).

Usage:
    python3 bin/agent_budget.py                 # table; exit 1 on any violation
    python3 bin/agent_budget.py --agents DIR    # check another agents/ directory (self-test)

Python 3.9+, standard library only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUDGET = 48 * 1024
CAPS = {"craft-review-checker": 16 * 1024}
NO_PRELOAD = {"craft-code-reviewer-deep"}
NO_AGENT = {"craft-review-checker"}
MAX_AGENTS = 5
CAP_LINE = re.compile(r"At most (\d+) agents per (?:run|review)\b")


def preloads(agent: Path) -> list[str]:
    head = agent.read_text(encoding="utf-8").split("\n---", 1)[0]
    m = re.search(r"^skills:\s*(.+)$", head, re.M)
    return [s.strip() for s in m.group(1).split(",") if s.strip()] if m else []


def effort(agent: Path) -> str:
    head = agent.read_text(encoding="utf-8").split("\n---", 1)[0]
    m = re.search(r"^effort:\s*(\S+)", head, re.M)
    return m.group(1) if m else ""


def tools(agent: Path) -> set[str]:
    head = agent.read_text(encoding="utf-8").split("\n---", 1)[0]
    m = re.search(r"^tools:\s*(.+)$", head, re.M)
    return {t.strip() for t in m.group(1).split(",")} if m else set()


def agent_cap(agent: Path) -> tuple[str, list[str]]:
    """Return (cap label, problems) for the agent-start rules."""
    if "Agent" not in tools(agent):
        return "cap 0", []
    if agent.stem in NO_AGENT:
        return "cap ?", ["must not have the Agent tool"]
    caps = [int(n) for n in CAP_LINE.findall(agent.read_text(encoding="utf-8"))]
    if not caps:
        return "cap ?", ["Agent tool without an 'At most N agents per run|review' line"]
    if max(caps) > MAX_AGENTS:
        return f"cap {max(caps)}", [f"cap above {MAX_AGENTS}"]
    return f"cap {max(caps)}", []


def main() -> int:
    agents_dir = Path(sys.argv[sys.argv.index("--agents") + 1]) if "--agents" in sys.argv else REPO / "agents"
    over = 0
    for agent in sorted(agents_dir.glob("*.md")):
        skills = preloads(agent)
        sizes = {s: (REPO / "skills" / s / "SKILL.md").stat().st_size for s in skills}
        total = agent.stat().st_size + sum(sizes.values())
        cap = CAPS.get(agent.stem, BUDGET)
        cap_label, problems = agent_cap(agent)
        if total > cap:
            problems.append(f"over {cap // 1024} KB")
        if agent.stem in NO_PRELOAD and skills:
            problems.append("must not preload skills")
        if ("reviewer" in agent.stem or "checker" in agent.stem) and effort(agent) == "xhigh":
            problems.append("reviewer agents use effort high, not xhigh")
        flag = "ok  " if not problems else "FAIL"
        over += bool(problems)
        parts = ", ".join(f"{s} {b / 1024:.1f}" for s, b in sizes.items())
        print(f"{flag} {agent.stem:26} {cap_label}  {total / 1024:5.1f} KB (~{total // 4 // 1000}K tokens) = "
              f"agent {agent.stat().st_size / 1024:.1f} + {parts or 'no preloads'}"
              + (f"  <- {'; '.join(problems)}" if problems else ""))
    print(f"budget {BUDGET // 1024} KB per agent (checker {CAPS['craft-review-checker'] // 1024} KB); at most {MAX_AGENTS} agents started; {over} failing")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
