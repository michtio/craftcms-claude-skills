# evals/

Token-budget and trigger-quality tooling for this plugin's 13 skills and 6
agents. Nothing in here ships to users — it's measurement and regression
tooling for whoever edits `skills/*/SKILL.md` or `agents/*.md`.

## What each tool measures

| Tool | Question it answers | Makes model calls? |
|---|---|---|
| `measure_tokens.py` | How many tokens does each skill cost — split into the always-loaded listing (paid every session) vs the on-demand SKILL.md/references (paid only when triggered)? What does each agent preload? | No |
| `trigger-sets/*.json` | Fixtures: realistic queries per skill, each labeled `should_trigger: true/false`. Not a tool by itself — input to the two below. | No |
| `route.py` | Forced-choice routing: given ONLY a skill's listing text (description + when_to_use), isolated from the real installed skill set, which skill does the model pick for each query? A/B-able across two git refs. | **Yes** |
| `trigger_check.py` | Real-world recall/precision: with the actual installed production skill set (all plugins, no isolation), does a given skill's `Skill` tool call actually fire for each query? | **Yes** |

`route.py` and `trigger_check.py` answer related but different questions.
`route.py` is a controlled instrument — good for "did rewriting this
description help or hurt, holding everything else constant." `trigger_check.py`
is the uncontrolled ground truth — good for "does this actually fire for a
real user, competing against everything else installed," at the cost of only
checking one skill at a time and needing the real plugin installed locally.

## How to run them

### Token budget

```bash
# Human-readable report
uv run --with tiktoken python3 evals/measure_tokens.py

# Machine-readable snapshot
uv run --with tiktoken python3 evals/measure_tokens.py --json > evals/snapshot-$(date +%F).json

# Diff against a prior snapshot
uv run --with tiktoken python3 evals/measure_tokens.py --compare evals/snapshot-2026-05-04-post.json
```

