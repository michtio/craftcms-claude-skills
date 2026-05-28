# Local Development for Cloud Projects

DDEV is the recommended local stack. The Cloud extension stays installed locally but doesn't activate, so your local environment stays untouched. Match the PHP and DB versions in your DDEV config to whatever `craft-cloud.yaml` declares for Cloud.

## Documentation

- Local development: https://craftcms.com/docs/cloud/local-dev
- DDEV setup (general): see the `ddev` skill in this repo

## Common Pitfalls

- Adding `db.php` with hardcoded credentials for both Cloud and local. Cloud auto-wires its own connection; the file conflicts. Use `CRAFT_DB_*` env vars in `.env` for local-only DB config; remove `db.php` entirely.
- Running `npm` or `composer` on the host instead of inside DDEV. Wrong architecture binaries (especially `node_modules` native deps) cause Cloud's build to fail in ways that don't reproduce locally.
- Pointing the local Cloud filesystem at a non-existent path. The local-filesystem fallback section needs Base Path + Base URL that match wherever your dev assets actually live.
- Setting `CRAFT_EPHEMERAL=true` locally and expecting normal Craft writes to keep working. The flag is a signal, not enforcement — but plugin code that gates on `App::isEphemeral()` will start using the Path service, which works locally too. Useful for testing the ephemeral code paths without deploying.
- Trying to mirror Cloud's edge layer (Cloudflare, Cloudflare Images) locally. Don't — it's not realistic and not necessary. Use a local-filesystem fallback for assets and stop worrying about CDN parity in dev.

## DDEV setup

The minimum DDEV config to align with Cloud:

```yaml
# .ddev/config.yaml
php_version: "8.3"          # match craft-cloud.yaml php-version
database:
  type: mysql               # or postgres, matching your Cloud project
  version: "8.0"            # match Cloud — MySQL 8.0 or Postgres 15
nodejs_version: "20"        # match craft-cloud.yaml node-version if you have one
```

Then:

```sh
ddev start
ddev composer install
ddev npm install   # if you have a JS build
ddev craft setup
```

See the `ddev` skill for the broader DDEV setup and shorthand commands.

## How the Cloud extension behaves locally

The `craftcms/cloud` package stays installed locally — don't remove it. The extension self-detects when it's running outside Cloud and no-ops most of its overrides:

- Cache, mutex, queue, session, assetManager — left to your local app.php / .env config.
- Database wiring — falls back to your local `CRAFT_DB_*` env vars.
- Filesystem — the Cloud filesystem type uses its "Local Filesystem" fallback section instead of hitting S3.
- Log target — falls back to file-based logs.

You can leave it installed in `composer.json` (and you should — Cloud builds the same code that's in version control). Don't `composer remove craftcms/cloud` in local dev.

## Database configuration for local

**Don't use `db.php` for Cloud projects.** Cloud's auto-wiring conflicts with file-based config. Instead:

1. Leave `db.php` deleted (or wrap its contents in `if (!App::env('CRAFT_CLOUD'))`).
2. Set DB connection in `.env` for local-only:
   ```sh
   CRAFT_DB_DRIVER=mysql
   CRAFT_DB_SERVER=db
   CRAFT_DB_PORT=3306
   CRAFT_DB_DATABASE=db
   CRAFT_DB_USER=db
   CRAFT_DB_PASSWORD=db
   ```
3. Document in `.env.example` so the rest of the team can replicate.

DDEV's defaults (`db` for host/user/password/database) work out of the box.

## Filesystem configuration for local

The Cloud filesystem type in the CP has a **Local Filesystem** section. Populate it for dev:

| Setting | Local dev value |
|---|---|
| Base Path | `@webroot/uploads/{handle}` (or wherever your dev assets live) |
| Base URL | `@web/uploads/{handle}` |

Cloud's filesystem reads from S3 in production; locally it reads from this fallback path. New uploads write to the fallback path locally, then sync to S3 only on deploy (when the Cloud extension activates).

For `cloud.artifactUrl()` and similar webroot helpers, use `Craft::getAlias('@webroot')` — the extension's `@artifactBaseUrl` alias resolves to local paths in dev.

## Database restore from a Cloud backup

Download the backup file from Console (Databases → Backups → Download), then:

### MySQL

Craft's built-in restore command works:

```sh
ddev craft db/restore /path/to/backup.sql
```

The dump's MySQL version should be close to your local MySQL version (matching the minor version is safest — Cloud's MySQL 8.0 dump restores cleanly into DDEV's MySQL 8.0).

### Postgres

`pg_restore` is required (the `db/restore` command targets MySQL). Run from inside DDEV:

```sh
ddev exec pg_restore --host=db --username=db --dbname=db \
  --no-owner --clean --single-transaction --if-exists --no-acl \
  /path/to/backup.dump
```

Same flag set as in production (see `database.md`).

## Optional: testing ephemeral code paths

Plugin code that gates on `App::isEphemeral()` won't exercise that branch locally because the flag is unset. To test the ephemeral path without deploying:

```sh
# In .env (local only)
CRAFT_EPHEMERAL=true
```

Code that branches on `App::isEphemeral()` now uses the Path service locally too. This lets you smoke-test the ephemeral branch — the Path service works fine in DDEV, so no real disruption.

Unset when you're done testing — leaving it on permanently isn't harmful, but it's not realistic.

## What you don't need to mirror locally

- **Edge static caching.** Use Craft's `{% cache %}` for local equivalence; the edge layer kicks in only when deployed.
- **Edge image transforms.** Cloud's transforms run on Cloudflare; locally you use Craft's native image transformer. Same template code, different backend.
- **Cloud's automatic queue processing.** Locally, run the queue worker manually (`ddev craft queue/listen`) or let Craft's default queue runner drive it. Cloud's auto-processor only activates in production.
- **Cloud's logger.** Local logs go to `storage/logs/` as normal. The Cloud log target activates only on Cloud.
- **DNS.** Use DDEV's automatic local domain (`yourproject.ddev.site`); the edge layer isn't in the picture.

## Workflow

A typical day:

1. `ddev start` — DDEV containers come up.
2. Work normally — edit templates, write plugin code, test in browser.
3. Commit and push.
4. Cloud deploys automatically (if On Push) or wait for the manual trigger.
5. Verify on the preview URL.

The Cloud extension never gets in your way locally; it just sits there waiting to take over when the code ships to production.

Last verified against https://craftcms.com/docs/cloud/local-dev on 2026-05-28.

> **Note:** The DDEV recipe above (especially the env-var-based DB config pattern and the `CRAFT_EPHEMERAL` test toggle) is community-knowledge synthesis from the Cloud docs and the `craftcms/cloud-extension-yii2` source — Pixel & Tonic's docs cover the high-level "use DDEV" guidance but don't prescribe a full config template. Verify against your project's needs.
