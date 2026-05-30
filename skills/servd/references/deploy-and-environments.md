# Deploy & Environments — Push, Build, Promote

How a Git push becomes a live deploy on Servd, the fixed local → staging → production environment model, the Node build step (`servd.yaml` vs dashboard), and how env vars/secrets work per environment.

## Documentation

- The Servd Workflow: https://servd.host/docs/the-servd-workflow
- Node Build Step: https://servd.host/docs/node-build-step
- Environment Variables: https://servd.host/docs/environment-variables
- Starting a Project From Scratch: https://servd.host/docs/starting-a-project-from-scratch
- Asset storage plugin source (console commands, reserved vars): https://github.com/servdhost/craft-asset-storage

## Common Pitfalls

- Trying to make schema/admin changes directly in staging or production. Servd forces `allowAdminChanges: false` everywhere except local. Field, section, and settings changes that touch Project Config **must** originate in your primary dev environment (local) and flow up. The CP will refuse the change otherwise.
- Committing a `.env` file and expecting it to drive production. Servd uses **real, dashboard-managed env vars per environment** — committed `.env` files are not the source of truth and don't fit a load-balanced, multi-instance setup. See "Env vars & secrets" below.
- Confusing build-time env vars with runtime env vars. The Node build step has its own separate set of environment variables configured on the build step — they are not the same as the runtime vars your PHP reads. A secret your bundler needs at build time goes on the build step, not in the runtime vars.
- Adding `npm install` to your build COMMAND. Servd runs `npm install` for you and caches `node_modules`. Putting it in the command is redundant and slows the build.
- Putting `composer install` or asset builds in a CI action. Servd does Composer install and the optional Node build itself on every deploy. A GitHub Action duplicating that is wasted work.
- Assuming `servd.yaml` and the dashboard merge. They don't — if `servd.yaml` exists at the repo root it **overrides** the dashboard build config entirely. There is no `servd.json` or `.servd`; `servd.yaml` is the only Servd repo config file.
- Editing content in production and expecting it upstream. Data flows down (production → staging → local) via cloning; only schema/config flows up via deploys. "local is always the most up-to-date" for config, never for live content.

## How deploys work

Servd is a Craft-specialised **managed** host: your app runs on load-balanced instances behind a gateway (not strictly serverless), on an ephemeral filesystem (see `limitations.md`). Deployment is **git push-to-deploy**.

- Connect a repo via OAuth (GitHub, GitLab, Bitbucket) or any git host over SSH with a deploy key. Servd pulls your code in via git rather than FTP/rsync.
- Craft is **auto-detected** from `composer.json` plus the `config/` folder; Servd recommends the detected path during setup.
- On deploy Servd runs **Composer install**, plus an **optional Node build step** (see below), then packages the result into a deployable **bundle** identified by its commit.

## The Node build step

Configured either in the dashboard (**Build & Deploy** page → **Node Build Step**) or in **`servd.yaml`** at the repo root. `servd.yaml` overrides the dashboard.

| Field | Meaning |
|---|---|
| **COMMAND** | Build command to run, e.g. `npm run build-production`, `npx webpack build`, or `./build-production.sh` |
| **NODE VERSION** | Supported: 10, 12, 14, 15, 16, 17, 18, 20 |
| **BUILD CONTEXT PATH** | Directory the buildchain runs in. Defaults to the repo root; needs a `package.json` at that path |
| **BUILD ORDER** | Run Node **before** Composer (default) or **after** it — use "after" when the Node step depends on Composer-installed packages |
| **ENVIRONMENT VARIABLES** | Build-time vars, a **separate set** from runtime env vars. Set here anything your build command needs |

Behaviour:

- Servd runs `npm install` automatically — do not include it in COMMAND.
- `node_modules` is cached and invalidated when `package.json`, `package-lock.json`, `.npm*`, or the `node_packages` folder changes.
- Custom local packages go in a **`node_packages`** folder inside the Build Context Path (e.g. `/node_packages` or `/buildchain/node_packages`), then referenced from `package.json`.

Example `servd.yaml`:

```yaml
node:
  command: npm run build-production
  version: 20
  context: /
  order: before
```

(Confirm exact `servd.yaml` key names against the Node Build Step docs for your project — **Verify**. The fields above are accurate; the YAML key spelling is the load-bearing detail to check.)

See `local-dev.md` for running the same buildchain locally.

## Environments: local → staging → production

The three environments are **fixed** and the flow between them is **strictly uni-directional**. From the docs: *"all your changes need to be made in your primary development environment (probably local) and then synced up through staging and production."*

Servd enforces this with Craft Project Config: **`allowAdminChanges: false`** on every environment except local. Staging and production cannot accept admin/schema changes directly — they only receive Project Config applied during a deploy.

Typical workflow:

1. Build a **bundle** from a git commit (via the dashboard, "Build Bundle").
2. **Clone production down to staging** — copies production data, assets, and bundles to staging ("Clone From Environment").
3. **Deploy the bundle to staging** and test. Project Config applies automatically during the deploy.
4. **Deploy to production** — select the same bundle, or clone staging → production if content changed during testing.

Because all config originates locally, *"local is always the most up-to-date."*

## Cloning & syncing between environments

Data and assets move **downward** (production/staging → local) using the `servd-asset-storage` console commands provided by the Servd plugin:

- `servd-asset-storage/clone` — clone between environments; takes `from`, `to`, `database`, `assets`, and `bundle` options.
- `servd-asset-storage/local/pull-database` — pull a remote environment's database to local.
- `servd-asset-storage/local/pull-assets` — pull remote assets to local.
- `push-database` / `push-assets` under the same `local` controller for the reverse (gated by a "Disable Push Console Commands" plugin setting).

Cover the day-to-day usage of these in `local-dev.md`; database/queue specifics live in `database-and-queue.md`. Asset volume configuration is in `asset-storage.md`; the static cache layer is in `caching.md`.

## Env vars & secrets

Servd uses **real environment variables, managed per environment in the dashboard** — not a committed `.env` (the docs cite the difficulty of keeping `.env` files on disk in a high-availability environment). Production and staging each have their own set; changing them requires a "Sync" deploy step to take effect.

Reserved Servd variables (confirmed in the plugin source):

- `SERVD_PROJECT_SLUG` — the project's primary identifier (also shown on the dashboard Assets page).
- `SERVD_SECURITY_KEY` — the key used to authenticate against your project (e.g. for clone/pull commands).
- `SERVD_BUNDLE_HASH` — identifies the deployed bundle. **Verify** (not located in the asset-storage plugin source; confirm against current Servd docs/runtime).

Read all of these the normal Craft way with `App::env('SERVD_PROJECT_SLUG')`; the Servd plugin itself reads them via `getenv()`/`App::env()` internally. Build-time env vars are configured separately on the Node build step (above) and are not available at runtime.

Last verified against https://servd.host/docs/the-servd-workflow, https://servd.host/docs/node-build-step, https://servd.host/docs/environment-variables, https://servd.host/docs/starting-a-project-from-scratch, and `servdhost/craft-asset-storage@main` on 2026-05-30.
