# Configuration

## Documentation

- General config reference: https://craftcms.com/docs/5.x/reference/config/general.html
- Database config reference: https://craftcms.com/docs/5.x/reference/config/db.html
- App config reference: https://craftcms.com/docs/5.x/reference/config/app.html
- Environment config: https://craftcms.com/docs/5.x/configure.html
- `craft\config\GeneralConfig`: https://docs.craftcms.com/api/v5/craft-config-generalconfig.html
- `craft\config\DbConfig`: https://docs.craftcms.com/api/v5/craft-config-dbconfig.html

## Common Pitfalls

- Setting `allowAdminChanges` to `true` in production — schema changes made in the CP won't sync back to `project.yaml`, so the next deploy overwrites them.
- Forgetting `CRAFT_SECURITY_KEY` — encryption keys differ across environments, breaking session cookies, encrypted field values, and password reset tokens.
- Putting secrets in `config/general.php` instead of `.env` — config files are committed to version control, secrets are not.
- Using `config/db.php` when `CRAFT_DB_*` env vars work out of the box — DDEV auto-injects these; a db config file just adds a maintenance surface.
- Editing `config/app.php` without understanding merge order — user config overrides Craft's internal defaults via `yii\helpers\ArrayHelper::merge()`, so partial component definitions can silently drop Craft's own settings.
- Running the queue via web requests on high-traffic sites — set `runQueueAutomatically` to `false` and run a dedicated daemon (`ddev craft queue/listen`) to avoid tying up PHP workers.
- Not understanding that `CRAFT_*` env vars always win — they override config files regardless of what you set in PHP.
- Using the old multi-environment array syntax (`'*'` key) when the fluent API is cleaner and type-safe — the array syntax still works but the fluent API catches typos at the IDE level.

## Contents

