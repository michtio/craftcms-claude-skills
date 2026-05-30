# Database, Backups, and the Queue on Servd

Servd runs **MariaDB or MySQL 8** and reaches it over an **SSH tunnel** — there's no public DB port. Backups are automatic, four-component, and retained 30 days. The queue runs via control-panel AJAX by default; the **Dedicated Queue Runner** (Enhanced/Pro plans) isolates it. Servd does **not** document a user-configurable cron — move recurring work into queue jobs.

## Documentation

- Connect to the database (MySQL CLI): https://servd.host/docs/connect-to-the-database-with-mysql-cli
- Backup & restore: https://servd.host/docs/backup-restore
- Dedicated Queue Runner: https://servd.host/docs/dedicated-queue-runner

## Common Pitfalls

- Looking for a direct public database host/port. There isn't one. Access is only over an SSH tunnel with port forwarding (see below). Unlike Craft Cloud — which exposes connection credentials directly — Servd gates the DB behind an SSH session.
- Assuming MariaDB is fine to stay on long-term. Craft 5 no longer officially supports MariaDB; Servd's default is now MySQL 8.0 and provides an "Upgrading a Project From MariaDB to MySQL 8" path. New projects should target MySQL 8. (Contrast Craft Cloud, which bans MariaDB outright.)
- Assuming Postgres is available. Servd's docs reference only MySQL/MariaDB — Postgres support is **Verify / not documented**.
- Expecting jobs to run on their own under the default queue. By default Craft's queue is driven by control-panel AJAX, so a job not triggered by CP activity "will just sit in a pending state until an admin logs in." Heavy jobs also steal resources from user requests. Enable the Dedicated Queue Runner instead.
- Scheduling work via cron. Servd does not document a cron UI — do not assume one exists. **Verify** per plan; otherwise model recurring work as queue jobs (see below).
- Running a `push-database` casually. A DB push may make the **target** environment unresponsive during transfer. See `local-dev.md`.

## Database engine

| Engine | Status |
|---|---|
| MySQL | 8.0 — current default for new projects |
| MariaDB | Supported (legacy); migrate to MySQL 8 per Servd's upgrade doc |
| Postgres | **Verify / not documented** |

## Connecting to the database

There is no public DB port. You connect over an SSH tunnel (Servd **does** offer SSH sessions — a difference from Craft Cloud):

1. Open the project's **Access Control** page and create a new **SSH Session**.
2. In the **SSH Connection** section, select an environment and enable the **"Include database port forward"** option, then copy and run the supplied SSH connection string in your local terminal. This opens the tunnel.
3. With the MySQL client installed locally, return to Access Control and, from the **Database Connection** section, copy the **"MySQL CLI"** command and run it. It connects through the forwarded port.

Once connected, `show databases`, `use <database>`, `show tables`, and `show processlist` / `show full processlist` help you navigate and inspect running queries. For importing data, use Servd's sync commands rather than a manual import (see Sync commands below).

## Backups

All of a project's environments are **automatically backed up on a regular basis, the frequency of which is determined by the plan**. Each backup includes four components:

- A database dump.
- The deployed bundle at backup time.
- Environment settings (environment variables, etc.).
- A snapshot of assets on the Servd Asset Platform.

Backups are **retained for 30 days**.

**Manual backup:** select the project → **Environment > Backups** → **"Create a New Backup"**. Progress shows in the task bar; the backup appears in the list when complete.

**Restore:** on the **Environment > Backups** page, click **Restore** on the chosen backup. Restoration takes **anywhere from 30 seconds to 10 minutes** depending on project and asset size.

**Asset retention caveat:** the Servd Asset Platform only keeps copies of deleted files for up to **90 days**. Restoring an old backup will **not** restore files that were deleted more than 90 days ago.

## Queue

By default Craft processes the queue via AJAX requests triggered on control-panel activity. Consequences:

- Jobs not enqueued by CP activity sit **pending** until an admin logs in.
- Long-running jobs consume resources from normal user requests.
- CPU-intensive jobs can starve normal operations.

The **Dedicated Queue Runner** (available on **Enhanced and Pro** plans; the Starter plan keeps the default) isolates job processing from user requests. Jobs run "immediately after being created and within their own pool of resources."

**Enable it:** open the environment's settings page (Production or Staging) → **"Dedicated Queue Runner"** section → flip the switch on → deploy with **Sync**.

**Local debugging:** to find jobs that misbehave under isolation before enabling it, set `'runQueueAutomatically' => false` in `config/general.php` and run `./craft queue/run` from the project root.

## Cron / scheduled tasks

Servd's docs do **not** document a user-configurable cron feature — treat any cron capability as **Verify / not documented**, and do not claim a cron UI exists. The supported pattern for recurring work is queue jobs (triggered by application events, or self-perpetuating) combined with the Dedicated Queue Runner so they actually run without CP activity.

## Sync commands (brief)

For moving data between environments and to/from local, the `servd/craft-asset-storage` plugin provides console commands — detailed in `local-dev.md`:

- `servd-asset-storage/clone` — clone between environments.
- `servd-asset-storage/local/pull-database` — pull a remote DB to local.
- `servd-asset-storage/local/push-database` — push the local DB to a remote environment. A push may leave the **target** environment unresponsive during transfer; avoid pushing to production lightly.

For deploy mechanics and environment/Project Config sync discipline, see `deploy-and-environments.md`; for the broader filesystem and feature constraints, see `limitations.md`.

Last verified against https://servd.host/docs/backup-restore, https://servd.host/docs/connect-to-the-database-with-mysql-cli, and https://servd.host/docs/dedicated-queue-runner on 2026-05-30.
