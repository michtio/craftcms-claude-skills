# Deploy Pipeline — Build → Migrate → Release

How a Git push (or manual trigger) becomes a live deploy. The three-phase pipeline, what runs in each phase, and the environment variables you can rely on at each stage.

## Documentation

- Deployment: https://craftcms.com/docs/cloud/deployment
- Builds: https://craftcms.com/docs/cloud/builds
- Environments: https://craftcms.com/docs/cloud/environments
- Cloud extension source (cloud/up command): https://github.com/craftcms/cloud-extension-yii2/blob/main/src/cli/controllers/UpController.php

## Common Pitfalls

- Putting `composer install` or `npm run build` in a `.github/workflows/` action — Cloud runs both itself during the Build phase. Your action would be redundant and burn CI minutes.
- Expecting build-time access to the production database. The Build phase runs in an isolated container with no DB connection. Anything that needs the DB (project config apply, migrations, asset publishing) runs in the Migrate phase via `php craft cloud/up`.
- Setting custom env vars in `craft-cloud.yaml`. Custom env vars only exist in the Craft Console UI per environment — they are **not injected into the build container**. If your build needs a secret (e.g. a private NPM token), you'll need to handle it via build args from the Console UI's build-environment-variables section, not `craft-cloud.yaml`.
- Letting build time approach the 15-minute cap. Cloud kills the build at 15 minutes. If you're close, split out the heavy work (image optimization, content sync) into queue jobs that run post-deploy.
- Assuming a failed migration rolls back the deploy. It doesn't — Cloud keeps the previous version serving traffic while the failed deploy stays in a failure state. You fix the migration, push again.
- Pushing from a forked repository. Cloud can't deploy forks — the connected repository must be the upstream.

## The three phases

Every deploy runs through these three phases in order. If a phase fails, the deploy stops and the previously-released version keeps serving traffic.

### 1. Build

Runs in an isolated container with the PHP and Node versions specified in `craft-cloud.yaml`.

Sequence:

1. Repository checkout at the deploying commit.
2. `composer install` (always).
3. If `node-version` is set in `craft-cloud.yaml`:
   - `cd` into `node-path` (if set; defaults to repo root).
   - `npm clean-install`.
   - `npm run <npm-script>` — defaults to `build`.
4. Artifact packaging — everything in `artifact-path` (or the `webroot` if unset) is uploaded for the next phase.

Constraints:

- **15-minute hard cap.** The container is killed at 15 minutes regardless of progress.
- **No database access.** The build container can't reach the production DB.
- **Custom env vars are not injected.** Only the system vars listed below are available.

### 2. Migrate

Runs the Cloud extension's `cloud/up` command against the freshly-built artifact, with full DB access.

`cloud/up` does the following, in order (verified from `craftcms/cloud-extension-yii2/src/cli/controllers/UpController.php`):

1. Triggers the `beforeUp` event (cancelable — plugins can abort the deploy here).
2. Runs `setup/php-session-table` — ensures the PHP session table exists in the DB.
3. Runs `setup/db-cache-table` — ensures the DB cache table exists.
4. If Craft is installed, runs `up` — Craft's standard `craft up` command, which applies pending migrations and pending project-config changes.
5. Purges the static cache gateway via `StaticCache::purgeGateway()` so the next request hits the freshly-deployed code.
6. Triggers the `afterUp` event (cancelable).

If any step exits non-zero, the deploy fails and the prior version keeps serving traffic.

### 3. Release

The new build is promoted to receive traffic. Edge caches are already purged in the Migrate phase, so the first request after release hits the new build cleanly.

## Trigger modes

Deploys are triggered from the Craft Console UI per environment.

- **On Push** — Cloud subscribes to the branch and deploys every push automatically. Default for production environments.
- **Manual** — Cloud waits for a click in the Console. Useful for staging environments where you want to control deploys independently of branch state.

The trigger mode is per-environment, not per-project — your production environment can be On Push while staging is Manual, or vice versa.

## Environment variables

Cloud distinguishes **build-time** and **runtime** environment variables. They're not the same set.

### Build-time system variables

Available in the Build container only. Set automatically by Cloud:

| Variable | Purpose |
|---|---|
| `CRAFT_CLOUD_PROJECT_ID` | The Cloud project ID |
| `CRAFT_CLOUD_ENVIRONMENT_ID` | The environment being built |
| `CRAFT_CLOUD_BUILD_ID` | This specific build |
| `CRAFT_CLOUD_CDN_BASE_URL` | The CDN URL for the build's static assets |
| `CRAFT_CLOUD_ARTIFACT_BASE_URL` | The URL where the build artifact will live |
| `GIT_SHA` | The commit being deployed |
| `NODE_ENV` | Hard-coded to `production` during builds — affects which dependencies `npm install` resolves and how bundlers like Vite/Webpack optimize output |

Use these in build scripts when you need them. Custom env vars from the Console UI are **not** available at build time.

### Runtime variables

Available at runtime (PHP request handling). Set in the Craft Console UI per environment.

- **Standard env vars** — your `MY_API_KEY`, `STRIPE_SECRET`, etc.
- **Write-only env vars** — set once, decrypted into a secrets file at runtime, not exposed in process env or logs. Use for highly sensitive values.
- **Cloud-managed runtime vars** — DB credentials, asset-storage credentials, and similar secrets are auto-injected by the Cloud extension; you should not override them and you generally shouldn't read them directly (use Craft's standard APIs).

Read them with `App::env('MY_VAR')` as you would on any Craft project. The `.env` file is not the source of truth on Cloud — the Console UI is.

### When to use which

- Build-time vars are mostly read-only and auto-set. The only reason to know them is if your build script needs to know the build ID, CDN URL, or commit SHA.
- Runtime vars are where every app-level setting lives. Configure them in the Console UI, not by committing `.env` files.

## Failed deploys

When a phase fails:

1. Cloud stops the pipeline.
2. The previously-released version keeps serving traffic (no automatic rollback because nothing was rolled forward yet).
3. The failed deploy is visible in the Console with the failing phase and any output.

To recover:

- Fix the underlying issue (build syntax error, failing migration, missing env var).
- Push the fix (for On Push environments) or click Deploy (for Manual environments).

There is no one-click rollback to a prior build in the documented surface. The supported recovery path is `git revert <bad-commit> && git push` — which triggers a new build with the prior state. See `migration.md` for the same pattern applied to bigger rollback scenarios.

## What you can't do

- **No build hooks.** No `pre-build` / `post-build` / `post-deploy` keys in `craft-cloud.yaml`.
- **No build-time DB access.** Migration-style work (e.g. generating fixtures, syncing content) has to happen in the Migrate phase via `cloud/up`'s event hooks, or post-deploy via Console commands.
- **No build caching across deploys** — not documented. `vendor/` and `node_modules` are rebuilt every deploy. If your builds are slow because of dependency installs, the lever is `composer install --prefer-dist` (default) and a slim `package.json`, not a cache layer you can configure.
- **No skipping phases.** Every deploy runs all three; you can't push a "config only" deploy that skips the Build phase.

Last verified against https://craftcms.com/docs/cloud/deployment, https://craftcms.com/docs/cloud/builds, and `craftcms/cloud-extension-yii2@main` on 2026-05-28.
