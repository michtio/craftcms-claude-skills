---
name: craft-cloud
description: "Craft Cloud, Pixel & Tonic's serverless hosting platform for Craft CMS. Covers craft-cloud.yaml, the Build → Migrate → Release deploy pipeline, the craftcms/cloud extension, edge image transforms via Cloudflare, edge static caching (cache.rules, ESI), the Cloud S3 filesystem, MySQL 8 / Postgres 15 (no MariaDB, no tablePrefix), the Console command runner and scheduled cron (hourly minimum), queue jobs, custom domains and SSL, preview environments per branch, limits (ephemeral filesystem, no SSH, no .htaccess, no built-in mail), Cloud-compatible plugins, and self-hosted → Cloud migration."
when_to_use: "Triggers on: craft-cloud.yaml, craftcms/cloud package, cloud.esi(), php craft cloud/up, App::isEphemeral(), CRAFT_EPHEMERAL, edge.craft.cloud, preview.craft.cloud, CRAFT_CLOUD_PROJECT_ID, CRAFT_CLOUD_SIGNING_KEY request signing (RFC 9421), AssetsFs, ESI islands, deploy or migrate to Craft Cloud, Craft Cloud quotas and regions, headless 429/503, cloud.artifactUrl(), @artifactBaseUrl. Do NOT trigger for Servd (servd), fortrabbit (craft-fortrabbit) or generic Craft deployment on Forge/bare metal (craftcms/deployment.md). Do NOT trigger for general DDEV local dev unrelated to Cloud parity."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft Cloud — Serverless Hosting for Craft CMS

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Reference for Craft Cloud, Pixel & Tonic's serverless hosting platform for Craft CMS. Covers the `craft-cloud.yaml` config file, the Build → Migrate → Release deploy pipeline, the `craftcms/cloud` extension, edge image transforms and static caching, the Cloud filesystem, plugin Cloud-compatibility requirements, and self-hosted → Cloud migration.

This skill is scoped to **Craft Cloud specifically** — what's different on Cloud vs running Craft yourself on Forge, Servd, fortrabbit, or bare metal. For **Servd**, see the `servd` skill; for **fortrabbit**, the `craft-fortrabbit` skill. For generic Craft deployment (build artifacts, project config sync, atomic deploys on traditional hosts), see the `craftcms` skill's `deployment.md`.

## Companion Skills — Load When Needed

- **`craftcms`** — When the Cloud topic intersects plugin or module PHP work (e.g. `App::isEphemeral()` guards in services, asset-bundle constraints, queue job design for the 15-minute cap).
- **`craft-site`** — When Cloud intersects front-end templating (ESI islands inside cached pages, edge image transform usage, `{% expires %}` opt-outs for static caching).
- **`ddev`** — For the local-dev parity recipe (matching PHP/DB versions, simulating the ephemeral filesystem locally).
- **`craft-php-guidelines`** — When editing plugin PHP to add Cloud-compatibility checks.
- **`craft-mcp`**: for Craft's MCP server, OAuth server and personal access tokens [5.12+] (signing keys as env vars on this host).

Docs: https://craftcms.com/docs/cloud/ (full source list and verification dates in `references/cloud-vs-self-hosted.md`).

## Cloud vs Self-Hosted at a Glance

Platform settings live in **`craft-cloud.yaml`** at the repo root; runtime env vars are set in the Craft Console UI, not `.env`. Git push triggers **Build → Migrate → Release** (15-min build cap). The filesystem is **ephemeral**, the database is **MySQL 8.0 or Postgres 15 only**, queue jobs are **auto-processed**, cron is **hourly at most**, image transforms and static caching happen **at the edge**, there is **no SSH, no `.htaccess`, no built-in mail**, and previews are **per-branch only**. The full comparison table is in `references/cloud-vs-self-hosted.md`.

## Common Pitfalls (Cross-Cutting)

One-liners; the long form of each is in `references/cloud-vs-self-hosted.md`.

