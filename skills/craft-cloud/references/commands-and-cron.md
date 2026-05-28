# Console Commands, Scheduled Cron, and Queue Jobs

Cloud has no SSH. Commands run through the Console UI's command runner. Recurring commands schedule from the same UI with a one-hour minimum interval. Queue jobs are auto-processed — don't schedule a runner yourself.

## Documentation

- Console commands: https://craftcms.com/docs/cloud/commands
- Scheduled commands (cron): https://craftcms.com/docs/cloud/cron

## Common Pitfalls

- Adding a scheduled command `php craft queue/run` (or similar) to "make sure the queue runs." Cloud already processes queue jobs automatically. A scheduled queue runner is redundant and can produce competing workers.
- Trying to pipe output (`craft my-command | grep error`) or chain commands (`craft a && craft b`) in the runner. Shell interpolation and piping aren't supported — one command per execution.
- Writing a recurring command that needs to run more often than hourly. Cloud's UI enforces a one-hour minimum. If you need higher frequency, design the work as queue jobs triggered by application events instead of by a cron schedule.
- Trying to schedule commands by committing them to `craft-cloud.yaml`. No YAML-based scheduling exists — Console UI is the only surface.
- Running a long-running resave without `--limit` or batching. Commands cap at 15 minutes. A `resave/entries` across 50k entries on a complex element type will hit the cap. Use the `--limit` option and run multiple times, or split into batched queue jobs.
- Expecting to edit a scheduled command in place. They can't be edited — delete and recreate to change anything (the schedule, the command, etc.).

## Console command runner

Each Cloud environment has a **Commands** screen in the Console.

### How to run a command

1. Open the Commands screen for the target environment.
2. Enter the command text — everything after `craft`. For example, to run `php craft resave/entries`, type `resave/entries`.
3. Press Enter or click Execute.
4. The command moves through states: **Pending** → **Running** → **Success** / **Error**.

Output is captured and viewable by expanding the row in the command history.

### Constraints

| Constraint | Value |
|---|---|
| Command text length | 255 characters (everything after `craft`) |
| Execution time | 15 minutes maximum |
| Interactive prompts | Not allowed — all input must be passed as args/options |
| Shell features | No piping, no command chaining, no bash interpolation |
| History retention | 6 months |

The 255-char limit catches you when running a `resave/entries --propagate-to=site1,site2,site3 --type=foo,bar,baz --status=...` with many options. Split into multiple runs if you hit it.

The 15-min cap is the same as queue jobs (both run in 15-minute-bound Lambda invocations). For longer work, see Queue Jobs below.

### What commands are available

Any Craft console command (`migrate/up`, `clear-caches/all`, `resave/entries`, `db/restore`, etc.) plus any plugin- or module-registered commands. The Cloud extension adds `cloud/*` commands (most are infrastructure-only — see `extension.md`).

The two `cloud/*` commands worth knowing about manually:

- `cloud/info` — diagnostic info about the environment, useful when debugging.
- `cloud/static-cache` — manual edge cache operations (inspect, purge).

## Scheduled commands (cron)

Recurring commands are scheduled from the same Commands screen, under **Scheduled Commands → Create**.

### Configuration

- **Command** — same syntax as one-off commands (everything after `craft`, 255-char cap).
- **Cron expression** — standard cron syntax. The docs reference Cronitor's Crontab.guru as the recommended tool for constructing expressions.

### Frequency floor

**One hour minimum interval.** You can pick the minute offset (e.g. `:17`), but you can't run more often than once per hour — the Console UI enforces this floor.

### Other constraints

| Constraint | Value |
|---|---|
| Max scheduled commands per environment | 5 |
| Editable in place | No — delete and recreate |
| Execution timing precision | Approximate (typically a few seconds late) |
| Same execution limits as one-off | 15 minutes, 255 chars, no shell features |

### Designing around the one-hour floor

When you need more frequent work, the supported pattern is:

- **Queue jobs triggered by events** — when an entry saves, when an asset uploads, when a webhook fires. The job runs immediately (auto-processed) rather than waiting for a scheduled tick.
- **Batched queue jobs** — a long-running task split into many small jobs, each well under the 15-minute cap. See Queue Jobs below.
- **Self-perpetuating jobs** — a queue job that schedules its own next invocation. Use carefully; easy to lose track of.

## Queue jobs

Cloud auto-processes queue jobs. You don't:

- Run a queue worker on a server (there isn't one).
- Schedule a Console command to drive the queue (don't — it conflicts with the platform runner).
- Configure a queue daemon in `app.php` (the extension auto-wires queue components).

You do:

- Push jobs to the queue normally (`Craft::$app->getQueue()->push(new MyJob([...]))`).
- Budget for the 15-minute per-job cap.
- Split long work into batched jobs.

### The 15-minute cap

Each queue job runs in a Lambda invocation capped at 15 minutes. The docs are explicit: "Jobs exceeding 15 minutes should be batched."

### Batched job pattern

A job that processes 100k records over 30 minutes won't survive Cloud. Instead, design it as:

```php
// Parent: figures out total work, queues N child jobs.
class SyncAllEntriesJob extends BaseBatchedJob
{
    protected function loadData(): Collection
    {
        return Entry::find()
            ->section('blog')
            ->collect();
    }

    protected function processItem(mixed $item): void
    {
        $this->syncOne($item);
    }
}
```

Each batch typically processes 50–200 items in well under 15 minutes. Failures are isolated to the current batch — the rest of the job continues.

See the `craftcms` skill's `queue-jobs.md` for the full batched-job pattern (`BaseBatchedJob`, TTR, retry, progress).

### What goes wrong if you ignore the cap

A job that hits 15 minutes is killed mid-execution by Lambda. Craft's queue will retry per the job's TTR/retry config, but each retry hits the same cap — guaranteed failure loop. Visible in Console as a stuck queue entry.

The fix is always architectural — split into smaller units, not "increase the timeout" (no setting exists).

## Reading command output

The Console command runner captures stdout and stderr. Click the row in command history to expand the output. Logs from inside the command (anything routed through `Craft::info/warning/error()`) also appear there.

There is no separate log-tailing UI documented today. If you need persistent operational logs, route them to an external service (Loggly, Papertrail, Datadog) via a Monolog handler configured in `config/app.php`. See `limitations.md` (Logs) for the broader picture.

Last verified against https://craftcms.com/docs/cloud/commands and https://craftcms.com/docs/cloud/cron on 2026-05-28.
