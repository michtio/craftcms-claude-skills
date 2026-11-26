---
name: ddev
description: "DDEV local development environment for Craft CMS projects. ALWAYS load this skill when running any ddev command, configuring .ddev/config.yaml, or troubleshooting local container issues. Covers config.yaml (project type, PHP/Node versions, database, docroot), shorthand commands, add-ons and built-in Mailpit, custom commands, Vite dev server exposure, database import/export, Xdebug toggling, sharing local sites, and troubleshooting (port conflicts, container restarts, ddev-injected env vars silently overriding your .env or config/general.php)."
when_to_use: "Triggers on: ddev start/stop/restart, ddev craft, ddev composer, ddev npm, ddev ssh, ddev import-db, ddev export-db, ddev craft db/backup, ddev xdebug on/off, ddev share, ddev add-on, ddev poweroff, ddev describe, ddev logs, ddev delete, .ddev/config.yaml, .ddev/commands/, web_extra_exposed_ports, web_extra_daemons, PHP version or Node version in local dev, port conflicts, container restart issues, database backup/restore locally, ran npm/composer on host instead of ddev, wrong node_modules architecture, local dev environment for Craft CMS, ddev-injected PRIMARY_SITE_URL, .ddev/.env.web regenerated on restart, CRAFT_ env var overriding config/general.php, general-config edit has no effect, ddev exec --dir, running a plugin's Pest suite inside a host project, ddev craft pest, tests wrote to the dev database. NOT for production deployment, CI/CD pipelines, GitHub Actions, or server configuration. NOT for Docker/container usage outside of DDEV."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# DDEV for Craft CMS Development

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

## Companion Skills — Always Load Together

When this skill triggers, also load:

- **`craftcms`** — Plugin/module development. Required when DDEV commands involve Craft CLI (`ddev craft make`, `ddev craft migrate`, `ddev craft project-config`).
- **`craft-php-guidelines`** — PHP coding standards. Required when DDEV commands involve code quality tooling (`ddev composer check-cs`, `ddev composer phpstan`, `ddev exec --dir … vendor/bin/pest`).

## Documentation

- DDEV docs: https://docs.ddev.com/en/stable/
- Craft CMS quickstart: https://docs.ddev.com/en/stable/users/quickstart/#craft-cms
- Configuration reference: https://docs.ddev.com/en/stable/users/configuration/config/
- Custom commands: https://docs.ddev.com/en/stable/users/extend/custom-commands/
- Additional services: https://docs.ddev.com/en/stable/users/extend/additional-services/
- Vite integration: https://docs.ddev.com/en/stable/users/usage/developer-tools/#nodejs

When unsure about a DDEV feature, `WebFetch` the relevant docs page.

## Common Pitfalls

- Using `ddev exec composer install` instead of `ddev composer install` — DDEV shorthand commands handle path resolution and environment setup. Always use the shorthand.
- Forgetting `ddev craft up` does both `migrate/all` and `project-config/apply` — no need to run them separately after pulls or deploys.
- Exposing the Vite dev server with `ports` instead of `web_extra_exposed_ports` — `ports` causes conflicts when running multiple DDEV projects. `web_extra_exposed_ports` routes through Traefik and works with HTTPS.
- Running `ddev composer global require` — global packages install inside the container and vanish on restart. Install project-level dependencies only.
- Setting `nodejs_version` but running `npm install` on the host — Node must run inside the container via `ddev npm` to match the configured version.
- Editing `.ddev/config.yaml` while containers are running without restarting — changes to config require `ddev restart` to take effect.
- Using `ddev import-db` without `--target-db=db` on multi-database setups — the default target is `db`, but if you've configured additional databases, be explicit.
- Adding `#ddev-generated` to custom commands you've customized — DDEV overwrites files with this comment during updates. Only use it for add-on-managed commands. Custom commands you maintain should omit it.
- Running `composer install` on the host then `ddev composer check-cs`/`ddev composer phpstan` — if the host PHP version differs from DDEV's (e.g., host PHP 8.4, DDEV PHP 8.3), `vendor/composer/platform_check.php` fails. Always run `ddev composer install` so `vendor/` matches the container's PHP version.

