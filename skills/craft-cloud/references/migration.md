# Self-Hosted to Cloud Migration

End-to-end migration sequence for moving an existing Craft site from self-hosted infrastructure to Cloud. The path: audit → code/config prep → DB export-import → asset sync → DNS cutover.

## Documentation

- Migrating: https://craftcms.com/docs/cloud/migrating
- Launch checklist: https://craftcms.com/docs/cloud/launch-checklist

## Common Pitfalls

- Starting the migration on Craft < 4.6.0. Cloud requires 4.6.0 minimum. Upgrade Craft first on the self-hosted side, verify the site still works, then migrate.
- Leaving a `tablePrefix` in `config/db.php` or `.env` when importing into Cloud. The import succeeds but Craft can't find its tables — the schema looks alien. Run `php craft db/drop-table-prefix` locally before exporting.
- Skipping the `aws s3 sync` step and uploading assets through the CP. Possible for small sites; impractical at scale. Sync via S3 CLI is the documented path.
- Cutting DNS before validating the Cloud site via the preview URL. Every environment gets a `*.preview.craft.cloud` URL — use it to verify end-to-end before swinging production DNS.
- Forgetting to put the legacy site in maintenance mode during the final cutover. New writes on the legacy site after your final DB export are lost.
- Leaving custom-coded mail in place that uses `sendmail`. Cloud has no built-in mail. The default sendmail adapter fails silently — emails just don't arrive. Configure SMTP/Postmark/SES/Resend before flipping DNS. See `limitations.md` (Mail).

## Pre-migration audit

Before starting, check the self-hosted site for things that won't translate:

| Check | What to do |
|---|---|
| Craft version ≥ 4.6.0 | Upgrade self-hosted first if needed |
| Cloud extension installed | `composer require craftcms/cloud` and run `php craft setup/cloud` |
| `craft-cloud.yaml` at repo root | Create with at minimum `php-version` (see `config-file.md`) |
| MariaDB | Cloud only supports MySQL 8.0 / Postgres 15. Convert before migrating, or accept a re-platforming step |
| `tablePrefix` set | Run `php craft db/drop-table-prefix` locally; unset in `db.php` and `.env` |
| Custom `db.php` config | Wrap in `if (!App::env('CRAFT_CLOUD'))` or remove entirely |
| Custom `CRAFT_DB_*` env vars | Will be ignored on Cloud (auto-wired connection) — but won't break |
| Local filesystems | Convert to Cloud filesystem type in the CP (see `assets-and-transforms.md`) |
| Third-party S3 plugins for assets | Replace with Cloud's bundled filesystem type |
| Mail adapter | Configure SMTP/Postmark/SES/Resend; default sendmail won't work |
| ImageOptimize / Imager-X | Remove or disable; Cloud's edge transforms supersede |
| `.htaccess` / nginx config | Migrate rules to `redirects:` and `rewrites:` in `craft-cloud.yaml` |
| Custom queue runner (systemd, supervisor, cron) | Remove — Cloud auto-processes |
| Scheduled cron jobs | Migrate to Console UI's Scheduled Commands; check hourly-minimum compatibility |
| Forked Git repository | Move to upstream; Cloud can't deploy forks |
| Logging that writes to files | Switch to `Craft::info/warning/error()` (see `plugin-development.md`) |

## Migration sequence

### Phase 1: Code and configuration

Goal: get the codebase Cloud-deployable, without touching production yet.

1. **Install the Cloud extension** on a feature branch:
   ```sh
   composer require craftcms/cloud
   php craft setup/cloud
   ```
2. **Create `craft-cloud.yaml`** at the repo root:
   ```yaml
   php-version: "8.3"
   # node-version: "20"   # uncomment if you have a JS build
   ```
3. **Audit `config/app.php`** — remove or environment-scope anything that overrides cache, mutex, queue, session, or assetManager. Cloud's extension overrides these automatically; conflicting local config can break the wiring.
4. **Convert local filesystems** in the CP (Settings → Filesystems). Create a new filesystem with the Cloud type, set the Subpath (e.g. `assets/`), copy your old Base Path and Base URL into the **Local Filesystem** section for dev-environment parity. Update asset volumes to point at the new filesystem.
5. **Move env vars** out of `.env` and into the Cloud Console UI per environment. `.env` is for local dev only on Cloud — production env vars live in Console.
6. **Audit asset bundle paths** in any custom plugins/modules. `sourcePath` must use an alias, not a hardcoded `__DIR__` path.
7. **Push to a feature branch** connected to a Cloud staging environment. Verify the build phase succeeds end-to-end before touching production.

