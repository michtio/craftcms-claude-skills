# Config Bootstrap

How Craft CMS 5 loads configuration: environment variables, aliases, config files, priority order, and the fluent API. This reference covers the loading mechanics — what files exist, how they interact, and what wins when they conflict.

## Documentation

- Environment config: https://craftcms.com/docs/5.x/configure.html
- General config reference: https://craftcms.com/docs/5.x/reference/config/general.html
- App config reference: https://craftcms.com/docs/5.x/reference/config/app.html
- `craft\config\GeneralConfig`: https://docs.craftcms.com/api/v5/craft-config-generalconfig.html
- `craft\config\DbConfig`: https://docs.craftcms.com/api/v5/craft-config-dbconfig.html

## Common Pitfalls

- `CRAFT_*` env vars always win over config files — this is a silent override. If `CRAFT_DEV_MODE=1` is set in `.env`, setting `->devMode(false)` in `config/general.php` has no effect. No warning is emitted.
- Putting secrets in `config/general.php` instead of `.env` — config files are committed to version control, secrets are not.
- Using `config/db.php` when DDEV auto-injects `CRAFT_DB_*` vars — the db config file just adds a maintenance surface with no benefit.
- Editing `config/app.php` without understanding merge order — `ArrayHelper::merge()` replaces array values by key, so a partial component definition can silently drop Craft's own settings. Define complete component configs or use closures.
- `@web` is empty in console context (queue jobs, CLI) unless `CRAFT_WEB_URL` is set — queue jobs that generate absolute URLs will produce broken links.
- Not setting `CRAFT_APP_ID` when multiple Craft installs share a cache backend — cache key collisions cause cross-site data leaks.
- Using the old multi-environment array syntax (`'*'` key) when the fluent API is cleaner and type-safe — the array syntax still works but the fluent API catches typos at the IDE level.

## Contents

