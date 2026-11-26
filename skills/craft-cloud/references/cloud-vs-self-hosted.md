# Cloud vs Self-Hosted: Orientation and Cross-Cutting Pitfalls

Where self-hosted Craft habits mislead you on Craft Cloud. This file holds the full comparison table, the long form of every cross-cutting pitfall that `SKILL.md` lists as a one-liner, and the authoritative documentation sources the skill was written from. Each pitfall names the reference that holds its detail.

## Documentation

Authoritative sources used to write this skill:

- Craft Cloud docs landing: https://craftcms.com/docs/cloud/
- Configuration reference: https://craftcms.com/docs/cloud/config
- Deployment pipeline: https://craftcms.com/docs/cloud/deployment
- Builds: https://craftcms.com/docs/cloud/builds
- Compatibility & limitations: https://craftcms.com/docs/cloud/compatibility
- Assets & transforms: https://craftcms.com/docs/cloud/assets
- Static caching: https://craftcms.com/docs/cloud/static-caching
- Headless apps: https://craftcms.com/docs/cloud/headless-apps
- Request signing: https://craftcms.com/docs/cloud/request-signing
- Plugin development: https://craftcms.com/docs/cloud/plugin-development
- Cloud extension source: https://github.com/craftcms/cloud

Per-claim URLs appear in each reference file. Last verified against the docs and `craftcms/cloud-extension-yii2@main` on 2026-05-28; headless/request-signing, artifact URLs, environments, quotas, and backups content verified against `craftcms/docs@main` on 2026-09-02.

## What's Different on Cloud vs Self-Hosted

A quick orientation table. Each row is a place self-hosted habits will mislead you.

| Concern | Self-hosted | Cloud |
|---|---|---|
| Config file | `.env`, `config/general.php`, `config/db.php`, your web-server config | **`craft-cloud.yaml`** at repo root for platform settings; runtime env vars set in Craft Console UI (not `.env`) |
| Deploy | Whatever you've wired (Forge, GitHub Actions, rsync) | Git push → automatic **Build → Migrate → Release** (15-min build cap) |
| Filesystem | Local disk or your own S3/R2 config | **Ephemeral** Lambda filesystem; use `App::isEphemeral()` to gate writes; user assets must use the Cloud-bundled S3-backed filesystem type |
| Database | Whatever you've installed | **MySQL 8.0 or Postgres 15 only** — no MariaDB, no `tablePrefix`, no `db.php` touching, no `CRAFT_DB_*` overrides |
| App / component config | Free to override components in `config/app.php` | The extension **owns several components** (`response`, `session`, `cache`, `mutex`, `queue`, `assetManager`) + the DB connection — overriding them in `app.*.php` breaks the wiring, and it's **not reproducible locally** (the extension only runs on Cloud) |
| Headless / API consumers | Your GraphQL endpoint, your rate limits | Bot detection deprioritizes automated traffic — SSG builds/ISR get **429/503** unless requests are **signed** (RFC 9421, `$CRAFT_CLOUD_SIGNING_KEY`) and retried with backoff |
| Queue jobs | You run a worker (systemd, supervisor, cron) | **Auto-processed** by Cloud — don't schedule the runner; cap each job at 15 minutes |
| Cron | `crontab -e`, any frequency | Craft Console UI only; **once per hour minimum** |
| Image transforms | ImageOptimize / Imager-X / native | **Edge transforms** via Cloudflare Images — no template changes needed, but ImageOptimize is incompatible |
| Page caching | Blitz or similar | **Edge static caching** via `cache.rules` in `craft-cloud.yaml`; tag-based auto-invalidation |
| Dynamic islands in cached pages | Per-cache-driver workaround | First-class **`cloud.esi(...)`** Twig helper |
| Logs | Files in `storage/logs/` | `Craft::info/warning/error()` only — no file-tailing UI; Console command output is the de-facto surface |
| Mail | sendmail or any adapter | **No built-in mail** — bring your own SMTP/Postmark/SES/Resend |
| SSH | `ssh user@server` | None — Console command runner only (255-char cap, 15-min cap) |
| Server rewrites | `.htaccess` / nginx config | `redirects:` and `rewrites:` keys in `craft-cloud.yaml` |
| Custom domains | DNS provider + cert | DNS + ownership TXT + CNAME to `edge.craft.cloud`; auto SSL via Cloudflare |
| Preview environments | Your CI | Per-branch only — **no per-PR previews documented** |

## Common Pitfalls (Cross-Cutting)

