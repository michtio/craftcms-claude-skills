# Cloud Code Review Checklist

What to flag when reviewing a diff for a project hosted on Craft Cloud, grouped by severity. Used by the `craft-code-reviewer` and `craft-code-reviewer-deep` agents; apply it by hand in any Cloud review.

Conditional checks. Apply this entire section **only** when the project is detected as a Craft Cloud project — signals:

- `craft-cloud.yaml` at the repo root, OR
- `craftcms/cloud` in `composer.json` `require`, OR
- `Hosted on Craft Cloud` (or equivalent) in the project's `CLAUDE.md`

Skip the section silently for self-hosted projects (Forge, Servd, bare metal) — these patterns are correct or harmless there, and flagging them creates noise.

For full background on every rule below, see `plugin-development.md` and `limitations.md` in this skill.

## Critical

- **Raw CSRF token output in any rendered template**: `{{ craft.app.request.getCsrfToken() }}` or `{{ csrfTokenName }}` baked into a hidden input by hand. Edge static caching will cache the rendered page including the baked-in token, leaking one user's CSRF token to every subsequent visitor. Always use the `csrfInput()` Twig function — it renders an async-fetched input that's compatible with caching.
- **Runtime asset publishing**: `Craft::$app->getAssetManager()->publish(...)` calls, or any code path that writes into `@webroot/cpresources` at request time. Cloud's asset bundle publisher runs at build time only; runtime publishing silently fails. Move the assets into a proper `AssetBundle` with `sourcePath` rooted at the plugin's alias.
- **`tablePrefix` left in config**: `tablePrefix` set in `config/db.php`, `CRAFT_DB_TABLE_PREFIX` in `.env` or Console env vars. Cloud doesn't support table prefixes; deployments succeed but Craft can't find its tables. Run `php craft db/drop-table-prefix` and remove both settings.
- **MariaDB references in `db.php` or Composer constraints**. Cloud supports MySQL 8.0 / Postgres 15 only.
- **Custom `db.php` with hardcoded credentials, not wrapped in an environment check**. Cloud auto-wires its own DB connection; a file-based override fights the platform wiring. Either remove `db.php` or wrap it in `if (!App::env('CRAFT_CLOUD')) { ... }` so it only applies locally.

## Important

- **File writes without an `App::isEphemeral()` guard**: `file_put_contents()`, `mkdir()`, `fopen()` with write modes, custom `Monolog\Handler\StreamHandler` pointed at a file path. Lambda's filesystem is ephemeral — writes outside Craft's Path service vanish when the container recycles. Gate the write on `App::isEphemeral()` and use `Craft::$app->getPath()->getTempPath()`/`getStoragePath()`/`getCachePath()` for transient writes.
- **Asset bundle `sourcePath` not using the plugin's Composer alias**: hardcoded `__DIR__ . '/...'` or absolute paths in `sourcePath`. The Cloud asset publisher needs the alias to resolve correctly at build time. Convert to `@vendor/my-plugin/...`.
- **Asset bundle class that hits the DB in its constructor or `init()`**: any `Craft::$app->getDb()`, element queries, service lookups that touch the DB. The build container runs without DB access; bundles must instantiate cleanly. Move DB-dependent logic out of the bundle (into a service that's invoked at render time).
- **File-based logging**: custom `Monolog\Handler\StreamHandler`, `Monolog\Handler\RotatingFileHandler`, `error_log()` to a path, or any `file_put_contents()` to `storage/logs/`. Cloud's log target captures `Craft::info/warning/error()` calls automatically; file writes are lost. Switch to `Craft::info($message, $category)`.
- **Queue jobs with no batching for large datasets**: a single job that iterates an unbounded element query, runs migrations across many records, or makes many HTTP calls in a loop. Cloud kills jobs at 15 minutes. Refactor to `craft\queue\BaseBatchedJob` with `loadData()` + `processItem()` so each batch fits comfortably under the cap.
- **Custom queue runner scheduled in cron**: a `php craft queue/run` or `queue/listen` scheduled command. Cloud auto-processes the queue; an extra runner produces competing workers and stuck jobs. Remove it.

## Suggestion

- **Cookies set on cacheable site requests**: `setcookie()` or `Craft::$app->getResponse()->getCookies()->add(...)` on routes covered by `cache.rules`. Each `Set-Cookie` busts the edge cache for that user — consider client-side cookies or accepting the cache bypass if the cookie is genuinely required.
- **Session writes on cacheable site requests**: `Craft::$app->getSession()->set(...)`, flash messages, anything that mutates `$_SESSION` on a route the edge layer caches. Forces a cookie and breaks caching.
- **`.htaccess` or `nginx.conf` rules in the repo**: not honored on Cloud. Migrate to `redirects:` and `rewrites:` keys in `craft-cloud.yaml`.
- **`devMode` or `allowAdminChanges` set to `true` in production-equivalent config**: Pixel & Tonic strongly discourages both on Cloud (project-config / DB divergence risk). Gate to dev environments only.
- **Hardcoded `sendmail` adapter in `config/app.php`**: Cloud has no built-in mail service. Configure SMTP/Postmark/SES/Resend explicitly so transactional email actually delivers in production.

## How to apply

Walk the changed files first, then run the Cloud section once you've established the project is Cloud-hosted. Don't paste every rule into the report — call out specifically what was found, severity-tagged, with the file and line. Quote the rule's "why" briefly (Lambda ephemeral filesystem, edge cache token leakage, etc.) so the developer can judge whether the fix is mandatory or contextual.
