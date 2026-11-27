# Outside builders

An outside builder is a program other than the main assistant that builds one slice from a brief: a local AI running on your machine, a script, or a person. The protocol below is the same for all of them and needs no particular tool.

## Call form

```
<command> <brief-file> <handback-file>
```

The command is configured per builder. It receives two paths. It reads the brief (format in `docs/brief-format.md`), does the work in the project root named there, and writes the hand-back to the second path.

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | done, hand-back written |
| 3 | unavailable (not installed, not running, no capacity): try the next builder at once |
| other | failed: try the next builder |

## Timeout

Each builder has a `timeout_minutes` value (see `docs/profile.md`). A builder that has not exited within `timeout_minutes` counts as failed. The pack's `bin/run_builder.py` runs one builder with its timeout and kills the whole process tree when it expires (exit 124).

## Before each builder

Each builder starts from a clean slice, so a failed builder leaves nothing behind for the next one.

1. Record the base commit.
2. Reset the slice's working tree to it: `git reset --hard <base>` and `git clean -fd`, inside the project root only.
3. Delete any old hand-back file.

Within one builder's fix rounds the tree is kept, so the builder fixes on top of its own work.

## After the builder exits

After every exit 0, in every round, the caller checks in this order:

1. Both lock checks (`git diff --quiet <gate commit> HEAD -- <gate files>` and `git diff --quiet <gate commit> -- <gate files>`). A nonzero code disqualifies the builder: reset, next builder.
2. A clean tree: `git status --porcelain --untracked-files=all` prints nothing. Uncommitted work sends the slice back to the same builder.
3. The hand-back checker: `python3 bin/handback_check.py --brief <brief-file> <handback-file>`. A hand-back with a missing or bad line is not a pass, whatever else it says.

| Result | Action |
|---|---|
| exit 0, hand-back checker passes | rerun the gate yourself; the slice passes only when every `R<n>` is `PASS`, both lock checks are `exit 0` and the gate is green |
| exit 0, hand-back checker fails | another round for the same builder with the hand-back checker's messages, up to 3 rounds; then the next builder |
| exit 0, a lock check nonzero | the builder is disqualified: reset, next builder |
| exit 3 | next builder |
| other exit | next builder |
| timeout | kill the whole process tree, then next builder |

The hand-back is a claim, not evidence: the caller reruns the gate and the lock checks itself.

## Order

Builders run in the order listed in the project profile. When all of them are unavailable or failed, the pack's own builder, `craft-feature-builder`, builds the slice from the same brief.