- **Writing to disk without an `App::isEphemeral()` guard.** Lambda's filesystem is ephemeral and writes are lost between requests. Plugins, services, and migrations all need to check and use the Path service (`Craft::$app->getPath()->getTempPath()`/`getStoragePath()`/`getCachePath()`) for transient writes. See `references/extension.md` (App::isEphemeral) and `references/plugin-development.md`.
- **OAuth keys in `storage/`.** [5.12+] MCP and OAuth-authenticated GraphQL need signing keys; `oauth/generate-keys` writes them to the ephemeral `storage/`. Set `CRAFT_OAUTH_PRIVATE_KEY` / `CRAFT_OAUTH_PUBLIC_KEY` as Console env vars instead. See `references/extension.md` and the `craft-mcp` skill.
- **Reconfiguring Cloud-owned app components in `config/app.php` / `app.web.php` / `app.console.php`.** The `craftcms/cloud` extension augments the `response` component (header normalization, gzip, binary→S3 offload, all attached on `EVENT_AFTER_PREPARE`) and replaces `session`, `cache`, `mutex`, `queue`, and `assetManager` — plus auto-wires the database connection. Redefining or augmenting any of these in your app config collides with that wiring and can return **HTTP 500 on every request** (and bypass edge caching). This includes the DB: don't configure `db.php` or set `CRAFT_DB_*` env vars. To add response logic (e.g. a `Content-Language` header), attach at runtime to the response *instance* from a module — `Craft::$app->getResponse()->on(\yii\web\Response::EVENT_AFTER_PREPARE, …)` — never redefine the `response` component. **And never validate these changes locally:** the extension only runs on Cloud (`Helper::isCraftCloud()` is false on DDEV), so a local HTTP 200 proves nothing — treat `app.*.php` as prod-only-verifiable. See `references/database.md` and `references/extension.md`.
- **Using `tablePrefix`.** Unsupported on Cloud. Run `php craft db/drop-table-prefix` before migrating. See `references/migration.md`.
- **Choosing MariaDB.** Cloud only supports MySQL 8.0 and Postgres 15.
- **Scheduling your own queue runner.** Cloud auto-processes queue jobs — adding a scheduled command for the queue runner is redundant and may conflict.
- **Flushing the whole cache from a migration.** `Craft::$app->getCache()->flush()` (or any global wipe) during the Migrate phase contends with the still-live old version on a shared cache — and when Redis/Valkey isn't provisioned, that cache is a single MySQL table, so a flush can deadlock (MySQL 1205) and blow the deploy's CLI cap. Invalidate only what changed. See `references/deploy-pipeline.md` (Never flush the whole cache from a migration) and `references/extension.md` (Cache, queue, and session wiring).
- **Synchronous external HTTP in element save hooks.** Blocks every save, and during a resave or `cloud/up` serializes network latency into the deploy's CLI cap. Queue the call instead. See `references/plugin-development.md`.
- **Trying to schedule cron more often than hourly.** Cloud's UI enforces a one-hour minimum. Design recurring tasks around this floor or move the work into queue jobs triggered by other events.
- **`{{ csrfInput() }}` in cacheable templates.** Forces a cookie, busts edge static caching. Use the `csrfInput()` function instead, which renders an async input compatible with `asyncCsrfInputs` [5.1+] (force-enabled on Cloud).
- **Expecting logged-in users to see `currentUser`-gated UI on a cached route.** Cloud does **not** auto-bypass the edge cache for logged-in requests — once a URL's guest copy is cached, editors are served that copy too (`cf-cache-status: HIT`), so server-rendered edit links / member-only blocks silently disappear. Vary the cache key on the session cookie (`cookies: [CraftSessionId]`), not `session:`, under a nested `cache:` → `rules:` key. See `references/caching-and-edge.md`.
- **`.htaccess` rules or nginx config in the repo.** Won't be honored — move to `redirects:` / `rewrites:` in `craft-cloud.yaml`. See `references/config-file.md`.
- **Writing to log files.** No persistent filesystem. Use `Craft::info/warning/error()` and the logger routes to Cloud's log target automatically. See `references/extension.md`.
- **Assuming SSH access.** There is none. The Console command runner is the only way to execute commands, with a 255-character argument cap and 15-minute timeout.
- **Forked Git repos.** Cloud can't deploy from forks — must be the upstream repository.
- **Expecting per-PR preview environments.** Cloud supports per-branch environments only; no automatic ephemeral environment per pull request.
- **Default `sendmail` adapter.** Will not deliver mail. Configure SMTP/Postmark/SES/Resend explicitly. See `references/limitations.md` (Mail).
- **Using ImageOptimize on Cloud.** Cloud handles transforms at the edge via Cloudflare Images — ImageOptimize duplicates the work and can conflict. See `references/assets-and-transforms.md`.
- **Unsigned automated traffic (SSG builds, ISR revalidation, CI) getting `429`/`503`.** Cloud's bot detection correctly flags headless content retrieval as bot traffic. Sign server-side requests with the environment's `$CRAFT_CLOUD_SIGNING_KEY` (RFC 9421) *and* retry `429`/`503` with `Retry-After`-aware backoff — signatures bypass the bot policy, not capacity limits. Never expose the key client-side. See `references/headless.md`.
- **A robots.txt that blocks everything, or slow first requests, on a non-production environment.** Cloud injects `Disallow: /` into every environment not marked Production, and lets non-prod functions sleep after ~15 min idle. Both are by design — check the Production Environment setting before debugging. See `references/limitations.md` (Environments).
- **Changing a Console env var and expecting it to apply.** Variable changes take effect only on the **next deployment**. See `references/deploy-pipeline.md`.