- [Config File Overview](#config-file-overview)
- [The Fluent API](#the-fluent-api)
- [Config Priority Order](#config-priority-order)
- [Essential Environment Variables](#essential-environment-variables)
- [Aliases](#aliases)
- [Custom Config](#custom-config)
- [Database Config](#database-config)
- [Routes Config](#routes-config)
- [HTML Purifier](#html-purifier)

## Config File Overview

| File | Purpose |
|------|---------|
| `.env` | Environment variables — secrets, DB credentials, environment name |
| `config/general.php` | General settings — routing, security, sessions, assets, dev mode |
| `config/general.web.php` | Web-only general config overrides |
| `config/general.console.php` | Console-only general config overrides |
| `config/db.php` | Database connection (usually unnecessary — DDEV auto-injects `CRAFT_DB_*` vars) |
| `config/app.php` | Yii2 component overrides — cache, session, queue, mailer, mutex |
| `config/app.web.php` | Web-only component overrides (session, CORS) |
| `config/app.console.php` | Console-only component overrides |
| `config/custom.php` | Custom key-value config accessed via `craft.app.config.custom` |
| `config/routes.php` | Custom URL routes (site-specific nesting supported) |
| `config/htmlpurifier/` | HTML Purifier configs for CKEditor fields |

All config files return a PHP array or fluent config object. None of these files are required — Craft has sensible defaults for everything. Create them only when you need to override a default.

The `.web.php` and `.console.php` variants are app-type specific. Craft loads the base file first, then merges the variant on top. This is useful for settings that only make sense in one context — for example, session config is meaningless in console commands.

## The Fluent API

The modern pattern for `config/general.php`:

```php
use craft\config\GeneralConfig;

return GeneralConfig::create()
    ->devMode(true)
    ->cpTrigger('admin')
    ->allowAdminChanges(false)
    ->defaultImageQuality(90)
    ->maxUploadFileSize('64M');
```

Boolean setters default to `true` when called without arguments — `->devMode()` is equivalent to `->devMode(true)`.

The fluent API also works for `config/db.php` via `DbConfig::create()`.

### Old Array Syntax

The multi-environment array syntax with `'*'`, `'dev'`, `'production'` keys still works:

```php
return [
    '*' => [
        'cpTrigger' => 'admin',
        'maxUploadFileSize' => '64M',
    ],
    'dev' => [
        'devMode' => true,
        'allowAdminChanges' => true,
    ],
    'production' => [
        'allowAdminChanges' => false,
        'runQueueAutomatically' => false,
    ],
];
```

This is discouraged. The fluent API is type-safe, IDE-friendly, and eliminates the environment-key merging indirection. With the fluent API, use `App::env()` calls for environment-specific values instead of the key-based approach.

## Config Priority Order

### General Config

Highest priority wins:

1. Craft default values (property declarations on `GeneralConfig`)
2. `config/general.php` (base config)
3. `config/general.web.php` or `config/general.console.php` (app-type specific)
4. `CRAFT_*` environment variables (always win)

Step 4 is the critical one. Environment variables are applied last and cannot be overridden by any config file. This is by design — it allows deployment platforms to control behavior without touching code.

### App Config

Merged in order via `ArrayHelper::merge()` — later entries override earlier:

1. Craft's internal `app.php`
2. Craft's internal `app.web.php` / `app.console.php`
3. User's `config/app.php`
4. User's `config/app.web.php` / `config/app.console.php`

`ArrayHelper::merge()` is a deep merge — nested arrays are merged recursively. But scalar values and indexed arrays are replaced, not appended. If you define a component partially, the merge may drop Craft's defaults for that component. When in doubt, use a closure that calls `App::sessionConfig()` or similar helpers to start from Craft's base config.

## Essential Environment Variables

### Core

| Variable | Purpose |
|----------|---------|
| `CRAFT_ENVIRONMENT` | Environment name — `dev`, `staging`, `production`. Controls which config overrides apply. |
| `CRAFT_DEV_MODE` | Enable dev mode without touching config files. Overrides `devMode`. |
| `CRAFT_SECURITY_KEY` | Encryption key for cookies, sessions, encrypted fields. Must be identical across all servers in the same environment. |
| `CRAFT_APP_ID` | Unique application ID — prevents cache collisions when multiple Craft installs share a cache backend. |
| `CRAFT_LICENSE_KEY` | Craft license key. Can also live in `config/license.key`. |

### Database

DDEV auto-injects all of these. Only set manually in non-DDEV environments.

| Variable | Purpose |
|----------|---------|
| `CRAFT_DB_DRIVER` | `mysql` or `pgsql` |
| `CRAFT_DB_SERVER` | Database hostname |
| `CRAFT_DB_PORT` | Database port (`3306` for MySQL, `5432` for PostgreSQL) |
| `CRAFT_DB_USER` | Database username |
| `CRAFT_DB_PASSWORD` | Database password |
| `CRAFT_DB_DATABASE` | Database name |
| `CRAFT_DB_TABLE_PREFIX` | Table prefix (default: none) |

### Paths

| Variable | Purpose |
|----------|---------|
| `CRAFT_BASE_PATH` | Override the base project path |
| `CRAFT_STORAGE_PATH` | Override `storage/` location |
| `CRAFT_TEMPLATES_PATH` | Override `templates/` location |
| `CRAFT_WEB_URL` | Primary site URL — critical for console context where no HTTP request exists |
| `CRAFT_WEB_ROOT` | Web root path (used for asset volumes with local filesystems) |

### Operational

| Variable | Purpose |
|----------|---------|
| `CRAFT_ALLOW_ADMIN_CHANGES` | Override `allowAdminChanges` |
| `CRAFT_CP_TRIGGER` | Override `cpTrigger` |
| `CRAFT_SITE` | Default site handle for console commands |
| `CRAFT_HEADLESS_MODE` | Override `headlessMode` |
| `CRAFT_RUN_QUEUE_AUTOMATICALLY` | Override `runQueueAutomatically` |
| `CRAFT_EPHEMERAL` | Optimizes for ephemeral/read-only filesystems (disables generated files, stores compiled templates in memory) |

### Auto-Mapping Rule

Every public property on `GeneralConfig` maps to `CRAFT_{UPPER_SNAKE_CASE}` automatically. For example:

| Property | Environment Variable |
|----------|---------------------|
| `devMode` | `CRAFT_DEV_MODE` |
| `elevatedSessionDuration` | `CRAFT_ELEVATED_SESSION_DURATION` |
| `maxUploadFileSize` | `CRAFT_MAX_UPLOAD_FILE_SIZE` |
| `cpTrigger` | `CRAFT_CP_TRIGGER` |

This means any setting you can configure via the fluent API can also be set via an environment variable. The env var always wins.

## Aliases

Craft pre-defines these aliases at bootstrap:

| Alias | Resolves To |
|-------|-------------|
| `@web` | Auto-detected from HTTP request; primary site Base URL in console |
| `@webroot` | Web root directory (document root) |
| `@storage` | `storage/` directory |
| `@config` | `config/` directory |
| `@contentMigrations` | `migrations/` directory |
| `@templates` | `templates/` directory |
| `@app` | Craft's source directory (Yii convention) |
| `@vendor` | `vendor/` directory (Yii convention) |
| `@runtime` | `storage/runtime/` directory (Yii convention) |

### Custom Aliases

Define custom aliases in `config/general.php` via the fluent API:

```php
use craft\config\GeneralConfig;
use craft\helpers\App;

return GeneralConfig::create()
    ->aliases([
        '@assetBasePath' => App::env('ASSETS_BASE_PATH'),
        '@assetBaseUrl' => App::env('ASSETS_BASE_URL'),
    ]);
```

Custom aliases are used in:
- Volume settings (Base URL, File System Path)
- Email template paths
- Asset filesystem configs
- Twig templates via the `alias()` function: `{{ alias('@assetBaseUrl') }}`

### The @web Problem

`@web` is auto-detected from the HTTP request. In console commands (queue jobs, CLI), there is no request, so `@web` resolves from the primary site's Base URL. If that Base URL is empty or relative, `@web` is empty in console context.

This breaks queue jobs that generate absolute URLs (e.g., asset transforms, search index URLs, email links).

The fix: set `CRAFT_WEB_URL` and `CRAFT_WEB_ROOT` environment variables. These provide explicit values that work in both web and console contexts.

```
# .env
CRAFT_WEB_URL=https://mysite.com
CRAFT_WEB_ROOT=/var/www/html/web
```

## Custom Config

For project-specific settings that don't belong in `GeneralConfig`:

```php
// config/custom.php
use craft\helpers\App;

return [
    'gtmId' => App::env('GTM_ID'),
    'analyticsEnabled' => App::env('ANALYTICS_ENABLED') ?? false,
    'supportEmail' => 'support@example.com',
    'maxApiResults' => 100,
];
```

Access in Twig:

```twig
{% if craft.app.config.custom.analyticsEnabled %}
    <script src="https://www.googletagmanager.com/gtm.js?id={{ craft.app.config.custom.gtmId }}"></script>
{% endif %}
```

Access in PHP:

```php
$gtmId = Craft::$app->config->custom->gtmId;
```

Custom config does NOT support `CRAFT_*` env var auto-mapping or the fluent API. Use `App::env()` calls inside the return array for environment-specific values.

The legacy multi-environment `'*'` key pattern works but is unnecessary — `App::env()` is more explicit and doesn't require matching `CRAFT_ENVIRONMENT`.

## Database Config

Usually not needed — DDEV and most hosting platforms inject `CRAFT_DB_*` environment variables that Craft reads automatically. Only create `config/db.php` when you need settings not covered by env vars (like `charset`, `tablePrefix`, or connection `attributes`).

```php
// config/db.php
use craft\config\DbConfig;
use craft\helpers\App;

return DbConfig::create()
    ->driver('mysql')
    ->server(App::env('DB_SERVER') ?? '127.0.0.1')
    ->port(3306)
    ->database('mydb')
    ->user('root')
    ->password('')
    ->tablePrefix('craft_')
    ->charset('utf8mb4');
```

When both `config/db.php` and `CRAFT_DB_*` env vars are present, the env vars win for any property they define. This follows the same priority rule as general config.

## Routes Config

`config/routes.php` defines custom URL routes that map URL patterns to templates:

```php
// config/routes.php
return [
    'feed' => ['template' => '_feeds/rss'],
    'api/<slug:{slug}>' => ['template' => '_api/detail'],
    'archive/<year:\d{4}>/<month:\d{2}>' => ['template' => '_archive/month'],
];
```

URL tokens use Yii2 route syntax — `<paramName:regex>` captures a named parameter. Common token patterns:

| Token | Regex | Matches |
|-------|-------|---------|
| `{slug}` | `[^\/]+` | Any non-slash string |
| `{uid}` | `[0-9a-f]{8}-...` | UUID format |
| `{handle}` | `[a-zA-Z][a-zA-Z0-9_]*` | Valid handle |
| `\d{4}` | (literal) | Four digits |

### Site-Specific Routes

Nest routes under site handles to scope them to a specific site:

```php
// config/routes.php
return [
    'english' => [
        'feed' => ['template' => '_feeds/rss-en'],
        'api/<slug:{slug}>' => ['template' => '_api/detail'],
    ],
    'french' => [
        'flux' => ['template' => '_feeds/rss-fr'],
    ],
];
```

The top-level keys are site handles. Routes defined at the top level (not nested) apply to all sites. You can mix site-specific and global routes in the same file.

### Routes vs Section URLs

Routes defined here take precedence over section URL patterns. If a route matches, Craft renders the specified template and does not check section URLs. Use this for pages that don't map to entries — feeds, API endpoints, utility pages.

## HTML Purifier

The `config/htmlpurifier/` directory contains JSON config files used by CKEditor fields to sanitize HTML content on save.

Each CKEditor field references a purifier config by filename (without extension) in its field settings. If no config is specified, Craft uses a sensible default that strips scripts and dangerous attributes.

The JSON format follows [HTML Purifier's configuration schema](http://htmlpurifier.org/live/configdoc/plain.html):

```json
{
    "Attr.AllowedFrameTargets": ["_blank"],
    "Attr.EnableID": true,
    "HTML.AllowedComments": ["pagebreak"],
    "HTML.SafeIframe": true,
    "URI.SafeIframeRegexp": "%^(https?:)?//(www\\.youtube\\.com/embed/|player\\.vimeo\\.com/video/)%"
}
```

Place configs at `config/htmlpurifier/MyConfig.json`. The filename (minus `.json`) appears in the CKEditor field settings dropdown.

Common use cases:
- Allowing `target="_blank"` on links
- Permitting iframe embeds from specific domains (YouTube, Vimeo)
- Enabling HTML comments for CKEditor page break markers
- Allowing `id` attributes for anchor links