- **Disk writes without an `App::isEphemeral()` guard** are lost between requests; use the Path service (`getTempPath()`/`getStoragePath()`/`getCachePath()`). See `extension.md`, `plugin-development.md`.
- **OAuth keys in `storage/`.** [5.12+] `oauth/generate-keys` writes to the ephemeral `storage/`; set `CRAFT_OAUTH_PRIVATE_KEY` / `CRAFT_OAUTH_PUBLIC_KEY` as Console env vars. See `extension.md`.
- **Redefining Cloud-owned components** (`response`, `session`, `cache`, `mutex`, `queue`, `assetManager`, the DB connection) in `config/app*.php` can return HTTP 500 on every request. Attach to the response *instance* (`EVENT_AFTER_PREPARE`) from a module instead. No `db.php`, no `CRAFT_DB_*`. A local HTTP 200 proves nothing: the extension only runs on Cloud. See `extension.md`, `database.md`.
- **`tablePrefix`** is unsupported: run `php craft db/drop-table-prefix` before migrating (`migration.md`). **MariaDB** is not offered.
- **Don't schedule a queue runner**: Cloud auto-processes jobs (15-min cap each).
- **Never flush the whole cache from a migration**: it contends with the live release and can deadlock the MySQL-table cache (1205). See `deploy-pipeline.md`.
- **Synchronous external HTTP in element save hooks** serializes latency into the deploy's CLI cap; queue it. See `plugin-development.md`.
- **Cron more often than hourly** is impossible; use queue jobs triggered by events.
- **`{{ csrfInput() }}` on cacheable pages** forces a cookie; it renders async with `asyncCsrfInputs` [5.1+] (force-enabled on Cloud). See `caching-and-edge.md`.
- **Logged-in users get the cached guest copy**: Cloud does not bypass the edge cache for them. Vary on `cookies: [CraftSessionId]` under nested `cache:` → `rules:`. See `caching-and-edge.md`.
- **`.htaccess` / nginx config** is ignored: use `redirects:` / `rewrites:` in `craft-cloud.yaml` (`config-file.md`).
- **Log files**: no persistent disk; use `Craft::info/warning/error()` (`extension.md`).
- **No SSH**: Console command runner only (255-char cap, 15-min cap). **Forked repos** can't deploy. **No per-PR previews.**
- **`sendmail`** won't deliver: configure SMTP/Postmark/SES/Resend (`limitations.md`, Mail).
- **ImageOptimize** conflicts with edge transforms (`assets-and-transforms.md`).
- **Unsigned SSG/ISR/CI traffic gets `429`/`503`**: sign with `$CRAFT_CLOUD_SIGNING_KEY` (RFC 9421) and retry with `Retry-After` backoff; never expose the key client-side. See `headless.md`.
- **Non-prod environments** inject `robots.txt` `Disallow: /` and sleep after ~15 min idle, by design (`limitations.md`, Environments).
- **Console env var changes** apply only on the **next deployment** (`deploy-pipeline.md`).

## Reference Files

Read the relevant reference file(s) for your task. Multiple files often apply.

**Task examples:**

- "Set up a new Craft project on Cloud" → `config-file.md` + `deploy-pipeline.md` + `extension.md`
- "Configure `craft-cloud.yaml` for PHP and Node versions" → `config-file.md`
- "Add redirects in `craft-cloud.yaml`" → `config-file.md` (Redirects and Rewrites)
- "What happens during deploy?" → `deploy-pipeline.md`
- "Set build-time env vars" → `deploy-pipeline.md` (Build-time vs runtime variables)
- "Which env vars are reserved / shouldn't I set on Cloud?" → `deploy-pipeline.md` (Reserved runtime variables)
- "What does `php craft cloud/up` do?" → `extension.md` (cloud/up internals)
- "Add an ESI island inside a cached page" → `caching-and-edge.md`
- "Edge static caching rules" → `caching-and-edge.md`
- "Migrate user assets from self-hosted to Cloud" → `assets-and-transforms.md` + `migration.md`
- "Make this plugin Cloud-compatible" → `plugin-development.md`
- "Why does my plugin's file write silently fail on Cloud?" → `plugin-development.md` (Ephemeral filesystem) + `extension.md` (App::isEphemeral)
- "Set up a custom domain" → `domains.md`
- "Schedule a recurring command" → `commands-and-cron.md` (hourly minimum)
- "Run a one-off command on Cloud" → `commands-and-cron.md` (Console command runner)
- "Configure SMTP on Cloud" → `limitations.md` (Mail) + `craftcms/email.md`
- "Set up local DDEV to match Cloud" → `local-dev.md`
- "Move a self-hosted Craft site to Cloud" → `migration.md`
- "What plugins work on Cloud?" → `limitations.md` (Plugin compatibility — community knowledge)
- "My Next.js/Nuxt/Astro build gets 429s from Cloud" → `headless.md`
- "Sign programmatic requests to Cloud" → `headless.md` (Request signing)
- "Link built JS/CSS from templates" → `deploy-pipeline.md` (Artifact URLs)
- "Private Composer packages on Cloud" → `deploy-pipeline.md` (Private Composer packages)
- "robots.txt is blocking my site" → `limitations.md` (Environments)
- "How does Cloud differ from self-hosting / full pitfall detail" → `cloud-vs-self-hosted.md`

