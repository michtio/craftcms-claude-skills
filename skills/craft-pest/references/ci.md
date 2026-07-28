# CI for a Plugin Test Suite

A suite that isn't in CI doesn't exist. It rots at the speed of the codebase, and the first person to notice is whoever inherits it. Two mistakes account for most of the gap: no test job at all, and a style step that "fixes" instead of failing.

For the full `code-analysis.yaml` workflow (PHP matrix, Composer caching, `--no-blocking`, the release workflow), see the `craftcms` skill's `quality.md`. This file covers what's specific to the **test** job.

## Contents

- `check-cs`, never `fix-cs`
- The test job itself
- Invocation from the plugin's own root
- Database service and the test database
- Verifying against a fresh database

## `check-cs`, never `fix-cs`

```yaml
- name: Coding Standards
  run: composer check-cs        # NOT fix-cs
```

`fix-cs` in CI rewrites files inside the runner and exits `0`. The job goes green, the violations never reach anyone's attention, and the fixes are discarded when the runner is torn down. The whole point of the step is to **fail** on a violation so it gets fixed in the branch. Auto-fixing belongs on a developer's machine (`ddev composer fix-cs`, scoped to changed files) or in a pre-commit hook.

Same logic applies to any `--fix`-style flag in a CI quality step.

## The test job itself

Static analysis first (seconds), tests last (minutes) — fail fast on cheap signals:

```yaml
      - name: PHPStan
        run: composer phpstan
      - name: Coding Standards
        run: composer check-cs
      - name: Pest
        run: composer test
```

`composer test` (rather than a raw `vendor/bin/pest` with flags) is deliberate: it keeps the invocation identical between CI and a developer's machine, so a suite that passes locally is running the same way in CI.

## Invocation from the plugin's own root

This is the CI-side of the cwd-bound `<env>` mechanism described in `isolation.md`. For a plugin repo, the checkout *is* the plugin root, so `composer test` at the default working directory is already correct — nothing to do.

Where it goes wrong is a **monorepo or host-project workflow** that runs the suite from the project root:

```yaml
# WRONG — getcwd() is the project root, so the plugin's <env> DB pins never load
- run: vendor/bin/pest -c vendor/acme/my-plugin/phpunit.xml.dist

# Right — run from the plugin's own directory
- run: composer test
  working-directory: vendor/acme/my-plugin
```

`working-directory` is the fix. Without it the suite runs against whatever database the project's environment resolves to, which in CI is usually harmless and in a deploy-adjacent pipeline is not.

## Database service and the test database

The suite needs a MySQL (or Postgres) service and the test database to exist before Pest boots:

```yaml
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: db_test
        ports: ['3306:3306']
        options: >-
          --health-cmd="mysqladmin ping" --health-interval=10s
          --health-timeout=5s --health-retries=5

    env:
      CRAFT_DB_SERVER: 127.0.0.1
      CRAFT_DB_USER: root
      CRAFT_DB_PASSWORD: root
      CRAFT_DB_DATABASE: db_test
      CRAFT_SECURITY_KEY: ci-only-not-a-secret
```

`MYSQL_DATABASE` creates it, so no separate create step is needed.

The env vars here are the *outer* environment, and they are what supplies the **connection coordinates** — `CRAFT_DB_SERVER: 127.0.0.1` is correct for a GitHub Actions service container and wrong inside DDEV. That division of labour only works if the suite's `phpunit.xml.dist` declares those variables with `default="true"` rather than forcing them; a forced local hostname (`value="db"`) overrides this block and the job can't connect. See `isolation.md` (Force the database name, default everything else) — if you find yourself adding an `/etc/hosts` alias so `db` resolves on the runner, fix the `<env>` entry instead.

The suite still decides its own **database name**: the `phpunit.xml.dist` pin and `tests/bootstrap.php` apply on top, and the bootstrap pins win (set last, before Craft boots), which is the behavior you want.

`CRAFT_SECURITY_KEY` must be set to something or Craft's install will generate one per run; a fixed dummy value keeps runs comparable.

## Verifying against a fresh database

CI is where the fresh-database path actually gets exercised — every run starts empty, so CI is the natural guard against the `Install.php`/migration drift described in `shared-state.md`. Two things follow:

- **Don't cache the test database between runs.** The empty start is a feature.
- **When CI fails and local passes, believe CI.** The difference is almost always ambient local data: a test asserting on rows it didn't create, or a schema change that only landed in `Install.php`.

If you want the guard locally too, add a script that recreates the database before running:

```json
{
    "scripts": {
        "test": "pest",
        "test:fresh": [
            "mysql -h db -u root -proot -e 'DROP DATABASE IF EXISTS db_test; CREATE DATABASE db_test;'",
            "@test"
        ]
    }
}
```

Run `test:fresh` after any schema change and before believing a green suite; keep plain `test` for the fast inner loop.