## Craft CLI First, Raw SQL Last

Always prefer Craft CLI commands over raw database queries:

```bash
ddev craft users/list-admins         # not: ddev mysql -e "SELECT * FROM users WHERE admin=1"
ddev craft project-config/get system # not: reading project.yaml manually
ddev craft resave/entries            # not: UPDATE queries on content tables
ddev craft elements/delete           # not: DELETE FROM elements
```

Only fall back to `ddev mysql` when no CLI equivalent exists (e.g., checking table schemas, debugging specific rows, `TRUNCATE cache` for stuck mutex locks). Craft CLI commands handle project config, search index updates, and event firing that raw SQL skips.

## Shorthand Commands

Always use DDEV shorthand over `ddev exec`:

```bash
ddev composer install          # not ddev exec composer install
ddev craft up                  # not ddev exec php craft up
ddev npm install               # not ddev exec npm install
ddev craft make service        # scaffolding
```

## Craft CMS Project Type

```yaml
# .ddev/config.yaml
name: my-craft-site
type: craftcms
docroot: web
php_version: "8.3"
database:
  type: mysql
  version: "8.0"
nodejs_version: "20"
```

DDEV auto-injects: `CRAFT_DB_SERVER`, `CRAFT_DB_USER`, `CRAFT_DB_PASSWORD`, `CRAFT_DB_DATABASE`, `PRIMARY_SITE_URL`. These are injected into the container via `.ddev/.env.web` and can be opted out of with `disable_settings_management: true` in `.ddev/config.yaml`.

## New Project Bootstrap

The canonical flow for a fresh DDEV + Craft project:

```bash
mkdir my-craft-site && cd my-craft-site
ddev config --project-type=craftcms --docroot=web   # writes .ddev/config.yaml
ddev start
ddev composer create-project craftcms/craft         # Craft's setup wizard runs automatically
```

`ddev composer create-project` launches Craft's interactive install wizard on completion. If it doesn't run (or you need to re-run it), use `ddev craft install`. Swap `craftcms/craft` for a community starter project to bootstrap from one instead.

## Common Commands

```bash
ddev start                     # Start the project
ddev stop                      # Stop the project
ddev restart                   # Restart containers
ddev ssh                       # SSH into web container
ddev describe                  # Show project info and URLs
ddev launch                    # Open the project in a browser
ddev launch -m                 # Open Mailpit (also --mailpit)
ddev logs                      # View container logs
ddev import-db --file=dump.sql # Import database
ddev export-db --file=dump.sql # Export database
ddev xdebug on                 # Enable Xdebug
ddev craft db/backup           # Craft database backup
```

## Post-Install Auto-Run

Composer scripts auto-run `craft up` after install/update:

```json
{
    "scripts": {
        "post-craft-update": [
            "@php craft install/check && php craft up --interactive=0 || exit 0"
        ],
        "post-update-cmd": "@post-craft-update",
        "post-install-cmd": "@post-craft-update"
    }
}
```

So `ddev craft up` (migrations plus project config) auto-runs after `ddev composer install/update`.

## Add-ons

```bash
ddev add-on get ddev/ddev-redis       # Install Redis
ddev add-on list                       # List installed add-ons
ddev add-on remove ddev/ddev-redis    # Remove add-on
```

Mailpit is built into DDEV core — no add-on installation needed. Outgoing mail is captured automatically. Access the web UI with `ddev mailpit`, or `ddev describe` shows its URL (e.g. `https://{project}.ddev.site:8026`).

## Sharing a Local Site

```bash
ddev share                     # Expose the project on a temporary public URL
```

Craft's MCP endpoint [5.12+] rejects `ddev share` hostnames (see `craft-mcp`).

`ddev share` defaults to the ngrok provider, which requires a free ngrok.com account and a configured ngrok auth token. (`cloudflared` is an alternative provider via `--provider=cloudflared`, no account required, but ngrok is the default.)

## Custom Commands

Place scripts in `.ddev/commands/web/` (container) or `.ddev/commands/host/` (host):

```bash
#!/usr/bin/env bash
## Description: Run ECS code style check
## Usage: check-cs
## Example: ddev check-cs

cd /var/www/html && composer check-cs
```

