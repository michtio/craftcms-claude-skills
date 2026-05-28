# Database on Cloud

Cloud provisions and manages your database — you don't run it, configure `db.php`, or set `CRAFT_DB_*` env vars. The Cloud extension auto-wires the connection. You get MySQL 8.0 or Postgres 15; nothing else is supported.

## Documentation

- Databases reference: https://craftcms.com/docs/cloud/databases

## Common Pitfalls

- Committing a `config/db.php` with hardcoded credentials. Cloud's auto-wiring won't override file-based config in all cases, and stale credentials in `db.php` will fight the platform. Remove `db.php` entirely or wrap its contents in an `App::env('CRAFT_CLOUD')` check that no-ops on Cloud.
- Setting `CRAFT_DB_*` env vars on Cloud. Same root cause as above — the Cloud extension injects connection details automatically; manual overrides break the wiring.
- Using `tablePrefix`. Unsupported. Run `php craft db/drop-table-prefix` locally before importing, and remove the setting from both `db.php` and `.env` before deploying.
- Choosing MariaDB. Cloud only supports MySQL 8.0 and Postgres 15. New projects should default to MySQL 8.0 — Postgres is supported but Craft's Postgres surface has fewer plugins tested against it.
- Setting a custom `backupCommand` to work around the Cloud-managed backup format. The docs explicitly warn: "[A custom `backupCommand`] can cause unreliable backups." Use Cloud's backup interface instead.
- Restoring a Postgres backup with `psql` instead of `pg_restore`. Cloud captures Postgres backups in `custom` format (Craft defaults to plaintext). `psql < backup.sql` fails on the custom format. You need `pg_restore` with specific flags.

## Supported engines

| Engine | Version | Notes |
|---|---|---|
| MySQL | 8.0 | Recommended for new projects |
| Postgres | 15 | Supported; smaller plugin compatibility surface |
| MariaDB | — | Not supported |

Both engines are available in every region. The engine is chosen at project creation and can't be changed afterward (along with region — see `limitations.md`).

## Configuration: there isn't any

Once your Cloud project is provisioned, you don't configure the database connection. The Cloud extension reads the platform-supplied credentials at boot and wires `Craft::$app->db` automatically.

Things to **remove or leave unset** when deploying to Cloud:

- `config/db.php` — delete it, or wrap in `if (!App::env('CRAFT_CLOUD'))` so it only applies locally.
- `CRAFT_DB_DRIVER`, `CRAFT_DB_SERVER`, `CRAFT_DB_USER`, `CRAFT_DB_PASSWORD`, `CRAFT_DB_DATABASE`, `CRAFT_DB_PORT`, `CRAFT_DB_TABLE_PREFIX` — Cloud sets all of these automatically. Leave them unset in the Console env vars.
- `db.php` `tableSchema` / `port` / `socket` overrides — same reason.

For local development you still need these — see `local-dev.md` for the recommended pattern.

## Backups

Cloud takes automated nightly backups per environment and lets you trigger a manual backup on demand from Console. Retention period is not stated in the docs.

The CP's Database Backup utility is **disabled** on Cloud — backups happen at the platform level, not via the Craft application. Plugins that depend on the CP utility (rare) won't work; use Cloud's backup interface instead.

## Restoring a backup

Download the backup from Console (Databases → Backups → Download), then restore against the target database.

### MySQL

Client version must match the dump version (ideally minor version). Use the `mysql` CLI:

```sh
mysql --host={hostname} --port=3306 --user={username} \
  --password={password} --database={database} < backup.sql
```

For a local DDEV environment, Craft's built-in restore command works:

```sh
ddev craft db/restore /path/to/backup.sql
```

### Postgres

Cloud captures Postgres backups in `custom` format. You need `pg_restore`, not `psql`:

```sh
pg_restore --host={hostname} --username={username} \
  --dbname={database} \
  --no-owner --clean --single-transaction --if-exists --no-acl \
  backup.dump
```

The flag set matters:
- `--no-owner` strips ownership metadata that doesn't apply on the destination.
- `--clean` drops existing objects before recreating.
- `--single-transaction` makes the restore atomic.
- `--if-exists` prevents errors on missing objects during the drop phase.
- `--no-acl` strips ACL/grant statements.

For plaintext-format Postgres dumps (e.g. from a self-hosted Craft project), use `psql`:

```sh
psql --host={hostname} --username={username} \
  --dbname={database} --password < backup.sql
```

## Connection access for external tools

Database credentials are available in the Cloud Console under **Access** for each environment. These let you connect a desktop client (TablePlus, Sequel Ace, pgAdmin) or run scripts against the live DB.

Treat these credentials as production secrets — they bypass the application's permission model entirely.

## Migrating an existing database

The end-to-end migration sequence (export, schema cleanup, table-prefix removal, import) lives in `migration.md`. The short version for the DB step alone:

1. Locally: `php craft db/drop-table-prefix` if you ever used a table prefix.
2. Locally: export your DB.
3. Provision the Cloud project with the matching engine and version.
4. Import the dump using the engine-specific command above.

Last verified against https://craftcms.com/docs/cloud/databases on 2026-05-28.