### Phase 2: Database

1. **Locally, drop any table prefix** if you ever used one:
   ```sh
   php craft db/drop-table-prefix
   ```
2. **Export the self-hosted DB**:
   - MySQL: `mysqldump --user=... --password=... --host=... dbname > backup.sql`
   - Postgres: `pg_dump --host=... --username=... --format=custom dbname > backup.dump`
3. **Import into Cloud**:
   - MySQL: `mysql --host={cloud-host} --user={cloud-user} --password={cloud-pass} --database={cloud-db} < backup.sql`
   - Postgres: `pg_restore --host={cloud-host} --username={cloud-user} --dbname={cloud-db} --no-owner --clean --single-transaction --if-exists --no-acl backup.dump`

   Connection details come from the **Access** screen in Console (see `database.md`).

### Phase 3: Assets

The supported tool is the AWS S3 CLI's `sync`. You need AWS credentials set up locally (`aws configure`) with access to Cloud's bucket — the exact bucket and credential setup is in the Console UI.

```sh
aws s3 sync ./web/craft-cloud-assets/ s3://{project-uuid}/{environment-uuid}/assets/
```

The third URL segment (`assets/`) must match the Subpath you set on the Cloud filesystem. Files uploaded outside it are invisible to Craft.

For an active site, run sync periodically during the migration window — each run catches new uploads on the legacy side.

### Phase 4: Deploy and verify on preview URL

1. **Trigger a deploy** (push the migration branch, or use the Manual trigger).
2. **Watch the Build → Migrate → Release pipeline** in Console. The Migrate phase runs `php craft cloud/up`, which applies any pending migrations and project config — see `deploy-pipeline.md`.
3. **Verify the site on the preview URL** — `project-{handle}-environment-{prefix}.preview.craft.cloud`.
4. **Walk through the critical paths**: homepage, login, content editing, file upload, form submission, search, any payment/checkout. Confirm each works against the Cloud DB and Cloud filesystem.

### Phase 5: Launch (DNS cutover)

The recommended sequence minimizes data loss and downtime:

1. **Put the legacy site in maintenance mode.** Block writes (forms, registrations, comments) to prevent new data from being lost in the final sync.
2. **Final DB export + import.** Re-run Phase 2 to capture any changes since the staging-environment import.
3. **Final asset sync.** Re-run Phase 3 with `aws s3 sync` — it only uploads new/modified files.
4. **Trigger a final Cloud deploy** to apply any last-minute code changes.
5. **Disable maintenance mode** on Cloud and verify on the preview URL one more time.
6. **Update DNS** to point your domain at Cloud (CNAME to `edge.craft.cloud` or A records for apex — see `domains.md`).
7. **Monitor.** Watch Console logs, error rates, and queue processing for the first few hours. DNS propagation can take minutes to 24 hours; some users will still hit the legacy server until their DNS resolver refreshes.

## Rollback

There is no one-click rollback to the legacy infrastructure once DNS is cut. The supported approach:

- Keep the legacy server running for a defined post-launch window (one to two weeks is common).
- If a critical issue surfaces on Cloud, revert DNS to the legacy IP. New requests flow back to legacy; users with a cached Cloud DNS entry continue hitting Cloud until their resolvers refresh.
- Fix the issue on Cloud, redeploy, point DNS back.

This is messy by design — there's no fork in the timeline. Any writes during the legacy-rollback window are stranded if you cut back to Cloud later. Plan the launch to minimize the need.

## Post-migration cleanup

After the migration is verified stable:

- Decommission the legacy server (with a final backup).
- Remove `db.php` from the repo if you wrapped it in environment checks — pure dead code at this point.
- Strip any `App::env('CRAFT_CLOUD')` branches in code that were temporary migration scaffolding.
- Remove ImageOptimize / similar plugins that Cloud's edge transforms supersede.
- Document the new env vars in `.env.example` for new team members.

For the broader launch-day checklist (TLS verification, header checks, SEO redirects), see https://craftcms.com/docs/cloud/launch-checklist.

Last verified against https://craftcms.com/docs/cloud/migrating and https://craftcms.com/docs/cloud/launch-checklist on 2026-05-28.
