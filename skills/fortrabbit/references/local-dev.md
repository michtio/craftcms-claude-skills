# Local Development for fortrabbit Projects

fortrabbit has no first-party local environment and no `ddev pull` provider. DDEV is the common local stack for Craft on fortrabbit; set it up the normal way (see the `ddev` skill). Database and assets come down over SSH: `mysqldump` and `rsync`.

Local is where code, schema and plugin changes happen. They reach fortrabbit with a git push. Content flows the other way: production → local.

## Documentation

- DDEV on fortrabbit: https://docs.fortrabbit.com/integrations/local-development/ddev
- Craft install: https://docs.fortrabbit.com/guides/craft-cms/install
- Craft ENV vars: https://docs.fortrabbit.com/guides/craft-cms/env-vars
- Craft multi-environment config: https://craftcms.com/docs/5.x/configure.html

## DDEV setup

```sh
ddev config --project-type=craftcms --docroot=web
ddev start
```

Match the PHP version to the environment's PHP version in the dashboard (`php_version` in `.ddev/config.yaml`). The database is MySQL on fortrabbit: use a MySQL image locally (`database: type: mysql`), not MariaDB, so dumps import cleanly in both directions.

SSH from inside the container (for `ddev exec rsync` or Composer over SSH) needs the local keys:

```sh
ddev auth ssh
```

## Local `.env`

The environment's ENV vars come from the dashboard; locally Craft reads `.env`. The keys match, so the same config files work in both places:

```sh
CRAFT_ENVIRONMENT=dev
CRAFT_DEV_MODE=true
CRAFT_ALLOW_ADMIN_CHANGES=true
CRAFT_ALLOW_UPDATES=true
CRAFT_SECURITY_KEY=…       # same value as on fortrabbit when the database moves between them
PRIMARY_SITE_URL=https://my-project.ddev.site
```

`CRAFT_ENVIRONMENT` on fortrabbit holds the environment name, e.g. `production` or `staging`. Multi-environment config in `config/general.php` can key off it, see Craft's configuration docs.

## Pull production down

Database (see `database.md` for push and the tunnel):

```sh
ssh <env>@ssh.<region>.frbit.app \
  'mysqldump --single-transaction --set-gtid-purged=OFF --no-tablespaces "$FORTRABBIT_DB_NAME"' \
  | gzip > /tmp/<env>.sql.gz
ddev import-db --file=/tmp/<env>.sql.gz
ddev craft clear-caches/all
```

Assets (see `asset-storage.md`):

```sh
rsync -avz <env>@ssh.<region>.frbit.app:web/uploads/ ./web/uploads/
```

Both overwrite local data. Pulled dumps hold customer data: keep them outside the repo.

## Push up

Code, `composer.lock` and `config/project` go up with `git push`. Pushing the database or assets up is the exception (first launch, a migration): see `database.md` and `asset-storage.md`, and back up the environment first.

## Common Pitfalls

1. **MariaDB locally, MySQL on fortrabbit** — dumps carry engine-specific syntax and collations. Use MySQL in DDEV.
2. **Different PHP versions** — Composer resolves packages locally that fail in the build. Match `php_version` to the environment, or set `config.platform.php` in `composer.json`.
3. **Different security keys** — a database pulled down can't decrypt stored values. Use one `CRAFT_SECURITY_KEY` for local and the environments that share data.
4. **Editing schema on staging to "test it there"** — `CRAFT_ALLOW_ADMIN_CHANGES=false` blocks it. Make the change locally, push, let the post-deploy commands apply it.
5. **SSH keys missing in the container** — `Permission denied (publickey)` from `ddev exec`. Run `ddev auth ssh`.