- [Config File Overview](#config-file-overview)
- [The Fluent API](#the-fluent-api)
- [Config Priority Order](#config-priority-order)
- [Essential Environment Variables](#essential-environment-variables)
- [GeneralConfig — Key Settings by Category](#generalconfig--key-settings-by-category)
- [App Config — Component Overrides](#app-config--component-overrides)
- [Custom Config](#custom-config)
- [Database Config](#database-config)

## Config File Overview

| File | Purpose |
|------|---------|
| `.env` | Environment variables — secrets, DB credentials, environment name |
| `config/general.php` | General settings — routing, security, sessions, assets, dev mode |
| `config/db.php` | Database connection (usually unnecessary — DDEV auto-injects `CRAFT_DB_*` vars) |
| `config/app.php` | Yii2 component overrides — cache, session, queue, mailer, mutex |
| `config/app.web.php` | Web-only component overrides (session, CORS) |
| `config/app.console.php` | Console-only component overrides |
| `config/custom.php` | Custom key-value config accessed via `craft.app.config.custom` |
| `config/routes.php` | Custom URL routes (site-specific nesting supported) |
| `config/htmlpurifier/` | HTML Purifier configs for CKEditor fields |

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

The old array syntax with `'*'`, `'dev'`, `'production'` keys still works but is discouraged. The fluent API is type-safe, IDE-friendly, and eliminates the environment-merging indirection.

## Config Priority Order

### General Config

Highest priority wins:

1. Craft default values (property declarations on `GeneralConfig`)
2. `config/general.php` (base config)
3. `config/general.web.php` or `config/general.console.php` (app-type specific)
4. `CRAFT_*` environment variables (always win)

### App Config

Merged in order via `ArrayHelper::merge()` — later entries override earlier:

1. Craft's internal `app.php`
2. Craft's internal `app.web.php` / `app.console.php`
3. User's `config/app.php`
4. User's `config/app.web.php` / `config/app.console.php`

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
| `CRAFT_WEB_URL` | Primary site URL |
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

Every public property on `GeneralConfig` maps to `CRAFT_{UPPER_SNAKE_CASE}` automatically. For example, `elevatedSessionDuration` becomes `CRAFT_ELEVATED_SESSION_DURATION`.

## GeneralConfig — Key Settings by Category

Not an exhaustive list. Only the settings developers regularly configure. Type and default shown; every setting maps to a `CRAFT_*` env var following the naming pattern above.

### Routing

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `cpTrigger` | `?string` | `'admin'` | URL segment for the control panel |
| `actionTrigger` | `string` | `'actions'` | URL segment for controller actions |
| `omitScriptNameInUrls` | `bool` | `false` | Remove `index.php` from URLs (requires rewrite rules) |
| `addTrailingSlashesToUrls` | `bool` | `false` | Append trailing slashes to generated URLs |
| `baseCpUrl` | `?string` | `null` | Explicit CP URL — required when CP domain differs from site domain |
| `loginPath` | `mixed` | `'login'` | Front-end login path; set to `false` to disable |
| `logoutPath` | `mixed` | `'logout'` | Front-end logout path; set to `false` to disable |
| `pageTrigger` | `string` | `'p'` | URL param or segment for pagination (`?p=2` or `/p2`) |

### Security

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `allowAdminChanges` | `bool` | `true` | Allow schema/plugin changes in CP. Set `false` in production. |
| `securityKey` | `?string` | `null` | Encryption key — use `CRAFT_SECURITY_KEY` env var instead |
| `enableCsrfProtection` | `bool` | `true` | CSRF token validation. Never disable. |
| `asyncCsrfInputs` | `bool` | `false` | Load CSRF tokens via AJAX — required for full-page static caching |
| `elevatedSessionDuration` | `mixed` | `300` (5 min) | Seconds of elevated session after password re-entry. `0` to disable. |
| `maxInvalidLogins` | `int` | `5` | Failed logins before lockout |
| `preventUserEnumeration` | `bool` | `false` | Return identical responses for valid/invalid usernames |
| `sanitizeSvgUploads` | `bool` | `true` | Strip scripts from SVG uploads |

### Sessions & Users

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `userSessionDuration` | `mixed` | `3600` (1 hr) | Session duration in seconds. `0` = until browser closes. |
| `rememberedUserSessionDuration` | `mixed` | `1209600` (14 days) | Duration when "Remember Me" is checked |
| `useEmailAsUsername` | `bool` | `false` | Hide the username field, use email as the identifier |
| `preloadSingles` | `bool` | `false` | Preload all Single entries as Twig globals |
| `autoLoginAfterAccountActivation` | `bool` | `false` | Log users in automatically after account activation |

### Assets & Images

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `maxUploadFileSize` | `int\|string` | `16777216` (16 MB) | Max upload size. Accepts int (bytes) or string (`'64M'`). |
| `defaultImageQuality` | `int` | `82` | JPEG/WebP quality for transforms |
| `upscaleImages` | `bool` | `true` | Allow transforms to upscale beyond original dimensions |
| `generateTransformsBeforePageLoad` | `bool` | `false` | Generate transforms inline instead of via queue. Slower page loads. |
| `revAssetUrls` | `bool` | `false` | Append `?v={dateModified}` to asset URLs for cache busting |
| `imageDriver` | `mixed` | `'auto'` | `'gd'` or `'imagick'` — auto-detects by default |

### Performance & Caching

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `cacheDuration` | `mixed` | `86400` (1 day) | Default data cache duration in seconds |
| `enableTemplateCaching` | `bool` | `true` | Enable `{% cache %}` tags. Disable in dev for convenience. |
| `runQueueAutomatically` | `bool` | `true` | Trigger queue via web requests. Set `false` in production and use a daemon. |
| `maxRevisions` | `?int` | `50` | Max entry revisions. `null` = unlimited. `0` = no revisions. |

### Development

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `devMode` | `bool` | `false` | Verbose errors, debug toolbar, expanded logging. Never `true` in production. |
| `disallowRobots` | `bool` | `false` | Send `X-Robots-Tag: none` header. Auto-enabled when `devMode` is on. |
| `testToEmailAddress` | `mixed` | `null` | Redirect all system emails to this address (string or array) |
| `translationDebugOutput` | `bool` | `false` | Wrap translated strings with `@@@` to identify untranslated text |

### Headless

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `headlessMode` | `bool` | `false` | Disable front-end template rendering — API-only mode |
| `enableGql` | `bool` | `true` | Enable the GraphQL API |
| `enableGraphqlCaching` | `bool` | `true` | Cache GraphQL query results |
| `maxGraphqlComplexity` | `int` | `0` | Max query complexity (`0` = unlimited — set a limit in production) |
| `maxGraphqlDepth` | `int` | `0` | Max query depth (`0` = unlimited — set a limit in production) |
| `maxGraphqlResults` | `int` | `0` | Max results per query (`0` = unlimited) |

## App Config — Component Overrides

`config/app.php` (and its `.web.php` / `.console.php` variants) override Yii2 application components. The config is a standard Yii2 application configuration array merged on top of Craft's defaults.

### Redis Configuration

Complete Redis setup for cache, session, and mutex. Requires `yiisoft/yii2-redis`:

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'cache' => [
            'class' => yii\redis\Cache::class,
            'redis' => [
                'hostname' => App::env('REDIS_HOST') ?? '127.0.0.1',
                'port' => App::env('REDIS_PORT') ?? 6379,
                'database' => 0,
            ],
        ],
        'mutex' => [
            'class' => yii\redis\Mutex::class,
            'redis' => [
                'hostname' => App::env('REDIS_HOST') ?? '127.0.0.1',
                'port' => App::env('REDIS_PORT') ?? 6379,
                'database' => 0,
            ],
        ],
    ],
];
```

Session must be configured in the web-only file because console requests have no session:

```php
// config/app.web.php
use craft\helpers\App;

return [
    'components' => [
        'session' => function() {
            $config = App::sessionConfig();
            $config['class'] = yii\redis\Session::class;
            $config['redis'] = [
                'hostname' => App::env('REDIS_HOST') ?? '127.0.0.1',
                'port' => App::env('REDIS_PORT') ?? 6379,
                'database' => 1,
            ];
            return Craft::createObject($config);
        },
    ],
];
```

Use a different `database` index for session vs. cache to allow flushing cache without killing sessions.

Craft's queue does NOT have a built-in Redis adapter that preserves the CP queue manager UI. The default database-backed queue works well for most projects. If you need Redis-backed queues, use `ostark/yii2-artisan-bridge` or a custom adapter, but the CP progress indicators will not work.

### CORS Configuration

Craft 5.3+ provides a built-in CORS filter. Apply it as a behavior in the web app config:

```php
// config/app.web.php
return [
    'as corsFilter' => [
        'class' => craft\filters\Cors::class,
        'cors' => [
            'Origin' => ['https://mysite.com'],
            'Access-Control-Request-Method' => ['GET', 'POST', 'OPTIONS'],
            'Access-Control-Request-Headers' => ['Authorization', 'Content-Type', 'X-Craft-Token'],
            'Access-Control-Allow-Credentials' => true,
            'Access-Control-Max-Age' => 86400,
        ],
    ],
];
```

The deprecated `allowedGraphqlOrigins` config setting (removed in Craft 5) is replaced by this filter.

### Logging Customization

The `log` component can be customized in `config/app.php`. By default, Craft logs to `storage/logs/web.log` (web requests) and `storage/logs/console.log` (CLI). In dev mode, logs are also written to `storage/logs/web-*.log` per category.

```php
// config/app.php — add a custom log target
return [
    'components' => [
        'log' => function() {
            $config = craft\helpers\App::logConfig();
            if ($config) {
                $config['targets']['custom'] = [
                    'class' => yii\log\FileTarget::class,
                    'logFile' => '@storage/logs/custom.log',
                    'categories' => ['my-plugin'],
                ];
            }
            return $config ? Craft::createObject($config) : null;
        },
    ],
];
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

Custom config does NOT support `CRAFT_*` env var overrides or the fluent API. It does support the legacy multi-environment `'*'` key pattern for per-environment values, but prefer using `App::env()` calls inside the return array instead.

## Database Config

Usually not needed — DDEV and most hosting platforms inject `CRAFT_DB_*` environment variables that Craft reads automatically. Only create `config/db.php` when you need settings not covered by env vars (like `charset`, `tablePrefix`, or `attributes`).

```php
// config/db.php
use craft\config\DbConfig;

return DbConfig::create()
    ->driver('mysql')
    ->server(craft\helpers\App::env('DB_SERVER') ?? '127.0.0.1')
    ->port(3306)
    ->database('mydb')
    ->user('root')
    ->password('')
    ->tablePrefix('craft_')
    ->charset('utf8mb4');
```

When both `config/db.php` and `CRAFT_DB_*` env vars are present, the env vars win for any property they define.
