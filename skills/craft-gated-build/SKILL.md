---
name: craft-gated-build
description: "Builds one approved slice with the outside builders listed in .ai/skills-profile.json (local AI, a script) and keeps the pack's gates: craft-gate-writer locks the gate ahead of any builder, each builder gets a brief and returns a handback, the handback is verified, the lock and craft-review-checker cover the result, at most three rounds, and craft-feature-builder takes over when every outside builder fails, is unavailable or passes its timeout setting."
when_to_use: "Use only when .ai/skills-profile.json names builders. Triggers on: outside builder, local AI builder, builders list, brief, handback, unavailable builder, timeout_minutes, builder fallback. Not for a build without a profile naming builders (craftcms)."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Gated Build with Outside Builders

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, read `craftcms/cms` from `composer.lock` (site) or the lowest version the `craftcms/cms` constraint in `composer.json` allows (plugin). The brief needs it.

The main session runs this procedure for one slice. It is the 1.31.0 gate flow (gate writer, lock check, checker gate, 3-round cap) with the build step handed to the outside builders the profile names, in order, and `craft-feature-builder` as the last builder. The protocol the builders follow is `docs/outside-builders.md`; the brief and hand-back formats are `docs/brief-format.md`. Both are in the pack, next to this skill: `${CLAUDE_SKILL_DIR}/../../docs/`.

Pack scripts (standard library Python), found from this skill's folder:
- `${CLAUDE_SKILL_DIR}/../../bin/profile_check.py <profile>`
- `${CLAUDE_SKILL_DIR}/../../bin/run_builder.py` (runs one builder with its timeout)
- `${CLAUDE_SKILL_DIR}/../../bin/handback_check.py --brief <brief> <handback>`

Never stop silently. Every skip, failure, fallback and skipped gate goes in the report.

## 1. Preconditions

Check all of these before anything starts:

1. **Spec gate.** The PRD and the plan are both `status: approved`, the slice exists, and you have its R ids with their acceptance criteria verbatim. Missing or unapproved: stop and report what is missing (as `craft-feature-builder` would).
2. **Profile.** `.ai/skills-profile.json` exists, `profile_check.py` exits 0 on it, and `builders` has at least one entry. Read `gate_tests` and each builder's `name`, `command` and `timeout_minutes` (missing: 30).
3. **Gate flow.** Locked when all hold: `tests/Pest.php` exists, `phpunit.xml.dist` pins `CRAFT_DB_DATABASE`, the project's `CLAUDE.md` has no `Gate tests: builder-written` line, and the profile's `gate_tests` is not `builder-written`. Otherwise builder-written, with the reason.
4. **Project facts from `CLAUDE.md`.** The Pest command exactly as `CLAUDE.md` gives it (for example `ddev exec --dir <plugin-root> vendor/bin/pest`, or plain `vendor/bin/pest` when it says there is no DDEV project), the project root (absolute path), and any gate it says to skip. A gate you skip is named in the report with the reason.
5. **Clean tree.** `git status --short` is empty. Otherwise stop and report: the resets below would discard that work.

No profile, an invalid profile or no builders: this procedure does not apply. Behave exactly as 1.31.0: start `craft-feature-builder` with the usual slice brief (it starts its own gate writer), and say why in one line.

## 2. Gate tests first

Locked flow only. Start `craft-gate-writer` (`craftcms-claude-skills:craft-gate-writer` when the pack is a plugin: use the name your agent list shows) before any implementation. Its brief, nothing else: the slice id, the R ids with their acceptance criteria copied verbatim from the PRD, the Craft version, the plugin root and the Pest command from step 1 (when `CLAUDE.md` says to run it without DDEV, say so, and point it to `CLAUDE.md` for any test conventions). No design, no class names you plan, no hints. Pass no `model`.

When it returns, confirm: `git log -1 --format=%s` is `test(gate): <slice id>`, and `git show --name-only --format= HEAD` lists only files under `tests/`. Record the short hash as `<gate commit>` and the files as `<gate files>`. Keep its `| AC | test | red reason |` table for the report.

Builder-written flow: no gate writer; the brief says `Gate commit: none`.

## 3. The brief file

Make a work folder outside the project root, so the resets below never touch it: `mktemp -d` (call it `<work>`). Write `<work>/brief.md` per `docs/brief-format.md`:

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

- <absolute path of the pack>/skills/craftcms/SKILL.md
- <the project's CLAUDE.md, and the skill references the slice needs>

## Rules

- Never edit a gate file.
- Stop at a passing gate.
- At most 3 rounds.
```

Write pack paths in the brief as absolute paths (resolve `${CLAUDE_SKILL_DIR}/../..`), so a builder outside this session can read them. Add the slice's scope (its deliverable and layers from the plan) as plain text under the title. The same brief serves every builder, `craft-feature-builder` included.

## 4. Builders, in profile order

### Before each builder: reset

Every builder starts from the same clean slice, so a failed builder leaves nothing behind:

1. `<base>` is `<gate commit>` (locked) or the HEAD you recorded before step 3 (builder-written).
2. Inside the project root only: `git reset --hard <base>` and `git clean -fd`.
3. Delete the old hand-back: `rm -f <work>/handback-<name>.md`.

Never reset during one builder's own fix rounds: it fixes on top of its own work.

### Run it

```
python3 ${CLAUDE_SKILL_DIR}/../../bin/run_builder.py --cwd <project root> \
  --timeout-minutes <timeout_minutes> --command '<command>' \
  <work>/brief.md <work>/handback-<name>.md
