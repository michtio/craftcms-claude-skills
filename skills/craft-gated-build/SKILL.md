---
name: craft-gated-build
description: "Builds one approved slice with the outside builders listed in .ai/skills-profile.json (local AI, a script) and keeps the pack's gates: craft-gate-writer locks the gate ahead of any builder, each builder gets a brief and returns a handback, the handback is verified, the lock and craft-review-checker cover the result, at most three rounds, and craft-feature-builder takes over when every outside builder fails, is unavailable or passes its timeout setting."
when_to_use: "Use only when .ai/skills-profile.json names builders. Triggers on: outside builder, local AI builder, builders list, brief, handback, unavailable builder, timeout_minutes, builder fallback. Not for a build without a profile naming builders (craftcms). Not for project setup that reads the profile (craft-project-setup)."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Gated Build with Outside Builders

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, read `craftcms/cms` from `composer.lock` (site) or the lowest version the `craftcms/cms` constraint in `composer.json` allows (plugin). The brief needs it.

The main session runs this for one slice: the 1.31.0 gate flow (gate writer, lock check, checker gate, 3-round cap) with the build handed to the profile's outside builders, in order, and `craft-feature-builder` last. Protocol: `docs/outside-builders.md`; brief and hand-back formats: `docs/brief-format.md`, both in `${CLAUDE_SKILL_DIR}/../../docs/`.

Pack scripts, found from this skill's folder (`<pack>` is `${CLAUDE_SKILL_DIR}/../..`):
- `<pack>/bin/profile_check.py <profile>`
- `<pack>/bin/run_builder.py` (one builder with its timeout)
- `<pack>/bin/handback_check.py --brief <brief> <handback>`

Never stop silently. Every skip, failure, fallback and skipped gate goes in the report.

## 1. Preconditions

1. **Spec gate.** PRD and plan both `status: approved`, the slice exists, and you have its R ids with their acceptance criteria verbatim. Otherwise stop and report what is missing.
2. **Profile.** `.ai/skills-profile.json` exists, `profile_check.py` exits 0 on it, and `builders` has an entry. Read `gate_tests` and each builder's `name`, `command` and `timeout_minutes` (missing: 30).
3. **Pack scripts.** When the bin/ scripts above are missing, for example in an install that links only skill folders, behave as 1.31.0 and say why.
4. **Gate flow.** Locked when `tests/Pest.php` exists, `phpunit.xml.dist` pins `CRAFT_DB_DATABASE`, `CLAUDE.md` has no `Gate tests: builder-written` line and the profile's `gate_tests` is not `builder-written`. Otherwise builder-written, with the reason.
5. **From `CLAUDE.md`.** The Pest command exactly as given (`ddev exec --dir <plugin-root> vendor/bin/pest`, or plain `vendor/bin/pest` when it says there is no DDEV project), the absolute project root, and any gate to skip (named in the report with the reason).
6. **Clean tree.** `git status --porcelain --untracked-files=all` is empty; otherwise stop and report, since the resets would discard that work. Record the branch (`git rev-parse --abbrev-ref HEAD`).

No profile, an invalid one or no builders: behave exactly as 1.31.0, start `craft-feature-builder` with the usual slice brief (it starts its own gate writer), and say why in one line.

Before the first builder, tell the user not to edit the repository during the run: the resets below discard any change.

## 2. Gate tests first

Locked flow only. Start `craft-gate-writer` (`craftcms-claude-skills:craft-gate-writer` when the pack is a plugin: use the name your agent list shows) before any implementation. Its brief, nothing else: the slice id, the R ids with their acceptance criteria verbatim from the PRD, the Craft version, the plugin root and the Pest command (when `CLAUDE.md` says to run it without DDEV, say so and point to `CLAUDE.md` for test conventions). No design, planned class names or hints. Pass no `model`.

Then confirm `git log -1 --format=%s` is `test(gate): <slice id>` and `git show --name-only --format= HEAD` lists only files under `tests/`. Record `<gate commit>` (short hash) and `<gate files>`, and keep its `| AC | test | red reason |` table.

Builder-written flow: no gate writer, and the brief says `Gate commit: none`.

## 3. The brief file

Make a work folder outside the project root, so resets never touch it: `mktemp -d` (`<work>`). Write `<work>/brief.md` per `docs/brief-format.md`:

```
# Brief: <slice id> <slice title>

Slice: <slice id>
Project root: <absolute project root>
Craft version: <x.y.z>
Gate commit: <gate commit, or none>
Gate files: <gate files, space separated>
Pest command: <Pest command from CLAUDE.md>

## R<n>

<requirement text, verbatim>
AC<n>: <Given/When/Then, verbatim>

## Pointers

- <absolute pack path>/skills/craftcms/SKILL.md
- <the project's CLAUDE.md and the skill references the slice needs>

## Rules

- Never edit a gate file.
- Stop at a passing gate.
- At most 3 rounds.
- Commit your work before writing the hand-back.
```

Write pack paths as absolute paths so a builder outside this session can read them. Add the slice's deliverable and layers from the plan under the title. Every builder gets the same brief.

## 4. Builders, in profile order

### Before each builder: reset

1. `<base>` is `<gate commit>` (locked) or the HEAD recorded before step 3 (builder-written).
2. Check the branch is still the one recorded in step 1; if it changed, stop and report.
3. `git reset --hard <base>` affects the whole repository; `git clean -fd` runs from the project root and cleans only below it. Then `git status --porcelain --untracked-files=all` must be empty.
4. `rm -f <work>/handback-<name>.md`.

Never reset during one builder's fix rounds: it fixes on top of its own work.

### Run it

```
python3 <pack>/bin/run_builder.py --cwd <project root> --timeout-minutes <timeout_minutes> \
  --command '<command>' --log <work>/log-<name>.txt <work>/brief.md <work>/handback-<name>.md
```

