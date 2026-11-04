# Deploy & Environments — Git Push, Template, Deploy File

How a git push becomes a deployment on fortrabbit, what the Craft CMS software template configures, how the deploy file replaces the dashboard settings, and how ENV vars and production settings work per environment.

## Documentation

- Craft setup: https://docs.fortrabbit.com/guides/craft-cms/setup
- Craft deployment: https://docs.fortrabbit.com/guides/craft-cms/deployment
- Craft ENV vars: https://docs.fortrabbit.com/guides/craft-cms/env-vars
- Craft domain setup: https://docs.fortrabbit.com/guides/craft-cms/domain-setup
- Craft production settings: https://docs.fortrabbit.com/guides/craft-cms/production-settings
- Updating Craft: https://docs.fortrabbit.com/guides/craft-cms/updating
- Software templates: https://docs.fortrabbit.com/platform/concepts/software-templates
- Deployment strategy: https://docs.fortrabbit.com/platform/deployment/strategy
- Replace patterns: https://docs.fortrabbit.com/platform/deployment/replace-patterns
- Deploy file: https://docs.fortrabbit.com/platform/deployment/deploy-file
- Deploy hook: https://docs.fortrabbit.com/platform/deployment/deploy-hook
- CLI: https://docs.fortrabbit.com/platform/automation/cli
- MCP server: https://docs.fortrabbit.com/platform/automation/mcp
- ENV vars: https://docs.fortrabbit.com/platform/settings/env-vars

## Contents

