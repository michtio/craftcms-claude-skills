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

Each builder has a `timeout_minutes` value. A builder that has not exited within `timeout_minutes` counts as failed, and is stopped.

## After the builder exits 0

1. `bin/handback_check.py` checks every hand-back before anything else: `python3 bin/handback_check.py --brief <brief-file> <handback-file>`. A hand-back with a missing or bad line is not a pass, whatever else it says.
2. The caller reruns the gate command itself and runs the lock checks itself. The hand-back is a claim, not evidence.
3. The slice passes only when every `R<n>` line is `PASS`, both lock checks are `exit 0`, and the gate is green.
4. A hand-back that fails these checks goes back to the same builder for another round, up to 3 rounds. After that, the next builder in order takes the brief.

## Order

Builders run in the order listed in the project profile. When all of them are unavailable or failed, the main assistant builds the slice itself from the same brief.