It runs `<command> <brief> <handback>` from the project root and kills the whole process tree at the timeout. Under 9 minutes: foreground, with a Bash timeout above `timeout_minutes`. Longer: background, and wait for the completion notice without polling.

| Exit | Meaning | Next |
|---|---|---|
| 0 | done | steps 5 to 7 |
| 3 | unavailable | record `<name> (exit 3, unavailable)`, next builder |
| 124 or `builder exit: timeout` | timed out | record `<name> (timeout)`, next builder |
| 64 | `run_builder.py` usage error | fix the call and rerun; never a builder result |
| other | failed | record `<name> (exit <n>, failed)`, next builder |

In a fix round, exit 3, a timeout or any other nonzero exit ends that builder: record it, reset, next builder.

## 5. Right after every exit 0

In every round, in this order:

1. **Lock check, before the hand-back check** (locked flow). Run both and record each exit code:
   - `git diff --quiet <gate commit> HEAD -- <gate files>` (committed)
   - `git diff --quiet <gate commit> -- <gate files>` (working tree against the gate commit)

   The general form of the second is `git diff --quiet <gate commit> -- <gate files>`. Nonzero disqualifies the builder: record `<name> (lock check failed)`, reset, next builder.
2. **Committed work.** `git status --porcelain --untracked-files=all` must be empty. Otherwise a round: "Commit your work before writing the hand-back."
3. **Hand-back check:** `python3 <pack>/bin/handback_check.py --brief <work>/brief.md <work>/handback-<name>.md`. Exit 1 or 2 (a line missing, bad or duplicated, or no file) is not a pass: a round with its messages.
4. **Gate, rerun by you.** Run the Pest command from the project root. A red gate, or an `R<n>:` line that is not `PASS`: a round with the failing output. The hand-back is a claim, not evidence.

## 6. Checker gate

Size the builder's commits as `craft-feature-builder` does (the 1.30.0 rule): `git diff --numstat <base>..HEAD` for changed lines, `git diff <base>..HEAD` for what it touches. Sensitive: controllers or actions, permission or access checks, request input, migrations, `|raw` or `attr()` output, MCP tools or OAuth, `config/` files.

- 50 lines or more: security and conventions, in one checker.
- Under 50 lines, anything sensitive: security lens only.
- Under 50 lines, nothing sensitive: conventions lens only.

Overrides the 1.30.0 skip: outside-builder work always gets a checker (no checker ran in its build).

Start `craft-review-checker` (`craftcms-claude-skills:craft-review-checker` when the pack is a plugin) with the lens brief(s) from `craft-feature-builder`'s checker gate, the Craft version, the changed files with `git diff <base>..HEAD -- <files>`, and the static-check results (or "not run" with the reason). Pass no `model`.

Agent cap: 4 per builder (the checker and up to two re-checks, plus the gate writer, counted once for the slice). At the cap, stop and report the open findings: the slice is not passed.

Critical: a round, then one re-check on the fix. Important: send it in the same round when there is one, or list it with the reason. Suggestions: list only.

## 7. Fix rounds

A round sends the problems back to the same builder: append `## Findings (round <n>)` to `<work>/brief.md` (dirty files, hand-back messages, red gate output or Critical findings), delete the old hand-back, and run the same command again with no reset. Then step 5, and step 6 for a re-check.

3 rounds per builder; the count restarts for the next. Stop after 3 rounds: when the tree, the hand-back or the gate still fails, record `<name> (3 rounds, gate red)`, reset and go to the next builder. When only checker findings stay open, stop and report them: the slice is not passed.

## 8. Fallback: craft-feature-builder

When every outside builder failed, timed out, was unavailable or was disqualified, reset and start `craft-feature-builder` (`craftcms-claude-skills:craft-feature-builder` when the pack is a plugin) with the spec paths, the slice, its R ids and acceptance criteria, and `<work>/brief.md`. Locked flow: give it the gate commit `<gate commit>` and gate files `<gate files>`, written by `craft-gate-writer`, so it builds against them and starts no second gate writer. Pass no `model`. It runs its own checker gate and round caps.

When it returns, write craft-feature-builder's hand-back lines to a file, `<work>/handback-craft-feature-builder.md`, and run `<pack>/bin/handback_check.py` on that file. Then run step 5's lock check and gate yourself. When its hand-back says `Checker: not run` or `skipped`, run step 6 on its commits.

The report says that all outside builders failed or were unavailable, with each exit code, and that `craft-feature-builder` continued from the same brief.

## 9. Report

One item per line, plain text:

```
Gate flow: locked (<gate commit>)
Builder: <the builder whose work passed, or craft-feature-builder>
Skipped: <name> (exit 3, unavailable); <name> (exit 1, failed); <name> (timeout); <name> (lock check failed); <name> (3 rounds, gate red) | none
Fallback: all outside builders failed or were unavailable; craft-feature-builder continued from the same brief | none
Hand-back check: exit <n> (<pass, or the messages>)
Gate: <Pest command> <green or red> (<counts>)
Lock check (committed): exit <n>
Lock check (working tree): exit <n>
R<n>: PASS|FAIL|PENDING  <acceptance criterion> | <evidence>
Checker: <conventions | security | security + conventions> · agents: <n> · fixed: <...> · open Important: <...>
Rounds: <n> of 3
Skipped gates: <gate> (<reason>) | none
```

Add the gate writer's table, any disputed gate test with its line and reason, and open findings. Builder-written flow: `Gate flow: builder-written (<reason>)`, no lock lines.

A slice passes only when every `R<n>` is `PASS`, the hand-back check passed, the gate is green under your own run and both lock checks are `exit 0`. Passing means ready for review, never done: that is the user's call.