## Plugin Development and Plugin Test Suites

- **Composer path repos** need a matching volume mount: the `url` in `composer.json` is the host path, and `.ddev/docker-compose.mounts.yaml` mounts that same path at the same location in the container, or the symlink in `vendor/` points nowhere. Never set `config.platform.php` in `composer.json`; DDEV owns the PHP version.
- **Run a symlinked plugin's Pest suite from its own directory**: `ddev exec --dir /var/www/html/vendor/acme/my-plugin vendor/bin/pest`. `markhuot/craft-pest-core` reads `getcwd().'/phpunit.xml(.dist)'` only and ignores `--configuration=`, so `ddev craft pest -- --configuration=vendor/acme/my-plugin/phpunit.xml.dist` runs the tests against the project's live database. Treat that shared-root form as unsafe.

Setup steps, mount example and the full test-suite mechanism: `references/plugin-development.md`; isolation checklist and CI: the `craft-pest` skill (`references/isolation.md`).

## Craft's Own MCP Server [5.12+]

Craft 5.12 ships its own MCP server, so an MCP client can read and edit the local site's content as a Craft user. Not the same thing as Chrome DevTools MCP (`references/browser-debugging.md`). Setup (OAuth keys, Settings → MCP, the `claude mcp add --transport http` command, the stdio variant `ddev craft mcp/serve --user=<username>`), mkcert trust for the client and plugin tools live in the **`craft-mcp`** skill; load it instead of improvising. Two DDEV-specific facts: the HTTP endpoint only accepts the CP and site hosts (`*.ddev.site`, `localhost`), so a `ddev share` URL is rejected unless it is also a site base URL, and Craft MCP needs Craft 5.12 or later [5.12+] (Before 5.12: nothing to connect to; upgrade first).

## Troubleshooting

```bash
ddev poweroff                  # Stop all DDEV projects
ddev debug router              # Debug router configuration
ddev debug capabilities        # Check Docker capabilities
ddev delete --omit-snapshot    # Remove project without snapshot
```

### A general-config edit isn't taking effect (ddev-injected env var wins)

DDEV auto-injects Craft env vars (including `PRIMARY_SITE_URL`, and `CRAFT_DB_*`) into the container via `.ddev/.env.web`, and **regenerates that file on every `ddev start`/restart** unless `disable_settings_management: true` is set in `.ddev/config.yaml`. Because a real container environment variable beats a `cms/.env` dotenv value, and `CRAFT_*` env vars beat `config/general.php` (see the `craftcms` skill's `config-bootstrap.md`), a value you edit in `.env` or `general.php` can be silently overridden by what ddev injected.

Two symptoms and fixes:

- **Wrong site URL / scheme.** `PRIMARY_SITE_URL` follows ddev's primary URL, whose scheme is often `http`; if Craft resolves an unexpected base URL, that injected var is the likely source. Point Craft's site URL at a **differently-named** env var (e.g. `SITE_URL`) in your site config so ddev's `PRIMARY_SITE_URL` doesn't shadow it, or override `PRIMARY_SITE_URL` deliberately.
- **A `.env` change reverts after restart.** If you edited `.ddev/.env.web` by hand, it's regenerated on restart — put durable overrides in `.ddev/config.yaml` (`web_environment`) or set `disable_settings_management: true` to own the file yourself.

When a config value "won't change," check the resolved environment (`ddev exec printenv | grep CRAFT_`, and `.ddev/.env.web`) before editing PHP again.

## Reference Files

| Reference | ~Tokens | Scope |
|-----------|---------|-------|
| `references/plugin-development.md` | ~850 | Composer path repos and volume mounts for local plugin development; running a plugin's own Pest suite with `ddev exec --dir` and why `--configuration=` is unsafe. |
| `references/browser-debugging.md` | ~680 | Chrome DevTools MCP: installation, capabilities, when to use it, logging into the CP on a DDEV site, project-level setup. |

Task examples: "symlink a local plugin into the project" or "run my plugin's tests" → `plugin-development.md`; "inspect the CP / check console errors in a browser" → `browser-debugging.md`.
