# Plugin Development in DDEV

Developing Craft plugins locally inside a DDEV host project: symlinking a plugin into `vendor/` through a Composer path repository with a matching volume mount, and running the plugin's own Pest suite from its directory so its database isolation actually applies.

## Contents

- [Composer Path Repos and Volume Mounts](#composer-path-repos-and-volume-mounts)
- [Running a Plugin's Own Test Suite](#running-a-plugins-own-test-suite)

## Composer Path Repos and Volume Mounts

When developing plugins locally, Composer path repos symlink the plugin into `vendor/`. For this to work inside DDEV's Docker container, the host path must be volume-mounted so the symlink resolves.

### Setup

1. **composer.json** — use the local host path:

```json
{
    "repositories": [
        {
            "type": "path",
            "url": "/Users/Shared/dev/craft-plugins/v5/*"
        }
    ]
}
```

2. **docker-compose override** — mount the same path into the container. Create `.ddev/docker-compose.mounts.yaml`:

```yaml
services:
  web:
    volumes:
      - /Users/Shared/dev/craft-plugins:/Users/Shared/dev/craft-plugins
```

The mount path inside the container must match the host path exactly — Composer creates absolute symlinks that must resolve in both contexts. Replace `/Users/Shared/dev/craft-plugins` with your actual plugin directory path.

3. **Require the plugin**: `ddev composer require vendor/plugin-handle:@dev`

### Common mistakes

- Using a Docker-internal path in `composer.json` `url` — the path must be the host filesystem path, not `/var/www/...`
- Forgetting the volume mount — `ddev composer install` succeeds but the symlink points nowhere inside the container
- Setting `"platform": {"php": "8.3"}` in `composer.json` `config` — don't. DDEV handles the PHP version via `.ddev/config.yaml`. Platform overrides cause dependency resolution mismatches between host and container, and prevent DDEV from managing version upgrades cleanly.

## Running a Plugin's Own Test Suite

When a plugin is symlinked into a host project, run its suite **from the plugin's own directory** inside the container:

```bash
ddev exec --dir /var/www/html/vendor/acme/my-plugin vendor/bin/pest
ddev exec --dir /var/www/html/vendor/acme/my-plugin composer test
```

`--dir` sets the working directory, and that is the load-bearing part. `markhuot/craft-pest-core` reads its environment overrides from `getcwd().'/phpunit.xml(.dist)'` only — it does **not** parse a `--configuration=` flag. So the shared-root form:

```bash
# UNSAFE — runs the tests, but against the project's live database
ddev craft pest -- --configuration=vendor/acme/my-plugin/phpunit.xml.dist
```

…discovers and executes the plugin's tests while silently ignoring the plugin's own `CRAFT_DB_DATABASE` pin. Combined with a suite that hasn't bound the `RefreshesDatabase` trait (rollback is opt-in), that writes test data permanently into your development database. Treat the shared-root invocation as unsafe for any craft-pest-core suite.

The full mechanism, the isolation checklist, and the CI equivalent are in the `craft-pest` skill (`references/isolation.md`).

For plugins mounted via a Composer path repo, the `--dir` path is the symlink target inside the container — see [Composer Path Repos and Volume Mounts](#composer-path-repos-and-volume-mounts) above for making that path resolve.