Load only the reference files your task needs.

| Reference | Scope | ~Lines |
|---|---|---:|
| `references/cloud-vs-self-hosted.md` | Full Cloud vs self-hosted comparison table, long form of every cross-cutting pitfall, documentation sources and verification dates | 69 |
| `references/config-file.md` | `craft-cloud.yaml` keys: `php-version`, `node-version`, `npm-script`, `artifact-path`, `app-path`, `webroot`, `cache:` → `rules:`, `redirects`, `rewrites` | 156 |
| `references/deploy-pipeline.md` | Build → Migrate → Release, triggers, 15-min build cap, build-time vs runtime vars, **reserved vars you must NOT set**, artifact URLs (`cloud.artifactUrl()`, `@artifactBaseUrl`), private Composer packages, failed-migration rollback | 210 |
| `references/headless.md` | Bot detection `429`/`503`, RFC 9421 signing with `$CRAFT_CLOUD_SIGNING_KEY`, `Retry-After` backoff, Next.js/Nuxt/Astro, `getRequestSigner()` | 107 |
| `references/extension.md` | `craftcms/cloud` package: bootstrap, `App::isEphemeral()`, Path service, `cloud.esi()`, `cloud/up` internals, asset-bundle CDN publisher, binary response upload, log target, OAuth keys | 256 |
| `references/assets-and-transforms.md` | Cloud filesystem (`assets/` subpath), `aws s3 sync`, edge transform limits (70MB / 100MP / 12,000px, AVIF 1,600px) | 87 |
| `references/database.md` | MySQL 8.0 / Postgres 15, `tablePrefix` ban, auto-wired connection, backups (30-day retention, 200GB cap), restore | 111 |
| `references/caching-and-edge.md` | Static caching rules (`pattern`, `query-string`, `cookies`, first-match wins), ignored tracking params, logged-in users, opt-outs (`{% expires %}`, `setNoCacheHeaders()`), Commerce cart, `asyncCsrfInputs` [5.1+], `cloud.esi(...)`, tag invalidation | 347 |
| `references/domains.md` | DNS (`_cf-custom-hostname` TXT, CNAME to `edge.craft.cloud`, apex), preview URLs, auto SSL, `www` not auto-added | 104 |
| `references/commands-and-cron.md` | Console command runner (255-char, 15-min caps), scheduled commands (hourly, max 5 per env), auto-processed queue, batched jobs | 141 |
| `references/plugin-development.md` | Cloud-compatible plugin checklist: asset bundles, `App::isEphemeral()`, logging, queue budgeting, cookie-free design, `csrfInput()`, `sendContentAsFile()`, Craft 4.6+ minimum | 302 |
| `references/migration.md` | Self-hosted → Cloud cutover: audit, `db/drop-table-prefix`, `aws s3 sync`, DNS cutover, project config | 132 |
| `references/local-dev.md` | DDEV parity: PHP/DB versions, extension no-op locally, `CRAFT_EPHEMERAL`, S3 emulation | 145 |
| `references/limitations.md` | Unsupported features and hard caps (6MB response, 16KB header, 60s request, 200MB upload), environments facts, plugin compatibility matrix (community knowledge), mail, logging | 239 |
| `references/review-checklist.md` | Code review checklist for Cloud projects, by severity: CSRF tokens in cached pages, runtime asset publishing, `tablePrefix`, ephemeral file writes, file logging, queue batching | ~42 |
