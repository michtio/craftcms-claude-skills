# GeneralConfig Reference — Content, Templates & Operations

Settings for content editing, templates, performance, garbage collection, localization, headless/GraphQL, accessibility, preview, development, and dangerous interactions. For system, routing, security, users, sessions, search, assets, and image settings, see `config-general.md`.

## Documentation

- General config reference: https://craftcms.com/docs/5.x/reference/config/general.html
- GeneralConfig API: https://docs.craftcms.com/api/v5/craft-config-generalconfig.html

## Contents

1. [Content & Editing](#1-content--editing)
2. [Templates](#2-templates)
3. [Performance & Maintenance](#3-performance--maintenance)
4. [Garbage Collection](#4-garbage-collection)
5. [Localization](#5-localization)
6. [Aliases & Resources](#6-aliases--resources)
7. [File Permissions & Cookies](#7-file-permissions--cookies)
8. [Headless & GraphQL](#8-headless--graphql)
9. [Accessibility](#9-accessibility)
10. [Preview](#10-preview)
11. [Development](#11-development)
12. [Dangerous Interactions](#dangerous-interactions)

---

## 1. Content & Editing

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `autosaveDrafts` | `bool` | `true` | Auto-save drafts as authors edit. Disabling reduces DB writes but risks lost work. |
| `maxRevisions` | `?int` | `50` | Max entry revisions. `null` = unlimited. `0` = no revisions. |
| `maxSlugIncrement` | `int` | `100` | Max suffix number for slug collisions before using random string. |
| `slugWordSeparator` | `string` | `'-'` | Word separator in auto-generated slugs. |
| `allowUppercaseInSlug` | `bool` | `false` | Preserve uppercase in slugs. Default lowercases everything. |
| `allowSimilarTags` | `bool` | `false` | Allow similarly-named tags (e.g., "Design" and "design"). |
| `defaultWeekStartDay` | `int` | `1` (Monday) | 0=Sunday through 6=Saturday. Affects date picker UI. |
| `defaultCountryCode` | `string` | `'US'` | Default country for address fields. (Since 4.5.0) |
| `defaultTokenDuration` | `mixed` | `86400` (1 day) | Default token lifetime (preview, verification, etc). |
| `previewTokenDuration` | `mixed` | `null` | Preview token lifetime. Defaults to `defaultTokenDuration`. (Since 3.7.0) |

Changing `slugWordSeparator` or `limitAutoSlugsToAscii` mid-project does NOT update existing slugs. URLs break unless you set up redirects. Only change these before content exists or prepare a migration to update all existing slugs.

`maxRevisions` at `0` means Craft saves no revisions -- there is no undo for published changes. At `null`, revisions accumulate indefinitely, which can bloat the database significantly on active sites. The default `50` is a reasonable balance.

`autosaveDrafts` at `true` creates a draft and auto-saves it every 2 seconds while editing. This generates substantial DB write traffic. On sites with many concurrent editors, consider monitoring database load. Disabling it means unsaved changes are lost if the browser crashes or the tab is closed. Note that `autosaveDrafts` only affects the auto-save interval -- manual draft saving always works regardless.

`maxSlugIncrement` controls how Craft handles slug collisions. If "my-post" already exists, Craft tries "my-post-2", "my-post-3", etc., up to this number. After that, it appends a random string. The default `100` is generous -- collisions above `10` usually indicate a naming problem.

`defaultCountryCode` sets the initial value for Address fields. It does not validate or restrict which countries are available. Use field-level configuration to restrict country lists.

`defaultWeekStartDay` affects only the date picker UI in the CP. It does not change how Twig's `date` filter handles week calculations (those follow PHP's `intl` settings).

`previewTokenDuration` at `null` inherits from `defaultTokenDuration` (1 day). For headless setups where editors preview content on an external front-end, consider setting this shorter (e.g., 2 hours) to limit the window during which preview URLs are valid. See `headless.md` for the full preview token flow.

---

## 2. Templates

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultTemplateExtensions` | `string[]` | `['twig', 'html']` | File extensions Craft looks for when resolving template paths. |
| `enableTemplateCaching` | `bool` | `true` | Enable `{% cache %}` tags. Disable in dev for convenience. |
| `privateTemplateTrigger` | `string` | `'_'` | Prefix identifying templates not directly accessible via URL. Empty string to disable. |
| `cpHeadTags` | `array` | `[]` | Inject HTML tags in CP `<head>`. Format: `[tagName, attributes]`. (Since 3.5.0) |

`enableTemplateCaching` at `false` makes all `{% cache %}` tags no-ops. The templates still render correctly, but no caching occurs. This is useful during development to avoid stale content. In production, leave it `true`. Note this only affects `{% cache %}` tags -- data caching (`craft.app.cache`) is controlled separately by `cacheDuration`.

`privateTemplateTrigger` at `'_'` means any template whose filename or directory name starts with `_` cannot be accessed directly via URL. The `_layouts/`, `_includes/`, `_partials/` convention works because of this. Set to empty string `''` to disable this protection (not recommended). Templates prefixed with `_` can still be included/extended from other templates -- they just can't be requested directly as a route target.

`cpHeadTags` injects tags into the CP's `<head>`. Common use: custom favicon or font loading:

```php
->cpHeadTags([
    ['link', ['rel' => 'icon', 'href' => '/favicon.ico']],
    ['link', ['rel' => 'stylesheet', 'href' => 'https://fonts.googleapis.com/css2?family=Inter']],
])
```

`defaultTemplateExtensions` controls which extensions Craft tries when resolving a template path. If you request `blog/index`, Craft looks for `blog/index.twig`, then `blog/index.html`. The order matters -- `.twig` is checked first by default. Adding more extensions (e.g., `['twig', 'html', 'xml']`) enables XML template rendering for feeds without explicit extensions in routes.

---

## 3. Performance & Maintenance

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `cacheDuration` | `mixed` | `86400` (1 day) | Default data cache duration. |
| `runQueueAutomatically` | `bool` | `true` | Trigger queue via web requests. Set `false` in production, use daemon. |
| `maxBackups` | `int\|false` | `20` | Max DB backups before oldest deleted. `false` = keep all. |
| `backupOnUpdate` | `bool` | `true` | Auto-backup DB before updates. |
| `backupCommand` | `string\|null\|false\|Closure` | `null` | Custom DB backup command. Supports `{file}`, `{port}`, `{server}`, `{user}`, `{password}`, `{database}`, `{schema}` placeholders. `false` to disable backups. |
| `backupCommandFormat` | `?string` | `null` | PostgreSQL backup format: `custom`, `directory`, `tar`, `plain`. No effect on MySQL. (Since 5.1.0) |
| `restoreCommand` | `string\|null\|false\|Closure` | `null` | Custom DB restore command. Same placeholders as `backupCommand`. `false` to disable restores. |
| `useFileLocks` | `?bool` | `null` | Use `LOCK_EX` when writing files. Set `false` on NFS. `null` = auto-detect. |

`runQueueAutomatically` at `true` means Craft triggers pending queue jobs by injecting a JavaScript call into CP pages and an AJAX ping into front-end pages. On high-traffic sites this ties up PHP-FPM workers processing queue jobs instead of serving requests. Set `false` in production and run a daemon:

```sh
# In a process manager (Supervisor, systemd, or DDEV custom command)
craft queue/listen --verbose
```

`cacheDuration` affects the default TTL for Craft's data cache (component configurations, element URI caches, GraphQL results). It does not affect `{% cache %}` tag duration, which defaults to the template cache duration setting on the component level.

`backupCommand` at `null` uses Craft's built-in backup mechanism. Set to `false` to disable backups entirely (useful when using an external backup solution). As a `Closure`, it receives the output file path as an argument.

`useFileLocks` at `null` auto-detects whether the filesystem supports `LOCK_EX`. On NFS mounts, file locking is often broken -- set explicitly to `false`. On local filesystems, leave at `null`.

`backupCommand` supports several placeholders that Craft substitutes before execution:

| Placeholder | Value |
|-------------|-------|
| `{file}` | Output file path |
| `{port}` | Database port |
| `{server}` | Database server |
| `{user}` | Database username |
| `{password}` | Database password (escaped) |
| `{database}` | Database name |
| `{schema}` | Database schema (PostgreSQL only) |

Example custom backup command for MySQL with compression:

```php
->backupCommand('mysqldump -h {server} -P {port} -u {user} -p{password} {database} | gzip > {file}')
```

`backupCommandFormat` only applies to PostgreSQL. The `custom` format is recommended for large databases as it supports parallel restore:

```php
->backupCommandFormat('custom')
```

---

## 4. Garbage Collection

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `softDeleteDuration` | `mixed` | `2592000` (30 days) | Time before soft-deleted items are hard-deleted by GC. `0` = never hard-delete. |
| `purgePendingUsersDuration` | `mixed` | `0` (disabled) | Time before pending (unactivated) users are purged. `0` = never purge. |
| `purgeStaleUserSessionDuration` | `mixed` | `7776000` (90 days) | Time before stale user sessions are purged from the DB. (Since 3.3.0) |
| `purgeUnsavedDraftsDuration` | `mixed` | `2592000` (30 days) | Time before unpublished drafts that were never updated are purged. (Since 3.2.0) |

All garbage collection settings only take effect when GC actually runs. GC is triggered probabilistically on web requests (Yii's `gcProbability` defaults to 1/1,000,000) or manually via the `gc` console command. For predictable cleanup, add `craft gc` to your cron schedule.

`softDeleteDuration` at `0` means soft-deleted items are never hard-deleted -- they remain in the database indefinitely with a `dateDeleted` timestamp. This is different from what many expect (they think `0` means "delete immediately"). To make deletes permanent immediately, this is not the right setting -- soft deletion is always the first step. The `softDeleteDuration` controls when the *hard* delete happens during GC.

`purgePendingUsersDuration` at `0` is disabled by default. When enabled, content assigned to pending users is also deleted when those users are purged. Set this carefully on sites with public registration where users may delay activating their accounts.

`purgeUnsavedDraftsDuration` targets "provisional" drafts -- drafts created automatically when an author starts editing but never explicitly saves. These accumulate in the database. The default 30-day cleanup is sensible for most sites. Set to `0` only if you need to retain all draft history indefinitely.

To ensure GC runs predictably, add to your cron schedule:

```
# Run Craft garbage collection daily at 3 AM
0 3 * * * cd /path/to/project && php craft gc --delete-all-trashed
```

The `--delete-all-trashed` flag hard-deletes all soft-deleted items regardless of `softDeleteDuration`. Use without the flag to respect the configured duration.

---

## 5. Localization

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultCpLanguage` | `?string` | `null` | Override CP language for all users. `null` = per-user preference. |
| `defaultCpLocale` | `?string` | `null` | Override CP locale for date/number formatting. `null` = follows CP language. |
| `extraAppLocales` | `string[]` | `[]` | Additional locales beyond installed sites. |
| `localeAliases` | `array` | `[]` | Custom locale aliases with `id`, `aliasOf`, and optional `displayName`. (Since 5.0.0) |

`defaultCpLanguage` forces a single language for the entire CP. Individual users cannot override it. Use when all CP users share a language.

`defaultCpLocale` separates formatting from language. For example, the CP can display in English (`defaultCpLanguage('en')`) but format dates in the European style (`defaultCpLocale('en-GB')`).

`localeAliases` lets you create custom locales for languages not in PHP's `intl` extension:

```php
->localeAliases([
    'smj' => [
        'aliasOf' => 'sv',
        'displayName' => 'Lule Sami',
    ],
])
```

`extraAppLocales` adds locales to the list available in the CP's language dropdowns and site configuration. These locales do not need to correspond to installed sites -- they are just additional formatting options. Useful for multi-region sites where date/number formatting differs by locale.

`timezone` (in the System & Environment section of `config-general.md`) only controls display formatting and Twig date output. The database stores all timestamps in UTC always. Craft normalizes all user-submitted datetimes to UTC before saving, and converts back to the configured timezone for display. This means changing `timezone` retroactively changes how existing dates are displayed but does not alter stored data.

---

## 6. Aliases & Resources

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `aliases` | `array` | `[]` | Custom Yii aliases for all requests. See `config-bootstrap.md` for full alias documentation. |
| `resourceBasePath` | `string` | `'@webroot/cpresources'` | Server path for published CP resources. |
| `resourceBaseUrl` | `string` | `'@web/cpresources'` | URL for published CP resources. |

`aliases` is the primary mechanism for defining path/URL pairs used throughout Craft -- filesystem Base URLs, volume paths, email template paths. Always use `App::env()` for values that differ between environments:

```php
->aliases([
    '@assetBasePath' => App::env('ASSETS_BASE_PATH'),
    '@assetBaseUrl' => App::env('ASSETS_BASE_URL'),
])
```

`resourceBasePath` and `resourceBaseUrl` control where Craft publishes CP assets (JavaScript, CSS, fonts). These must be web-accessible. On ephemeral filesystems (containerized deployments), you may need to point these to a shared or persistent volume.

These aliases can then be used in filesystem Base URL and Base Path settings in the CP. They can also be referenced in templates via the `alias()` Twig function: `{{ alias('@cdnUrl') }}`.

Craft pre-defines several aliases at bootstrap (`@web`, `@webroot`, `@storage`, `@config`, `@templates`, `@vendor`). Custom aliases defined here supplement those. If you define an alias that matches a built-in alias, yours takes precedence.

On ephemeral/containerized deployments, set `CRAFT_EPHEMERAL=true` in your environment variables. This tells Craft to avoid writing to the filesystem where possible -- compiled templates are stored in memory, and other generated files are minimized. This works in conjunction with `resourceBasePath`/`resourceBaseUrl` pointing to a writable location.

---

## 7. File Permissions & Cookies

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultDirMode` | `mixed` | `0775` | Permissions for new directories. `null` = environment-determined. |
| `defaultFileMode` | `?int` | `null` | Permissions for new files. `null` = environment-determined. |
| `defaultCookieDomain` | `string` | `''` | Domain for cookies. Blank = browser determines. Use `'.example.com'` for subdomains. |

`defaultDirMode` and `defaultFileMode` affect all files/directories Craft creates -- compiled templates, uploads, cache files. In containerized environments, these are typically fine at defaults. On shared hosting, you may need `0755` for directories and `0644` for files.

`defaultCookieDomain` with a leading dot (e.g., `'.example.com'`) makes cookies available to all subdomains. Without it, cookies are scoped to the exact domain. Set this when your CP is on `cms.example.com` and your site is on `example.com` and you need shared sessions.

Note: `defaultDirMode` uses octal notation. In PHP, prefix with `0` for octal: `0775`, not `775`. The config file value `0775` translates to Unix permissions `rwxrwxr-x`.

---

## 8. Headless & GraphQL

Brief entries -- see `headless.md` for production guidance, token management, and schema configuration.

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `headlessMode` | `bool` | `false` | Disable front-end template rendering -- API-only mode. |
| `enableGql` | `bool` | `true` | Enable the GraphQL API. |
| `enableGraphqlCaching` | `bool` | `true` | Cache GraphQL query results. Schema changes auto-purge cache. |
| `enableGraphqlIntrospection` | `bool` | `true` | Allow GraphQL introspection queries. Always allowed in CP regardless. |
| `maxGraphqlBatchSize` | `int` | `0` | Max queries per batched request. `0` = unlimited. (Since 4.5.5) |
| `maxGraphqlComplexity` | `int` | `0` | Max query complexity. `0` = unlimited -- set a limit in production. |
| `maxGraphqlDepth` | `int` | `0` | Max query depth. `0` = unlimited -- set a limit in production. |
| `maxGraphqlResults` | `int` | `0` | Max results per query. `0` = unlimited. |
| `allowedGraphqlOrigins` | `array\|null\|false` | `null` | CORS origins for GraphQL. Deprecated since 4.11.0 -- use `craft\filters\Cors`. |
| `gqlTypePrefix` | `string` | `''` | Prefix for all GraphQL type names. |
| `prefixGqlRootTypes` | `bool` | `true` | Apply `gqlTypePrefix` to root `query`, `mutation`, `subscription` types. (Since 3.6.6) |
| `setGraphqlDatesToSystemTimeZone` | `bool` | `false` | Return GraphQL date values in system timezone instead of UTC. |
| `lazyGqlTypes` | `bool` | `false` | Lazily load GraphQL types to reduce memory on large schemas. (Since 5.3.0) |
| `disableGraphqlTransformDirective` | `bool` | `false` | Disable `@transform` directive globally. Deprecated since 5.9.0 -- use per-schema settings. |

All `maxGraphql*` settings default to `0` (unlimited). In production, set nonzero values to prevent denial-of-service through expensive queries. Recommended starting points: `batchSize: 10`, `complexity: 500`, `depth: 10`, `results: 1000`.

`enableGraphqlIntrospection` at `true` allows clients to discover the schema structure. Disable in production if you don't want the schema exposed to unauthenticated requests. Introspection is always available in the CP's GraphiQL playground regardless.

`lazyGqlTypes` at `true` defers loading GraphQL type definitions until they are actually requested. On schemas with many sections, volumes, and fields, this significantly reduces memory usage and startup time. (Since 5.3.0)

`setGraphqlDatesToSystemTimeZone` at `true` returns dates in the system timezone instead of UTC. This can simplify front-end date handling but breaks the convention that APIs return UTC. Document the behavior clearly for API consumers.

`gqlTypePrefix` adds a prefix to all type names. Useful when multiple Craft instances share a federated GraphQL schema and type names would otherwise collide. `prefixGqlRootTypes` controls whether the root types (`query`, `mutation`) also get the prefix.

`allowedGraphqlOrigins` is deprecated since 4.11.0. Use the `craft\filters\Cors` behavior in `config/app.web.php` instead. The filter provides more control (applies to all endpoints, not just GraphQL) and follows the standard Yii2 filter pattern. See `headless.md` for CORS configuration examples.

Production GraphQL hardening:

```php
->enableGql(true)
->enableGraphqlCaching(true)
->enableGraphqlIntrospection(false)
->maxGraphqlBatchSize(10)
->maxGraphqlComplexity(500)
->maxGraphqlDepth(10)
->maxGraphqlResults(1000)
```

---

## 9. Accessibility

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `accessibilityDefaults` | `array` | (see below) | Default CP accessibility preferences for new users. (Since 3.6.4) |

Sub-properties of `accessibilityDefaults`:

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `alwaysShowFocusRings` | `bool` | `false` | Show focus rings on all focused elements, not just keyboard-focused. |
| `useShapes` | `bool` | `false` | Represent statuses with shapes alongside colors (WCAG contrast compliance). |
| `underlineLinks` | `bool` | `false` | Underline links in CP for better visibility. |
| `notificationDuration` | `int` | `5000` | Auto-dismiss notification milliseconds. `0` = indefinite (never auto-dismiss). |

These are defaults for new users only. Existing users' saved preferences are not overridden. Individual users can change their accessibility preferences in their account settings.

Setting `useShapes(true)` is recommended for teams where any member may have color vision deficiency. It adds distinct shapes (circle, square, diamond) alongside status colors so that statuses are distinguishable without relying on color alone.

`notificationDuration` at `0` makes CP flash notifications persist until manually dismissed. This is useful for users who need more time to read success/error messages but can be annoying for fast-paced editors. The default 5000ms (5 seconds) is a good balance.

---

## 10. Preview

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `previewIframeResizerOptions` | `array` | `[]` | iFrame Resizer options for Live Preview. (Since 3.5.0) |
| `useIframeResizer` | `bool` | `false` | Enable iFrame Resizer for Live Preview. Retains scroll position for cross-origin previews. (Since 3.5.5) |

`useIframeResizer` enables the [iFrame Resizer](https://github.com/davidjbradshaw/iframe-resizer) library for Live Preview. This is useful when the preview target is on a different domain (cross-origin) -- it maintains scroll position during content updates and auto-sizes the iframe to match content height. Without it, cross-origin Live Preview works but may jump to the top on every update.

`previewIframeResizerOptions` passes options directly to the iFrame Resizer library. Common options: `{ heightCalculationMethod: 'max' }` for pages with position-fixed elements.

For headless setups where preview targets are on external domains, `useIframeResizer` is typically required for a good Live Preview experience. Without it, the iframe cannot communicate with the parent frame due to cross-origin restrictions, which causes scroll-jump issues.

Note: The front-end application must include the iFrame Resizer content window script (`iframeResizer.contentWindow.min.js`) for this to work. See the [iFrame Resizer documentation](https://github.com/davidjbradshaw/iframe-resizer) for setup instructions on the front-end side.

---

## 11. Development

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `devMode` | `bool` | `false` | Verbose errors, debug toolbar, expanded logging. |
| `disallowRobots` | `bool` | `false` | Send `X-Robots-Tag: none`. Auto-enabled when `devMode` is on. |
| `testToEmailAddress` | `mixed` | `null` | Redirect all system emails to this address. Accepts string or array. |
| `useIdnaNontransitionalToUnicode` | `bool` | `false` | IDNA nontransitional flag for email Unicode conversion. (Since 5.9.0) |

`devMode` does several things simultaneously: enables verbose error pages with stack traces, enables the Yii debug toolbar, expands logging to include every SQL query and template render, sets the `X-Robots-Tag: none` header, and disables template caching by default. In production, this exposes sensitive information and generates enormous log files.

`testToEmailAddress` redirects ALL system emails (activation, password reset, notifications) to the specified address. Useful in staging environments to prevent emails from reaching real users. Can be an array to send to multiple addresses:

```php
->testToEmailAddress([
    'dev@example.com' => 'Dev Team',
    'qa@example.com' => 'QA Team',
])
```

`disallowRobots` sends the `X-Robots-Tag: none` HTTP header, which tells search engine crawlers not to index the site. It is auto-enabled when `devMode` is `true`. Set explicitly on staging environments even when `devMode` is `false`.

Typical development config:

```php
use craft\config\GeneralConfig;
use craft\helpers\App;

return GeneralConfig::create()
    ->devMode(App::env('CRAFT_DEV_MODE') ?? true)
    ->allowAdminChanges(true)
    ->enableTemplateCaching(false)
    ->testToEmailAddress('dev@example.com')
    ->disallowRobots(true);
```

---

## Dangerous Interactions

Settings that interact in non-obvious ways:

- **`devMode` auto-enables `disallowRobots`** -- even if you explicitly set `disallowRobots(false)`, `devMode(true)` overrides it.
- **`headlessMode` requires `baseCpUrl`** when CP and site are on different domains -- without it, the CP generates incorrect action URLs, form submissions, and asset URLs.
- **`allowAdminChanges` vs `safeMode`** -- `safeMode` is stricter, disables plugins entirely. `allowAdminChanges(false)` only prevents schema changes. Do not confuse the two.
- **`asyncCsrfInputs` must be `true` with full-page static caching** (Blitz) -- otherwise cached pages serve stale CSRF tokens that fail validation on form submission.
- **`runQueueAutomatically(false)` requires a separate daemon** -- `craft queue/listen` or a cron job running `craft queue/run`. Without it, queued jobs (transforms, search index updates, email) never execute.
- **`enableCsrfProtection` + `enableCsrfCookie`** -- the cookie is the storage mechanism. `enableCsrfCookie(false)` forces session-based CSRF storage, requiring a session start on every page that calls `csrfInput()`.
- **`trustedHosts` + `ipHeaders` + `secureProtocolHeaders`** -- all three must be configured together behind a reverse proxy. Misconfiguring one while setting another leads to incorrect IP detection or HTTPS detection failures.
- **`staticStatuses` + scheduled publishing** -- statuses won't update dynamically, so scheduled entries won't go live until the `update-statuses` command runs on cron. (Since 5.7.0)
- **`allowUpdates` auto-disabled by `allowAdminChanges(false)`** -- even if you explicitly set `allowUpdates(true)`, it has no effect when `allowAdminChanges` is `false`.
- **`softDeleteDuration(0)` is "never hard-delete"** -- soft-deleted items stay in the DB indefinitely. This is the opposite of what many developers expect (they think `0` means "delete immediately").
- **`preloadSingles` requires clearing compiled templates** -- changing this setting has no effect until you clear caches from the CP Caches utility.
- **`generateTransformsBeforePageLoad` + high-traffic pages** -- transforms generated inline block the request. On first load after a cache clear, this can cause request timeouts if the page references many transforms.
- **`maxCachedCloudImageSize` changed default in 5.9.0** -- upgrading to 5.9+ silently changes behavior from caching cloud images at 2000px to not caching them at all. If you relied on the old behavior, set explicitly.
- **`headlessMode` ignores `loginPath`, `logoutPath`, `setPasswordPath`** -- these front-end paths are not registered, so auth flows must be handled by the front-end application and API calls.
- **`disabledPlugins` per-environment causes schema mismatches** -- if a plugin is disabled in staging but enabled in production, their schema versions diverge and `project.yaml` changes can't be applied cleanly.
- **`enableGql(false)` does not remove the GraphQL endpoint route** -- it returns a 400 error instead of a 404. To fully hide the endpoint, also configure `allowedGraphqlOrigins(false)` or remove it via Cors filter.
- **`timezone` does not affect database storage** -- timestamps are always UTC in the database. Changing `timezone` retroactively changes how all existing dates are displayed.
- **`useEmailAsUsername(true)` mid-project** -- if existing users have usernames different from their emails, changing this setting can cause login issues. Migrate usernames to match emails first.
- **`disable2fa(true)` does not remove existing 2FA configurations** -- it only skips the 2FA challenge. If you re-enable 2FA later, users' existing configurations are restored.

## Quick Reference: Environment-Specific Config Pattern

The recommended pattern for environment-specific configuration without the legacy `'*'`/`'dev'`/`'production'` array syntax:

```php
use craft\config\GeneralConfig;
use craft\helpers\App;

return GeneralConfig::create()
    // Universal settings
    ->cpTrigger('admin')
    ->defaultImageQuality(90)
    ->maxUploadFileSize('64M')
    ->useEmailAsUsername(true)
    ->omitScriptNameInUrls(true)

    // Environment-conditional via env vars (env var always wins)
    ->devMode(App::env('CRAFT_DEV_MODE') ?? false)
    ->allowAdminChanges(App::env('CRAFT_ALLOW_ADMIN_CHANGES') ?? false)
    ->runQueueAutomatically(App::env('CRAFT_RUN_QUEUE_AUTOMATICALLY') ?? false)
    ->testToEmailAddress(App::env('CRAFT_TEST_TO_EMAIL_ADDRESS'))

    // Security
    ->enableCsrfProtection(true)
    ->preventUserEnumeration(true)
    ->sendPoweredByHeader(false)

    // Aliases
    ->aliases([
        '@assetBasePath' => App::env('ASSETS_BASE_PATH'),
        '@assetBaseUrl' => App::env('ASSETS_BASE_URL'),
    ]);
```

Then in `.env` per environment:

```
# .env.dev
CRAFT_DEV_MODE=1
CRAFT_ALLOW_ADMIN_CHANGES=1
CRAFT_RUN_QUEUE_AUTOMATICALLY=1
CRAFT_TEST_TO_EMAIL_ADDRESS=dev@example.com

# .env.production
CRAFT_DEV_MODE=0
CRAFT_ALLOW_ADMIN_CHANGES=0
CRAFT_RUN_QUEUE_AUTOMATICALLY=0
```