- [Apps and environments](#apps-and-environments) — the object model and hostnames
- [How deployments work](#how-deployments-work) — trigger, build, post-deploy
- [The Craft software template](#the-craft-software-template) — what it sets
- [Merge strategy and replace patterns](#merge-strategy-and-replace-patterns) — why uploads survive
- [The deploy file](#the-deploy-file) — deployment settings as code
- [ENV vars](#env-vars) — template vars, platform variables, multi-environment config
- [Production settings](#production-settings) — dev mode, admin changes, updates
- [Updates and upgrades](#updates-and-upgrades) — local first, then deploy
- [Common Pitfalls](#common-pitfalls)

## Apps and environments

- An **app** groups one or more **environments**, e.g. `production` and `staging`. Each environment has an ID `en-xxxxxx`, its own components (PHP, MySQL, storage, jobs), ENV vars, SSH access and git branch.
- Default domain: `https://<env>.<region>.frbit.app`. It forwards to the main domain, a cloud domain `https://<label>.frbit.cloud` or a custom domain.
- SSH: `<env>@ssh.<region>.frbit.app`. The MySQL database name and user are the environment ID.
- The region is fixed at app creation.

Staging and production are separate environments with separate databases and storage. Content flows down (production → local) by syncing; schema and code flow up through git.

## How deployments work

1. The repository is connected through the **fortrabbit GitHub App**. With the app installed, fortrabbit detects Craft from the repository when the app is created.
2. A `git push` to the environment's branch starts a deployment. The dashboard deploy button deploys the latest commit of the branch again. A **deploy hook** URL (a secret, set up in the dashboard) lets CI trigger a deployment.
3. **Build commands** run first. Composer runs here: don't commit `vendor/` and don't run Composer in a CI action as well.
4. The build result goes into the environment's storage according to the **deployment strategy**.
5. **Post-deploy commands** run once the new code is live. A failing post-deploy command does not roll back: the new code is already serving. Fix and push again, or run the command over SSH.

Follow a deployment with `frbit deployments list --environment <env>` and read a failed one with `frbit deployments logs <dp>` (MCP: `get_deployment`, `get_deployment_logs`). `frbit environments deploy <env>` deploys the latest commit again, e.g. from CI with `FRBIT_TOKEN` set, as an alternative to the deploy hook.

Only pushed commits deploy. Uncommitted or unpushed local work never reaches the environment. An older commit is deployed by reverting in git and pushing.

Without git, code can be uploaded with rsync or SFTP. Then no build or post-deploy commands run: run `php craft up` over SSH afterwards.

## The Craft software template

Choosing Craft CMS (or having it detected) applies the template for Craft 3, 4 and 5:

| Setting | Value |
|---|---|
| Root path | `web` |
| Strategy | `merge` |
| Replace patterns | `/config/project` |
| Exclude patterns | `/node_modules` |
| Build commands | `composer install --no-dev --prefer-dist --no-interaction --no-ansi --no-progress` |
| Post-deploy commands | `php craft migrate/all`, `php craft project-config/apply`, `php craft clear-caches/all` |

Add `npm ci` and `npm run build` to the build commands when the repo has a `package.json` and a lock file. Node.js runs during the build only, not at runtime.

The post-deploy commands do nothing when no migrations or project config changes are pending, so they are safe on every deployment.

Craft 6 apps get a different, Laravel-based template (root path `public`, `php artisan craft:up`); this skill covers Craft 4 and 5.

## Merge strategy and replace patterns

The **merge** strategy copies the build over the storage and deletes nothing:

- Files in the build overwrite their copies.
- Files on the environment that are not in the build stay: uploads in local volumes, transforms, runtime files.
- Files deleted in git stay too. The **replace pattern** `/config/project` deletes that folder before the copy, so a project config file removed from git is removed on the environment, and `project-config/apply` doesn't re-apply it.

The **replace** strategy makes the storage an exact copy of the build. With it, every local asset volume needs an **exclude pattern**, e.g. `/web/uploads`, or it is deleted on the next deployment.

## The deploy file

A deploy file holds the deployment settings in the repository: `.fortrabbit/deploy.yml`, `.fortrabbit/deploy.yaml` or `.fortrabbit/deploy.json`, first one found wins. fortrabbit marks it as a new feature; the format may still change.

The template settings as a deploy file:

```yaml
apiVersion: 1.0
build:
  buildCommands:
    - composer install --no-dev --prefer-dist --no-interaction --no-ansi --no-progress
  postDeployCommands:
    - php craft migrate/all
    - php craft project-config/apply
    - php craft clear-caches/all
distribution:
  strategy: merge
  replacePatterns:
    - /config/project
  excludePatterns:
    - /node_modules
```

Rules that bite:

- When the deployed branch has a deploy file, it is the **only** source for these settings. The dashboard shows them read-only.
- A key left out falls back to its default, **not** to the dashboard value: no build commands, no post-deploy commands, nothing cached, repository root, `replace` strategy, nothing excluded.
- `.` and `..` path segments are invalid in `gitSourceDirectory` and `cachedDirectories`. Leave `gitSourceDirectory` out for the repository root.
- `apiVersion` is required. Unknown keys, empty strings or a wrong `strategy` value make the file invalid; an invalid file fails the deployment before the build, and the code on the environment stays as it was.
- `replacePatterns` only apply with `strategy: merge`.
- A change to the file deploys with the next push. Redeploying the same commit doesn't pick it up.
- Deleting the file and pushing brings the dashboard settings back.
- Branch, deploy hook, PHP version and Node.js version stay in the dashboard.

## ENV vars

The template sets these ENV vars on the environment. There is no `.env` on the server; the local `.env` stays out of git.

```sh
CRAFT_ENVIRONMENT=${FORTRABBIT_ENVIRONMENT_NAME}
CRAFT_DEV_MODE=false
CRAFT_ALLOW_ADMIN_CHANGES=false
CRAFT_ALLOW_UPDATES=false
CRAFT_SECURITY_KEY=…                # random, generated at creation
CRAFT_STREAM_LOG=true
PRIMARY_SITE_URL=https://${FORTRABBIT_MAIN_DOMAIN}
CRAFT_DB_DRIVER=mysql
CRAFT_DB_SERVER=${FORTRABBIT_DB_HOST}
CRAFT_DB_DSN=mysql:host=${FORTRABBIT_DB_HOST};port=3306;dbname=${FORTRABBIT_DB_NAME}
CRAFT_DB_USER=${FORTRABBIT_DB_USER}
CRAFT_DB_PASSWORD=${FORTRABBIT_DB_PASSWORD}
```

- `${FORTRABBIT_…}` are **platform variables** fortrabbit fills and keeps current: `FORTRABBIT_DB_HOST`, `FORTRABBIT_DB_PORT`, `FORTRABBIT_DB_NAME`, `FORTRABBIT_DB_USER`, `FORTRABBIT_DB_PASSWORD`, `FORTRABBIT_ENVIRONMENT_NAME`, `FORTRABBIT_MAIN_DOMAIN`. Reference them instead of copying values, so a rotated password keeps working.
- An app created without the Craft template, or with deleted vars, needs them added by hand.
- `CRAFT_ENVIRONMENT` holds the environment name, e.g. `production`. Multi-environment config in `config/general.php` keys off it; locally `.env` sets its own, e.g. `CRAFT_ENVIRONMENT=dev`.
- A local table prefix needs `CRAFT_DB_TABLE_PREFIX` on the environment too.
- The editor takes dotenv syntax. A `$` is only allowed inside a `${…}` reference: encode a value containing `$` with the Base64 helper, which adds an `fr+base64:` prefix the platform decodes at runtime.
- Names starting with `FORTRABBIT` are reserved.
- Change ENV vars in the dashboard, with `frbit environments variables update`, or MCP `update_environment`. They reach PHP after `frbit environments restart <env>` or the next deployment.

- `PRIMARY_SITE_URL` is the var Craft's installer writes to `.env` and saves as `$PRIMARY_SITE_URL`, the primary site's base URL in project config. The template points it at the main domain. Apps created before the template set it need the line added by hand. For multi-site, give each site its own var (e.g. `SITE_URL_EN`), use it as that site's base URL, and set it per environment.

## Production settings

| Setting | Template value | Why |
|---|---|---|
| `CRAFT_DEV_MODE` | `false` | Hides error details. For debugging, set `true` on a non-public environment, then back. Dev mode also writes verbose logs on every request |
| `CRAFT_ALLOW_ADMIN_CHANGES` | `false` | Sections, fields and settings live in project config; the next deployment applies git over any change made here. Makes the plugin store read-only |
| `CRAFT_ALLOW_UPDATES` | `false` | An update on the environment changes files git doesn't track; the next deployment undoes it |

Editors still create and edit content with these settings.

Craft CLI on the environment, over SSH with `php craft`:

| Command | On fortrabbit |
|---|---|
| `setup/*` | Never, local only |
| `update/*` | Never, update locally |
| `migrate/all`, `project-config/apply`, `up` | Only when the post-deploy commands don't run them |
| `clear-caches/*` | Runs with every deployment; manually only with a reason |
| `resave/*` | When a migration or plugin asks for it |
| `db/backup`, `db/restore` | Possible; the dump slows the site while it runs |

## Updates and upgrades

Update locally, test, deploy:

```sh
ddev craft update all
git add composer.json composer.lock config/project
git commit -m "Update Craft and plugins"
git push
```

The build runs `composer install`, the post-deploy commands run the migrations and apply the project config. Plugins installed locally reach the environment the same way: `composer.json`, `composer.lock` and `config/project`.

Major upgrade (e.g. Craft 4 → 5):

1. Follow Craft's upgrade guide locally.
2. Set the environment's PHP version in the dashboard to one the new major supports (Craft 5 needs PHP 8.2+).
3. Create a backup of the environment in the dashboard.
4. Add the temporary `CRAFT_DB_CHARSET` and `CRAFT_DB_COLLATION` ENV vars the Craft guide asks for, then deploy.
5. Remove the two vars and run `php craft db/convert-charset` over SSH.

## Common Pitfalls

1. **Deploy file without `strategy: merge`** — the default is `replace`, which deletes every local asset volume not listed in `excludePatterns`. Write `strategy: merge` and `replacePatterns: [/config/project]`, or list each volume path in `excludePatterns`.
2. **Deploy file without `postDeployCommands`** — migrations and project config stop applying silently. Copy all three template commands into the file.
3. **Changing fields or sections in the control panel on fortrabbit** — blocked by `CRAFT_ALLOW_ADMIN_CHANGES=false`, and overwritten by the next deployment if forced. Make the change locally and push `config/project`.
4. **Expecting the local `.env` to work on the server** — Craft reads the environment's ENV vars. Check the `CRAFT_DB_*` values against the template when the database connection fails.
5. **Copying platform values instead of referencing them** — `CRAFT_DB_PASSWORD=abc123` breaks on a password reset. Write `CRAFT_DB_PASSWORD=${FORTRABBIT_DB_PASSWORD}`.
6. **Hand-uploading code with SFTP and forgetting `php craft up`** — no post-deploy commands run without a git deployment. SFTP clients also hide dot files: upload `web/.htaccess`.
7. **Pushing to a branch that isn't connected** — nothing happens. Compare the branch with the environment's git settings in the dashboard.
