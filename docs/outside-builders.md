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

Each builder has a `timeout_minutes` value (see `docs/profile.md`). A builder that has not exited within `timeout_minutes` counts as failed.

## Before each builder

Each builder starts from a clean slice, so a failed builder leaves nothing behind for the next one.

1. Record the base commit.
2. Reset the slice's working tree to it: `git reset --hard <base>` and `git clean -fd`, inside the project root only.
3. Delete any old hand-back file.

Within one builder's fix rounds the tree is kept, so the builder fixes on top of its own work.

## After the builder exits

`bin/handback_check.py` checks every hand-back before anything else: `python3 bin/handback_check.py --brief <brief-file> <handback-file>`. A hand-back with a missing or bad line is not a pass, whatever else it says.

| Result | Action |
|---|---|
| exit 0, checker passes | rerun the gate and the lock checks yourself; the slice passes only when every `R<n>` is `PASS`, both lock checks are `exit 0` and the gate is green |
| exit 0, checker fails | another round for the same builder with the checker's messages, up to 3 rounds; then the next builder |
| exit 3 | next builder |
| other exit | next builder |
| timeout | kill the whole process tree, then next builder |

The hand-back is a claim, not evidence: the caller reruns the gate and the lock checks itself.

## Order

Builders run in the order listed in the project profile. When all of them are unavailable or failed, the main assistant builds the slice itself from the same brief.