```

It runs `<command> <brief> <handback>` from the project root and kills the whole process tree at the timeout. Under 9 minutes: run it in the foreground with a Bash timeout above `timeout_minutes`. Longer: run it in the background and wait for the completion notice, without polling.

### Act on the exit code

| Exit | Meaning | Next |
|---|---|---|
| 0 | done, hand-back written | hand-back check (step 5) |
| 3 | unavailable | record `<name> (exit 3, unavailable)`, next builder at once |
| 124 or `builder exit: timeout` | timed out | record `<name> (timeout)`, next builder |
| any other | failed | record `<name> (exit <n>, failed)`, next builder |

## 5. Hand-back check

```
python3 ${CLAUDE_SKILL_DIR}/../../bin/handback_check.py --brief <work>/brief.md <work>/handback-<name>.md
```

Exit 0: continue. Exit 1 or 2 (a line missing, bad or duplicated, or no file): the hand-back is not a pass. Send the checker's messages back to the same builder as a round (step 8). The hand-back is a claim, not evidence: steps 6 and 7 verify it.

## 6. Gate and lock check, rerun by you

1. Run the Pest command from the project root. It must be green.
2. Locked flow: run both forms and record each exit code (0 means untouched):
   - `git diff --quiet <gate commit> HEAD -- <gate files>` (committed)
   - `git diff --quiet <gate commit> -- <gate files>` (working tree against the gate commit)

In general form, the working-tree check is `git diff --quiet <gate commit> -- <gate files>`. A nonzero lock code means a gate file changed: the builder broke the main rule. Record it, reset, and go to the next builder. A red gate, or an `R<n>:` line that is not `PASS`: a round for the same builder (step 8), with the failing output.

## 7. Checker gate

Size the builder's diff as `craft-feature-builder` does (the 1.30.0 rule): `git diff --numstat <base>` for changed lines, `git diff <base>` for what it touches. Sensitive: controllers or actions, permission or access checks, request input, migrations, `|raw` or `attr()` output, MCP tools or OAuth, `config/` files.

- 50 lines or more: security and conventions, in one checker.
- Under 50 lines, anything sensitive: security lens only.
- Under 50 lines, nothing sensitive: conventions lens only. An outside builder's work always gets one checker, since no checker ran inside its build.

Start `craft-review-checker` (`craftcms-claude-skills:craft-review-checker` when the pack is a plugin) with the lens brief(s) from `craft-feature-builder`'s checker gate, the Craft version, the changed files with `git diff <base>...HEAD -- <files>`, and the static-check results (or "not run" with the reason, such as no DDEV project). Pass no `model`. At most 4 agents per slice: the gate writer, the checker and up to two re-checks.

Critical: a round for the same builder (step 8), then one re-check on the fix. Important: send it in the same round when there is one, or list it with the reason. Suggestions: list only.

## 8. Fix rounds

A round sends the problems back to the same builder: append `## Findings (round <n>)` to `<work>/brief.md` with the checker's messages, the red gate output or the Critical findings, delete the old hand-back, and run the same command again (no reset). Then steps 5 to 7 again.

Stop after 3 rounds. When the hand-back check, the gate or a lock check still fails after round 3, reset and go to the next builder. When only checker findings stay open after round 3, stop and report them open: the slice is not passed.

## 9. Fallback: craft-feature-builder

When every outside builder failed, timed out or was unavailable, reset (as before each builder) and start `craft-feature-builder` (`craftcms-claude-skills:craft-feature-builder` when the pack is a plugin) with the same brief: the spec paths, the slice, its R ids and acceptance criteria, and `<work>/brief.md`. In the locked flow, tell it the gate commit `<gate commit>` with `<gate files>` already exists, written by `craft-gate-writer`: it builds against that commit in the locked flow and starts no second gate writer. Pass no `model`. It runs its own checker gate and round caps.

After it returns, rerun step 6 yourself. When its hand-back says `Checker: not run`, run step 7 on its diff.

Never let the fallback end silently: the report says that all outside builders failed or were unavailable, with each exit code, and that `craft-feature-builder` continued from the same brief.

## 10. Report

Write the report in this shape, one item per line, plain text:

```
Gate flow: locked (<gate commit>)
Builder: <name of the builder whose work passed, or craft-feature-builder>
Skipped: <name> (exit 3, unavailable); <name> (exit 1, failed); <name> (timeout) | none
Fallback: all outside builders failed or were unavailable; craft-feature-builder continued from the same brief | none
Hand-back check: exit <n> (<pass, or the messages>)
Gate: <Pest command> <green or red> (<counts>)
Lock check (committed): exit <n>
Lock check (working tree): exit <n>
R<n>: PASS|FAIL|PENDING  <acceptance criterion> | <evidence>
Checker: <lens: conventions | security | security + conventions> · agents: <n> · fixed: <...> · open Important: <...>
Rounds: <n> of 3
Skipped gates: <gate> (<reason>) | none
```

Add the gate writer's `| AC | test | red reason |` table, any disputed gate test with its line and reason, and the open findings. In the builder-written flow, the gate flow line is `Gate flow: builder-written (<reason>)` and the lock lines are omitted.

A slice passes only when every `R<n>` is `PASS`, the hand-back check passed, the gate is green under your own run, and both lock checks are `exit 0`. Passing means ready for review, never done: marking it done is the user's call.
