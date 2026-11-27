# S2 gate contract: brief and hand-back formats, hand-back checker, lock-check fix

Spec: extension-points PRD R3, R8; AC3; plan AD3, AD5, AD6, slice S2, plus the
lock-check defect fix. The builder makes every item below hold and does not edit
the fixtures, `evals/tests/test_ext_s2.py` or the facts pins in
`evals/behavior-sets/agents.json`. Run the tests with
`python3 -m unittest discover -s evals/tests -p 'test_ext_s2.py' -v`.

## 1. Interface

`python3 bin/handback_check.py --brief <brief> <handback>` (standard library only).

| Exit | Meaning |
|---|---|
| 0 | the hand-back is well formed (prints nothing required) |
| 1 | a required line is missing or bad (one message per problem, on stdout or stderr) |
| 2 | usage error: no `--brief`, no hand-back argument, an unreadable file, or a brief with no R ids |

The checker validates form only. Whether the slice passed (every R id `PASS`) is
the build's decision; a `FAIL` or `PENDING` line is well formed.

## 2. Required hand-back lines (each on its own line, at line start, plain text)

| Line | Format (regex) |
|---|---|
| Gate flow | `^Gate flow: (locked \((<sha>)\)\|builder-written \((<reason>)\))$`, `<sha>` is 7 to 40 hex characters, `<reason>` is non-empty |
| Lock check, committed | `^Lock check \(committed\): exit (\d+)$`, the exit code of `git diff --quiet <gate commit> HEAD -- <gate files>` |
| Lock check, working tree | `^Lock check \(working tree\): exit (\d+)$`, the exit code of `git diff --quiet <gate commit> -- <gate files>` |
| One per R id in the brief | `^R<n>: (PASS\|FAIL\|PENDING)$` |
| Builder | `^Builder: \S.*$`, the builder's name |

- Both Lock check lines are required when the flow is `locked`. With
  `builder-written` they are not required (there is no gate commit).
- The R ids to expect are the headings `## R<n>` in the brief (level 2 to 4).
- The same line shapes as `agents/craft-feature-builder.md` (`Gate flow: ...`).

## 3. Fixtures and expected output

`brief.md` lists R2 and R5. `complete.md` exits 0. Each broken fixture exits 1 and
the output contains the substring:

| Fixture | Rule broken | Substring in output |
|---|---|---|
| `missing-lock-line.md` | no working-tree lock line | `missing line: Lock check (working tree)` |
| `missing-gate-flow.md` | no Gate flow line | `missing line: Gate flow` |
| `missing-r-line.md` | no R5 line | `missing line: R5` |
| `bad-status.md` | `R2: DONE` | `bad status: R2` |
| `missing-builder.md` | no Builder line | `missing line: Builder` |
| `lock-nonzero.md` | committed lock exit 1 | `gate touched` |

Exit 2: no arguments; `--brief` missing; a hand-back path that does not exist.

## 4. Docs

- `docs/brief-format.md` exists and names the brief fields of AD6: `Slice:`,
  `Gate commit:`, `Gate files:`, `Pest command:`, `Project root:`, `Craft version:`,
  the `## R<n>` headings with acceptance criteria verbatim, pointers, and the
  rules. It also lists the five required hand-back lines of section 2 (the
  hand-back format), standalone, with no reference to Claude.
- `docs/outside-builders.md` exists, contains the call form
  `<command> <brief-file> <handback-file>`, the exit-code table (0 done, 3
  unavailable, any other failed, no exit within `timeout_minutes` counts as
  failed), and mentions `bin/handback_check.py`.

## 5. Lock-check fix

The builder and both reviewers use `git diff --quiet <gate commit> -- <gate files>`
(working tree against the gate commit, so staged edits are caught).

- `agents/craft-feature-builder.md`, `agents/craft-code-reviewer.md`,
  `agents/craft-code-reviewer-deep.md` and `docs/agents.md` contain the string
  `git diff --quiet <gate commit> -- <gate files>`.
- No file in `agents/` or `docs/` contains `git diff --quiet -- <gate files>`.
- The committed form `git diff --quiet <gate commit> HEAD -- <gate files>` stays
  in the builder and `docs/agents.md`.

Exact greps (all from the repo root; the first four must find a match, the last
must find none):

    grep -F 'git diff --quiet <gate commit> -- <gate files>' agents/craft-feature-builder.md
    grep -F 'git diff --quiet <gate commit> -- <gate files>' agents/craft-code-reviewer.md
    grep -F 'git diff --quiet <gate commit> -- <gate files>' agents/craft-code-reviewer-deep.md
    grep -F 'git diff --quiet <gate commit> -- <gate files>' docs/agents.md
    grep -rF 'git diff --quiet -- <gate files>' agents docs

## 6. bin/check.sh

Adds one `gate` line, `python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/complete.md`,
and one `must_fail` line per broken fixture (six), each with `--brief` the same brief.

## 7. Facts pins

All in `evals/behavior-sets/agents.json`, case `builder-checker-small-sensitive`
(already pinned by the builder gate; already in the facts check). Added by the
gate commit, not the builder: `docs/outside-builders.md`, `docs/brief-format.md`,
`docs/agents.md`, the two reviewers, and the new lock form in the builder, plus
`not_contains` for the old form. The builder makes the files satisfy them.
