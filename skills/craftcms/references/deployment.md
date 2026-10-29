# Deployment Patterns

How to deploy Craft CMS 5 to production: the standard pipeline, project config deployment, zero-downtime strategies, CI/CD, post-deploy steps, and rollback. For environment variables and config loading, see `config-bootstrap.md`. For general config settings, see `config-general.md`.

## Documentation

- Deployment: https://craftcms.com/docs/5.x/deploy.html
- Project config: https://craftcms.com/docs/5.x/system/project-config.html

## Common Pitfalls

- Using `craft migrate/all` instead of `craft up` — misses project config apply. `craft up` runs all pending migrations AND applies project config YAML.
- Forgetting `--interactive=0` in CI/CD — Craft CLI commands prompt for confirmation by default. Without this flag, CI pipelines hang.
- Varying `disabledPlugins` per environment — causes schema version mismatches that break `craft up` on deploy. Disabled plugins must be consistent across all environments.
- Not stopping the queue worker before migrations — in-flight jobs may use outdated schema. Stop the listener, run migrations, restart.
- Setting `allowAdminChanges(true)` in production — allows CP users to modify sections, fields, and plugins, causing project config drift that conflicts with the next deploy.
- Running `project-config/write` on a local DB restored from an older dump -- it empties `config/project/` and rewrites it from the DB, deleting YAML committed since the dump. Gate it with `craft up` and a clean `project-config/diff`. See [project-config/write safely](#project-configwrite-safely).
- Running `project-config/rebuild` to fix drift — rebuilds YAML from DB, overwriting your Git-tracked config. Only use when you intentionally want the DB to be the source of truth.

## Contents

- [Standard Deploy Pipeline](#standard-deploy-pipeline)
- [Production Config Baseline](#production-config-baseline)
- [Project Config Commands](#project-config-commands)
- [Zero-Downtime (Atomic) Deploys](#zero-downtime-atomic-deploys)
- [CI/CD Patterns](#cicd-patterns)
- [Post-Deploy Steps](#post-deploy-steps)
- [Rollback Strategies](#rollback-strategies)
- [Environment Management](#environment-management)
- [Hosting Platforms](#hosting-platforms)

## Standard Deploy Pipeline

```
Build → Release → Migrate → Clear Caches → Swap
```

1. `composer install --no-dev --optimize-autoloader`
2. `npm run build` (Vite, if applicable)
3. Stop queue worker
4. `php craft up --interactive=0`
5. `php craft clear-caches/all`
6. Swap symlink (atomic deploys) or restart web server
7. Restart queue worker

`craft up` is the single deploy command — it runs all pending migrations (every track) first, then applies project config YAML.

## Production Config Baseline

```php
// config/general.php
use craft\config\GeneralConfig;

return GeneralConfig::create()
    ->allowAdminChanges(false)   // Project config is read-only
    ->allowUpdates(false)         // No plugin/Craft updates from CP
    ->runQueueAutomatically(false) // Use daemon instead
    ->buildId(App::env('BUILD_ID'))
    ->enableTemplateCaching(true)
    ->devMode(false);
```

`allowAdminChanges(false)` is the critical setting — all structural changes (sections, fields, entry types, plugins) flow one direction: dev CP → YAML → Git → deploy → `craft up`.

## Project Config Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `craft up` | Runs all migrations + applies project config | **Every deploy** |
| `craft project-config/apply` | Applies YAML to DB (no migrations) | Emergency re-sync when you know no migrations are pending |
| `craft project-config/apply --force` | Treats every YAML value as changed and re-applies all of it | Stubborn drift that `apply` alone doesn't fix |
| `craft project-config/touch` | Sets `dateModified` in `project.yaml` to now | After manual YAML edits, merge conflict resolution |
| `craft project-config/diff` | Shows YAML changes that are not yet in the DB (`--invert` for the other direction) | Before `write`, diagnosing drift |
| `craft project-config/rebuild` | Rebuilds the config from the DB's component tables (sections, fields, …) | When DB is the source of truth (destructive to YAML) |
| `craft project-config/write` | Empties `config/project/` and rewrites it from the DB's stored config | Rarely; behind the gate in [project-config/write safely](#project-configwrite-safely) |

### project-config/write safely

`write` is `ProjectConfig::regenerateExternalConfig()`, which ends in `writeYamlFiles(true)`. That method **clears the `config/project/` directory** (everything except dotfiles) and rewrites it from the config stored in the DB. Any YAML the DB doesn't know about is deleted, and any YAML value the DB has older is reverted.

On a local DB restored from a production dump, the DB is behind the branch. Running `write` there deletes teammates' new fields, their layout elements, and anything else committed since the dump. Nothing warns you.

Gate it:

```bash
ddev craft up                        # bring the DB up to the branch's YAML first
ddev craft project-config/diff       # must print "No pending project config YAML changes."
ddev craft project-config/write
git diff --stat -- config/project    # only the files you meant to change
```

If `diff` shows anything after `craft up`, stop: the YAML is ahead of the DB and `write` would undo it. If `git diff` touches files you didn't mean to change, `git restore` them before committing.

You rarely need `write` at all. With `allowAdminChanges` on and `writeYamlAutomatically` at its default (`true`), the CP already writes YAML when you save. Run `git diff -- config/project` first.

**Small settings changes:** a layout element's required flag, a tip or instructions string, a dropdown option. These are safest as a direct edit to the YAML file, then:

```bash
ddev craft up                        # applies the edit; a YAML error fails here
ddev craft project-config/diff       # "No pending project config YAML changes." proves it was applied
```

`craft up` decides whether to apply by comparing content: it calls `areChangesPending(force: true)`. So a hand edit is picked up without bumping `dateModified`. The bump (`project-config/touch`) still matters for the CP's "pending changes" alert. That check skips the content comparison when `project.yaml`'s mtime matches the cached one, so an edit to a file under `config/project/` alone won't raise it.

Code-driven schema changes (saving a field or entry type from PHP) belong in a migration or a console command; see `migrations.md` → "Project config writes outside a request".

Source: `craftcms/cms` 5.11.5.1 -- https://github.com/craftcms/cms/blob/5.11.5.1/src/services/ProjectConfig.php (`regenerateExternalConfig()` 594-606, `areChangesPending()` 690-735, `writeYamlFiles()` 1631-1650), https://github.com/craftcms/cms/blob/5.11.5.1/src/console/controllers/UpController.php (line 60), https://github.com/craftcms/cms/blob/5.11.5.1/src/console/controllers/ProjectConfigController.php (`actionWrite()` 421-427), https://github.com/craftcms/cms/blob/5.11.5.1/src/helpers/Cp.php (lines 204-213). Docs: https://craftcms.com/docs/5.x/system/project-config.html and https://craftcms.com/docs/5.x/reference/cli.html

### rebuild vs apply --force — know the direction

These two commands fix drift but in **opposite directions**:

| Command | Direction | Destructive to | Use when |
|---------|-----------|----------------|----------|
| `project-config/apply --force` | YAML → DB | Database | YAML is correct, DB has drifted |
| `project-config/rebuild` | DB → YAML | YAML files | DB is correct, YAML has drifted |

Always run `project-config/diff` first to understand what diverged. Choosing the wrong direction overwrites the correct state with the stale one.

### Migration ordering

Migrations use timestamp format (`m{YYMMDD}_{HHMMSS}_description.php`). Each plugin has its own track (triggered by `schemaVersion` changes). Content migrations have a separate global track. `craft up` runs all tracks, then applies project config.

**Rule:** Let migrations own data transformations. Let YAML own structural config. If a migration creates a section and YAML also defines it, the apply step conflicts.

## Zero-Downtime (Atomic) Deploys

```
/var/www/
  releases/
    20260419-001/
    20260419-002/        ← new release
  shared/
    .env
    storage/
    web/cpresources/
  current -> releases/20260419-002/  (symlink, swapped atomically)
```

### Shared directories

Symlink from `shared/` into each release:

| Directory | Why Shared |
|-----------|-----------|
| `.env` | Environment-specific, never in Git |
| `storage/` | Logs, backups, runtime cache, session files |
| `web/cpresources/` | CP assets that persist across deploys |

### Deploy sequence

```bash
#!/bin/bash
RELEASE="/var/www/releases/$(date +%Y%m%d-%H%M%S)"

# 1. Build
git clone --depth 1 "$REPO" "$RELEASE"
cd "$RELEASE"
composer install --no-dev --optimize-autoloader
npm ci && npm run build

# 2. Link shared resources
ln -sf /var/www/shared/.env "$RELEASE/.env"
ln -sf /var/www/shared/storage "$RELEASE/storage"
ln -sf /var/www/shared/web/cpresources "$RELEASE/web/cpresources"

# 3. Migrate
supervisorctl stop craft-queue
php "$RELEASE/craft" up --interactive=0
php "$RELEASE/craft" clear-caches/all

# 4. Swap
ln -sfn "$RELEASE" /var/www/current

# 5. Restart
supervisorctl start craft-queue
```

The symlink swap is atomic on Linux — no requests see a partial state.

### Queue workers during deploy

Stop the listener before migrations, restart after the swap. Database queue jobs survive across deploys (shared DB). Redis queue jobs also survive (external to filesystem).

## CI/CD Patterns

### GitHub Actions

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install PHP dependencies
        run: composer install --no-dev --optimize-autoloader

      - name: Build assets
        run: npm ci && npm run build

      - name: Run quality checks
        run: |
          vendor/bin/ecs check
          vendor/bin/phpstan analyse

      - name: Deploy
        run: |
          # rsync, SSH, or platform-specific deploy command
          ssh $SERVER "cd /var/www && ./deploy.sh"
```

Pass `--interactive=0` to all `craft` commands in CI. Use `php -l` for syntax checking, but ECS and PHPStan are the real quality gates.

### Build artifacts

Vite produces content-hashed filenames — no need for `revAssetUrls`. Commit the build manifest (`web/dist/.vite/manifest.json`) or build during deploy.

## Post-Deploy Steps

| Step | Command | When |
|------|---------|------|
| Migrations + config | `craft up --interactive=0` | Every deploy |
| Clear caches | `craft clear-caches/all` | Every deploy |
| Restart queue | `supervisorctl restart craft-queue` | Every deploy |
| Rebuild search index | `craft resave/entries --update-search-index --queue` | After content modeling changes |
| Full search rebuild | `craft db/search-indexes` | After changing search component config |
| Asset indexing | `craft index-assets/all` | After adding files outside Craft |
| Cache warming | Blitz cache warmer or custom | After Blitz purge |

## Rollback Strategies

### Atomic deploys

Swap the `current` symlink back to the previous release directory. Fast and safe for code-only issues. However, **database changes cannot be un-swapped** — migrations that ran are permanent unless `safeDown()` is implemented.

### Migration rollback

`craft migrate/down` rolls back the last content migration. Only works if `safeDown()` returns `true`. Data transformations (UPDATE/DELETE) are generally non-reversible. Schema-only changes (addColumn, createTable) can be reversed.

### Pre-deploy backup

Always run `craft db/backup` before risky deploys. Backups go to `storage/backups/`. For atomic deploys, automate this in the deploy script before `craft up`.

### Failed migrations

Can leave mutex locks in the `cache` table. To recover:

```sql
TRUNCATE TABLE cache;
```

Then fix the migration and re-run `craft up`.

### Project config drift

```bash
craft project-config/diff    # See what diverged
craft project-config/apply   # YAML → DB (destructive to DB)
craft project-config/rebuild  # DB → YAML (destructive to YAML)
```

Choose direction carefully. `diff` first, always.

## Environment Management

Use `CRAFT_ENVIRONMENT` env var to drive per-environment behavior:

| Setting | Dev | Staging | Production |
|---------|-----|---------|-----------|
| `devMode` | `true` | `false` | `false` |
| `allowAdminChanges` | `true` | `false` | `false` |
| `enableTemplateCaching` | `false` | `true` | `true` |
| `runQueueAutomatically` | `true` | `false` | `false` |
| `testToEmailAddress` | — | `staging@example.com` | — |

### The .env file

Never committed to Git. Unique per environment. Contains:

```
CRAFT_APP_ID=my-site
CRAFT_ENVIRONMENT=production
CRAFT_SECURITY_KEY=<unique-per-environment>
CRAFT_DB_DSN=mysql:host=localhost;port=3306;dbname=craft
CRAFT_DB_USER=craft
CRAFT_DB_PASSWORD=<secret>
CRAFT_DEV_MODE=false
```

Every `GeneralConfig` property maps to `CRAFT_UPPER_SNAKE_CASE` automatically.

## Hosting Platforms

| Platform | Deploy Method | Queue | Notes |
|----------|--------------|-------|-------|
| **Laravel Forge** | Git push + deploy script | Daemon via supervisor | Add `craft up` to deploy script manually |
| **Ploi** | Git push + deploy hook | Built-in daemon | Native zero-downtime support |
| **Servd** | Git push | Managed | Handles `craft up` automatically |
| **Docker/K8s** | Container image | Sidecar or init container | Run `craft up` as init container. Shared storage (S3, Redis) mandatory. |
| **Craft Cloud** | Git push | Managed (auto-processed) | Build → Migrate → Release pipeline, Cloudflare Images for transforms, edge static caching, MySQL 8 / Postgres 15 only. Full surface in the **`craft-cloud`** skill — different enough from generic Craft deployment that none of the patterns in this file apply directly. |
