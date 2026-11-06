# Deploy & Environments — Git Push, Template, Deploy File

How a git push becomes a deployment on fortrabbit, what the Craft CMS software template configures, how the deploy file replaces the dashboard settings, and how ENV vars and production settings work per environment.

## Documentation

- Craft CMS guides: https://docs.fortrabbit.com/guides/craft-cms
- Deployment: https://docs.fortrabbit.com/platform/deployment
- Deploy file: https://docs.fortrabbit.com/platform/deployment/deploy-file
- ENV vars: https://docs.fortrabbit.com/platform/settings/env-vars

## Contents

- [Current values](#current-values) — where to read the live template and settings
- [Apps and environments](#apps-and-environments) — the object model and hostnames
- [How deployments work](#how-deployments-work) — trigger, build, post-deploy
- [The Craft software template](#the-craft-software-template) — what it sets up
- [Merge strategy and replace patterns](#merge-strategy-and-replace-patterns) — why uploads survive
- [The deploy file](#the-deploy-file) — deployment settings as code
- [ENV vars](#env-vars) — template vars, platform variables, site URL
- [Production settings](#production-settings) — dev mode, admin changes, updates
- [Updates and upgrades](#updates-and-upgrades) — local first, then deploy
- [Common Pitfalls](#common-pitfalls)

## Current values

Template values and the deploy file format change over time. The examples in this file show their shape; read the current values before writing a deploy file or changing settings (fetch the docs pages with `WebFetch`):

- **This environment's settings**: `frbit environments get <env> --json` or MCP `get_environment`: ENV vars, build and post-deploy commands, root path. When the branch has a deploy file, these show the dashboard values, which are not used; read the file instead.
- **The Craft template**: `https://docs.fortrabbit.com/raw/guides/craft-cms/setup.md`. The page renders the template from fortrabbit's platform definitions, so it is always current.
- **The deploy file schema**: `https://docs.fortrabbit.com/raw/platform/deployment/deploy-file.md`.

Any docs page is available as Markdown: insert `/raw` after the host and append `.md`. `https://docs.fortrabbit.com/llms.txt` lists every page.

## Apps and environments

- An **app** groups one or more **environments**, e.g. `production` and `staging`. Each environment has an ID `en-xxxxxx`, its own components (PHP, MySQL, storage, jobs), ENV vars, SSH access and git branch.
- Default domain: `https://<env>.<region>.frbit.app`. It forwards to the main domain, a cloud domain `https://<label>.frbit.cloud` or a custom domain.
- SSH: `<env>@ssh.<region>.frbit.app`. The MySQL database name and user are the environment ID.

Staging and production are separate environments with separate databases and storage. Content flows down (production → local) by syncing; schema and code flow up through git.

## How deployments work

1. The repository is connected through the **fortrabbit GitHub App**. fortrabbit detects Craft from the repository when the app is created.
2. A `git push` to the environment's branch starts a deployment. The dashboard deploy button, `frbit environments deploy <env>` and a **deploy hook** URL (a secret for CI) deploy the latest commit of the branch again.
3. **Build commands** run first. Composer runs here: don't commit `vendor/` and don't run Composer in a CI action as well.
4. The build result goes into the environment's storage according to the **deployment strategy**.
5. **Post-deploy commands** run once the new code is live. A failing post-deploy command does not roll back: the new code is already serving. Fix and push again, or run the command over SSH.

Read the log of a failed deployment with `frbit deployments logs <deployment>` or MCP `get_deployment_logs`.

Only pushed commits deploy. An older commit is deployed by reverting in git and pushing. Code uploaded with rsync or SFTP runs no build or post-deploy commands: run `php craft up` over SSH afterwards.

## The Craft software template

Choosing Craft CMS, or having it detected, applies the Craft template. It sets up:

- **Root path** `web`.
- **Build**: `composer install` without dev packages. Add `npm ci` and `npm run build` when the repo has a `package.json` and a lock file; Node.js runs during the build only, not at runtime.
- **Post-deploy**: Craft's migrations, project config apply and cache clear (`php craft migrate/all`, `php craft project-config/apply`, `php craft clear-caches/all` at the time of writing). They do nothing when no changes are pending, so they are safe on every deployment.
- **Strategy** `merge` with a replace pattern for `/config/project` (next section).
- **ENV vars** for the database, environment name and production settings (see [ENV vars](#env-vars)).

Craft 6 is built on Laravel and gets a separate template with a different root path and commands; this skill covers Craft 5.

## Merge strategy and replace patterns

The **merge** strategy copies the build over the storage and deletes nothing:

- Files in the build overwrite their copies.
- Files on the environment that are not in the build stay: uploads in local volumes, transforms, runtime files.
- Files deleted in git stay too. The **replace pattern** `/config/project` deletes that folder before the copy, so a project config file removed from git is removed on the environment, and `project-config/apply` doesn't re-apply it.

The **replace** strategy makes the storage an exact copy of the build. With it, every local asset volume needs an **exclude pattern**, e.g. `/web/uploads`, or it is deleted on the next deployment.

## The deploy file

A deploy file holds the deployment settings in the repository: `.fortrabbit/deploy.yml`, `.yaml` or `.json`, first one found wins. fortrabbit marks it as a new feature; check the schema page before writing one.

The Craft template as a deploy file, at the time of writing:

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
- A key left out falls back to its default, **not** to the dashboard value. The default strategy is `replace`, and the default command lists are empty.
- An invalid file fails the deployment before the build; the code on the environment stays as it was. The deployment log names the problem.
- A change to the file deploys with the next push. Redeploying the same commit doesn't pick it up.
- Deleting the file and pushing brings the dashboard settings back.
- Branch, deploy hook and PHP version stay in the dashboard.

## ENV vars

The environment's ENV vars replace `.env` on the server; the local `.env` stays out of git. The template sets:

- The database connection as `CRAFT_DB_*` vars that reference **platform variables**, e.g. `CRAFT_DB_PASSWORD=${FORTRABBIT_DB_PASSWORD}`.
- `CRAFT_ENVIRONMENT=${FORTRABBIT_ENVIRONMENT_NAME}`, e.g. `production`. Multi-environment config in `config/general.php` keys off it.
- A random `CRAFT_SECURITY_KEY`.
- `PRIMARY_SITE_URL=https://${FORTRABBIT_MAIN_DOMAIN}`, the site URL (below).
- The production settings below, and `CRAFT_STREAM_LOG=true` so logs go to the dashboard.

Platform variables are filled and kept current by fortrabbit. They all start with `FORTRABBIT_`, a reserved prefix: `FORTRABBIT_DB_*` for the database, `FORTRABBIT_ENVIRONMENT_NAME`, `FORTRABBIT_MAIN_DOMAIN`. Reference them with `${…}` instead of copying their values, so a rotated password keeps working.

**Site URL.** Craft's installer saves the site URL to `.env` as `PRIMARY_SITE_URL` and uses `$PRIMARY_SITE_URL` as the primary site's base URL in project config. The template sets it from the main domain, so it follows a domain change. Environments created before the template had it may lack it; add the same line there:

```sh
PRIMARY_SITE_URL=https://${FORTRABBIT_MAIN_DOMAIN}
```

For multi-site, give each site its own var (e.g. `SITE_URL_EN`), use it as that site's base URL, and set it per environment.

Other rules:

- A local table prefix needs `CRAFT_DB_TABLE_PREFIX` on the environment too.
- Change ENV vars in the dashboard, with the CLI or MCP `update_environment`. They reach PHP after a restart (`frbit environments restart <env>`) or the next deployment.
- A `$` is only allowed inside a `${…}` reference. Encode other values containing `$` with the dashboard's Base64 helper.

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

The build runs Composer, the post-deploy commands run the migrations and apply the project config. Plugins installed locally reach the environment the same way.

Major upgrade:

1. Follow Craft's upgrade guide locally.
2. Set the environment's PHP version in the dashboard to one the new major supports, as listed in Craft's requirements.
3. Create a backup of the environment in the dashboard.
4. Add any temporary ENV vars the Craft guide asks for (e.g. `CRAFT_DB_CHARSET`, `CRAFT_DB_COLLATION` for Craft 5), then deploy.
5. Remove them again and run the follow-up commands from the guide over SSH.

## Common Pitfalls

1. **Deploy file without `strategy: merge`** — the default is `replace`, which deletes every local asset volume not listed in `excludePatterns`. Write `strategy: merge` and the `/config/project` replace pattern, or list each volume path in `excludePatterns`.
2. **Deploy file without `postDeployCommands`** — migrations and project config stop applying silently. Copy the template's post-deploy commands into the file.
3. **Changing fields or sections in the control panel on fortrabbit** — blocked by `CRAFT_ALLOW_ADMIN_CHANGES=false`, and overwritten by the next deployment if forced. Make the change locally and push `config/project`.
4. **Expecting the local `.env` to work on the server** — Craft reads the environment's ENV vars. Compare the `CRAFT_DB_*` values with the template when the database connection fails.
5. **Copying platform values instead of referencing them** — `CRAFT_DB_PASSWORD=abc123` breaks on a password reset. Write `CRAFT_DB_PASSWORD=${FORTRABBIT_DB_PASSWORD}`.
6. **Site URL missing on an older environment** — the base URL resolves to nothing and links break. Add `PRIMARY_SITE_URL` as above.
7. **Hand-uploading code with SFTP and forgetting `php craft up`** — no post-deploy commands run without a git deployment. SFTP clients also hide dot files: upload `web/.htaccess`.
8. **Pushing to a branch that isn't connected** — nothing happens. Compare the branch with the environment's git settings.