Frontmatter (`description`, `when_to_use`, an agent's `skills:` field) is
parsed via the system `ruby` interpreter — the same parser
`bin/validate-skills.sh` uses — not a Python YAML library, since this host
has no `pyyaml` and ruby is already a hard requirement for this repo's
tooling (ships with macOS and every GitHub ubuntu runner). This keeps the
documented `uv run --with tiktoken python3 ...` invocation unchanged; no
extra `--with` flags needed.

### Trigger fixtures

Each `trigger-sets/<skill>.json` is a flat array: `[{"query": "...", "should_trigger": true|false}, ...]`.
Positives should exercise *real* coverage from the skill's SKILL.md body, not
just restate its trigger-word list verbatim. Negatives should be near-misses
that genuinely belong to a sibling skill (e.g. a Servd query for the
craft-cloud set, a craftcms-core query for the craft-plugins set) — a
negative that isn't tempting proves nothing.

`craft-pest.json` is a merge of the three original rounds documented in
`craft-pest-workspace/EVAL-NOTES.md` (trigger-eval, addendum, tail), plus one
item moved over from the ddev set (see below) — 37 items total, not the
~16-per-skill size of the others, since it absorbed three historical rounds.

### Routing harness (route.py)

```bash
# ALWAYS dry-run a new invocation first — zero model calls, verifies setup
python3 evals/route.py --dry-run
python3 evals/route.py --dry-run --compare-ref main

# A/B: does a description rewrite on the working tree route better than main?
python3 evals/route.py --compare-ref main --runs 2 --workers 10

# Single condition, narrowed to one trigger set via a temp sets dir, full
# per-query output written to a file
python3 evals/route.py --sets evals/trigger-sets --out evals/route-results.json
```

Cost note: 13 skills x ~16-18 queries/skill x `--runs` x (1 or 2 conditions)
`claude -p` calls. At the default `--runs 1`, single-condition that's ~230
calls; `--compare-ref` doubles it. Budget accordingly, and prefer `--runs 1`
for a quick check, `--runs 2`+ only when you need to smooth model noise (see
Known Pitfalls below).

### Single-skill production recall check (trigger_check.py)

```bash
python3 evals/trigger_check.py evals/trigger-sets/craft-pest.json --target craft-pest
```

Run in the **foreground** — backgrounding it has produced empty output
before. Expect several minutes for ~20-30 queries at the default 5 workers.

## How to read results

- **route.py** prints `pass/total` overall and per-skill. A query "passes" if:
  a positive's chosen skill matches the set's skill, or a negative's chosen
  skill does *not* match. `--compare-ref` adds an A/B delta table — read the
  per-skill rows, not just the overall number, since a wash in total score
  can hide a regression in one skill offset by a gain in another.
- **trigger_check.py** prints `recall` (how many of the positives actually
  fired the target skill) and `precision_negatives_correct` (how many
  negatives correctly stayed quiet) separately, since they fail for
  different reasons: low recall means the description's trigger words don't
  cover real phrasing; a negative miss means the description is too eager
  and is stealing queries that belong to a sibling skill.
- **measure_tokens.py --compare** sorts by absolute token delta, descending,
  so the biggest movers are at the top regardless of whether they're a new
  skill or growth in an existing one. A skill with no `old_tokens` is new
  since that snapshot, not a regression.

## Known pitfalls

- **skill-creator's own `scripts/run_eval.py` cannot be used in this repo.**
  It synthesizes a throwaway slash command and scores a trigger only if the
  model's *first* tool call is `Skill`/`Read` naming that command's uuid.
  Because the real skills here are installed globally (symlinked into
  `~/.claude/skills` **and** registered via the plugin), the model calls the
  *real* skill instead, whose name lacks the uuid, and the harness scores a
  false negative on every query — confirmed with a control run against a
  mature skill (craft-garnish) and a near-verbatim copy of its own README
  example prompt, which also scored 0. `route.py` and `trigger_check.py`
  exist specifically to work around this.
- **Installed-skill isolation matters.** `route.py`'s whole design is built
  around disabling the real installed plugin (`enabledPlugins` + 13x
  `skillOverrides: "off"`) so only the synthesized `-x` commands' listing
  text competes. Forgetting this (e.g. hand-rolling a similar script without
  the settings.json) means the model routes to the real skill every time,
  regardless of what listing text you're trying to test.
- **The user's own CLAUDE.md can bias answers toward one skill.** A global
  `CLAUDE.md` with strong Craft-PHP conventions has been observed nudging
  ambiguous queries toward `craft-php-guidelines` in forced-choice routing
  tests, independent of description quality. If a skill's route.py score
  looks suspiciously strong, check whether the query is genuinely
  PHP-shaped or whether it's picking up this bias.
- **The 1,536-character listing window is a real cliff, not a soft guideline.**
  Claude Code concatenates `description + " - " + when_to_use` and truncates
  the combined text in the always-loaded skill listing beyond 1,536
  characters (`bin/validate-skills.sh` enforces this at CI time). A
  description that reads fine in the file can have its tail silently
  dropped from routing consideration. `measure_tokens.py`'s "ALWAYS-LOADED
  SKILL LISTING" table reports `listing_chars` per skill — watch it stay
  under 1,536 on every edit, not just under the 1,024-char `description`-only
  cap.
- **Sonnet is noisy at low `--runs`.** The same query against the same
  listing text can flip between two adjacent skills (or a skill and NONE)
  across repeated calls, especially for genuinely ambiguous queries near a
  skill boundary. `--runs 1` is fine for a quick sanity check; treat a
  single-run regression in an A/B comparison as a hypothesis, not a verdict
  — rerun with `--runs 2` or more before concluding a description rewrite
  actually hurt.
- **The ddev → craft-pest crossover item.** "I need to write a GitHub Actions
  workflow that runs PHPStan and Pest tests on every pull request" is a
  correct negative for `ddev` (it's not a local-dev question) and was added
  as a positive to `craft-pest.json` since it falls under that skill's "CI
  jobs" / "no CI Pest job" coverage. `craft-pest-workspace/EVAL-NOTES.md`
  documents that near-identical CI-workflow phrasing has historically *not*
  triggered any skill in practice (the model answers GitHub Actions YAML
  confidently unaided) — kept as a should_trigger:true fixture anyway,
  since it tests intended coverage, not a currently-passing assertion.

## Files

- `measure_tokens.py` — token budget measurement (see above)
- `route.py` — forced-choice routing harness, A/B-able across git refs
- `trigger_check.py` — single-skill recall/precision check against the real installed skill set
- `trigger-sets/*.json` — fixtures, one file per skill, `[{query, should_trigger}, ...]`
- `snapshot-2026-05-04.json`, `snapshot-2026-05-04-post.json` — historical token snapshots (8 skills, pre-expansion)
- `snapshot-2026-10-05.json` — current token snapshot (13 skills); May→Oct total grew 251,863 → 466,944 tokens (+85%), roughly half from 5 new skills (craft-cloud, craft-pest, craft-plugin-release, craft-plugins, servd) and half from growth in the original 8

Run artifacts (`results*.json`, `route-results*.json`, `baseline.txt`, `*.log`)
are gitignored — only the fixtures and tooling above are tracked.
