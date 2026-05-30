# Local Development for Servd Projects

Servd has **no first-party local environment and no separate Servd CLI** — local dev is bring-your-own. **DDEV is the standard local stack** for Craft on Servd; set it up the normal way (see the `ddev` skill for the mechanics — `.ddev/config.yaml`, PHP/DB/Node versions, shorthand commands). Match the PHP, database, and Node versions to whatever your Servd build runs (see `deploy-and-environments.md`).

`local` is one of Servd's three environments (local → staging → production) and is "always the most up-to-date" — all changes originate locally, then sync forward. Because the workflow is **uni-directional**, the safe day-to-day pattern is to pull production (or staging) DB and assets *down* to local to work against real content; pushing *up* is rare and risky (see "Sync discipline" below and `deploy-and-environments.md`).

## Documentation

- The Servd workflow (environments, uni-directional flow): https://servd.host/docs/the-servd-workflow
- Plugin console commands (sync commands): https://servd.host/docs/servd-plugin-console-commands
- DDEV setup (general): see the `ddev` skill in this repo

## Local env vars for the asset plugin

The `servd/craft-asset-storage` plugin needs two values set as **local** env vars (in `.env`, not committed for production — those live in the dashboard):

```sh
SERVD_PROJECT_SLUG=your-project-slug
SERVD_SECURITY_KEY=your-security-key
```

Both come from the dashboard's **Assets** page. With them set, the plugin targets the `local` asset directory locally and authenticates the sync commands below. See `asset-storage.md` for the full filesystem setup.

## Sync console commands

These ship with `servd/craft-asset-storage` and are the local-dev workhorses. Through DDEV, prefix with `ddev craft`. Each **auto-detects its settings** (from `SERVD_PROJECT_SLUG` / `SERVD_SECURITY_KEY`) but accepts CLI flags to override — `--from` / `--to` pick the remote environment, `--servdSlug` / `--servdKey` override credentials, `--interactive` prompts.

```sh
# Download assets from a remote env (staging, development, or production) to local
ddev craft servd-asset-storage/local/pull-assets

# Upload local assets to a remote env
ddev craft servd-asset-storage/local/push-assets

# Download the database from Servd to local
ddev craft servd-asset-storage/local/pull-database

# Upload the local database to a Servd env
ddev craft servd-asset-storage/local/push-database
```

`pull-database` accepts `--skipBackup` and `--emptyDatabase` (the latter completely empties the target local DB before importing — avoid it if several projects share one database). `push-database` warning: "While a database is being pushed to a Servd environment, the target environment is likely to become unresponsive" during the transfer.

Two more remote-operation commands:

```sh
# Clone database/assets/bundle between staging, development, and production
ddev craft servd-asset-storage/clone --from=staging --to=production

# Run a Craft console command inside a remote Servd environment
ddev craft servd-asset-storage/command
```

`clone` flags include `--from`, `--to`, `--database`, `--assets`, `--bundle`, `--newEnvVars`, `--wait`. `command` accepts `--environment`, `--wait`, `--interactive`. Both also take `--servdSlug` / `--servdKey`. Don't invent flags beyond these — the documented set is exhaustive.

## Sync discipline

The whole platform is uni-directional, and so is the disciplined sync workflow:

- **Pull down freely.** `pull-database` + `pull-assets` from production (or staging) gives you real content to develop against. This is the everyday move.
- **Push up rarely.** Prefer deploying code and letting **Project Config sync forward** carry schema/settings changes (`allowAdminChanges` is off on staging/production — see `deploy-and-environments.md`). A `push-database` overwrites a live environment's content and can knock it offline during transfer; reserve it for deliberate, low-traffic operations.
- **`clone` for env-to-env.** To seed staging from production (or similar), use `servd-asset-storage/clone` rather than round-tripping through local.

## Common Pitfalls

- **Looking for a Servd local environment or CLI.** There isn't one. Use DDEV (`ddev` skill); Servd only provides the plugin's console commands and the dashboard.
- **Forgetting `SERVD_PROJECT_SLUG` / `SERVD_SECURITY_KEY` locally.** Without them the sync commands can't authenticate and the local filesystem won't resolve to the `local` asset directory. Pull them from the dashboard Assets page into `.env`.
- **Running `push-database` against production casually.** The target environment is likely to become unresponsive mid-push, and you've overwritten live content. Pull down instead; let Project Config flow changes up.
- **Using `--emptyDatabase` on a shared local database.** It wipes the entire target DB first — destructive if multiple projects share one DB server.
- **Running the commands on the host instead of through DDEV.** Run `ddev craft servd-asset-storage/...` so they execute inside the container against your local Craft install. See the `ddev` skill.
- **Expecting bidirectional sync.** Local is the source of truth; the flow is local → staging → production. There is no "pull config down from production" path — see `deploy-and-environments.md`.

## Database restore (alternative to pull-database)

If you have a manual backup file rather than a live sync, restore it with Craft's built-in command inside DDEV (`ddev craft db/restore /path/to/backup.sql`) or `ddev import-db`. See `database-and-queue.md` for Servd's backup/restore details and the `ddev` skill for local import mechanics.

Last verified against https://servd.host/docs/the-servd-workflow and https://servd.host/docs/servd-plugin-console-commands on 2026-05-30.
