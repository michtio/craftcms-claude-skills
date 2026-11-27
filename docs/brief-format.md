# Brief and hand-back format

This page defines two plain-text documents: the brief a builder receives and the hand-back it writes. Any builder can use them, human or AI, local or hosted. The builder reads one brief file, builds one slice, and writes one hand-back file.

## The brief

A brief is a markdown file. The header fields come first, one per line, as `Name: value`.

| Field | Meaning |
|---|---|
| `Slice:` | The slice id, for example `S1`. |
| `Gate commit:` | The commit that holds the locked gate tests, or `none` when the builder writes its own tests. |
| `Gate files:` | The test files in that commit, separated by spaces. |
| `Pest command:` | The command that runs the gate. Run it exactly as written. Stack-specific. |
| `Project root:` | The absolute path of the project. Work only inside it. |
| `Craft version:` | The Craft CMS version the code must target. Stack-specific. |

After the fields, each requirement is a level-2 heading followed by its text and its acceptance criteria, copied verbatim:

```
## R<n>

The requirement text (MUST or SHOULD).
AC<n>: Given ..., when ..., then ...
```

Then two more sections:

- `## Pointers`: file paths the builder must read before it writes code (conventions and known pitfalls).
- `## Rules`: always these three.
  - Never edit a gate file.
  - Stop at a passing gate.
  - At most 3 rounds.

## Working rules

1. Read every pointer first.
2. Run the Pest command. It must fail before you build and pass when you stop.
3. Edit only files that are not gate files. A gate test that looks wrong is reported in the hand-back, never changed.
4. Stop as soon as the gate passes. Do not add scope.

## The hand-back

After the work, write the hand-back file. It has exactly these five kinds of line. Each starts at the beginning of its line, in plain text, with no list marker, no bold and no code fence in the real file:

```
Gate flow: locked (<sha>)
Lock check (committed): exit <n>
Lock check (working tree): exit <n>
R<n>: PASS|FAIL|PENDING
Builder: <name>
```

- `Gate flow:` is `locked (<sha>)` when the brief has a gate commit (`<sha>` is 7 to 40 hex characters), or `builder-written (<reason>)` when it does not.
- `Lock check (committed):` is the exit code of `git diff --quiet <gate commit> HEAD -- <gate files>`.
- `Lock check (working tree):` is the exit code of `git diff --quiet <gate commit> -- <gate files>`. This compares your working tree and index with the gate commit.
- Both lock lines are required when the flow is `locked`. Each must be `exit 0`. A nonzero code means a gate file changed, and the slice does not pass.
- One `R<n>:` line per `## R<n>` heading in the brief, with exactly one of `PASS`, `FAIL` or `PENDING`.
- `Builder:` is your name, on one line.

Any other text in the file is allowed, for example notes or disputed tests, as long as it does not start with one of these line shapes.

## Check

`python3 bin/handback_check.py --brief <brief-file> <handback-file>` checks the form. It exits 0 when every required line is present and well formed, and 1 with one message per problem otherwise. A hand-back that is missing a line does not count as a pass.
