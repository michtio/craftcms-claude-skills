# Application Config Reference

Complete reference for `config/app.php` component configuration in Craft CMS 5. For how config files are loaded and merged, see `config-bootstrap.md`. For GeneralConfig settings, see `config-general.md`.

## Documentation

- App config reference: https://craftcms.com/docs/5.x/reference/config/app.html
- Yii2 application config: https://www.yiiframework.com/doc/guide/2.0/en/concept-configurations
- `craft\helpers\App`: https://docs.craftcms.com/api/v5/craft-helpers-app.html

## Common Pitfalls

- Partial component definitions can silently drop Craft's defaults -- `ArrayHelper::merge()` replaces entire arrays by key, not deep-merge by default. Define complete component configs or use closures that start from Craft's helper methods.
- Putting session config in `app.php` instead of `app.web.php` -- console commands crash because there is no HTTP session in CLI context.
- Using the same Redis `database` index for cache and session -- flushing cache kills all active sessions.
- Overriding the queue component with a Redis-backed queue -- loses the CP queue manager progress UI. The default database-backed queue works well for most projects.
- Overriding mailer in `app.php` without using `App::mailerConfig()` as the base -- loses CP email settings (system address, sender name, transport adapter selected in Settings).
- Overriding session without using `App::sessionConfig()` as the base -- loses Craft's `SessionBehavior` which the CP depends on.
- Not running `ddev craft db/search-indexes` after changing search component config -- existing entries are still indexed with the old settings.
- Forgetting `CRAFT_APP_ID` when multiple Craft installs share a cache backend -- cache key collisions cause cross-site data leaks.

## Contents

- [Web vs Console Split](#web-vs-console-split)
- [Cache Component](#cache-component)
- [Session Component](#session-component)
- [Queue Component](#queue-component)
- [Mutex Component](#mutex-component)
- [Mailer / Mail Transport](#mailer--mail-transport)
- [Search Component](#search-component)
- [Log Component](#log-component)
- [CORS Filter](#cors-filter)
- [Database Replicas](#database-replicas)
- [Module Registration](#module-registration)
- [Multi-Site Component](#multi-site-component)
- [Complete Production Example](#complete-production-example)

## Web vs Console Split

### Why three files exist

Craft loads application config from up to three files, merged in order:

| File | Applies To | Merged When |
|------|-----------|-------------|
| `config/app.php` | Both web and console | Always |
| `config/app.web.php` | Web only | HTTP requests |
| `config/app.console.php` | Console only | CLI commands (`ddev craft ...`) |

Craft loads `app.php` first, then merges either `app.web.php` or `app.console.php` on top depending on the request type. Both are merged on top of Craft's internal defaults via `ArrayHelper::merge()`.

### When to use which file

| Component | File | Reason |
|-----------|------|--------|
| Cache | `app.php` | Both web and console need caching |
| Queue | `app.php` | Jobs dispatched from web, processed by console (`craft queue/listen`) |
| Mutex | `app.php` | Both contexts need locking for job coordination |
| Mailer | `app.php` | Both web (form submissions) and console (`craft mailer/test`) send email |
| Search | `app.php` | Both contexts trigger search index operations |
| Log | `app.php` | Both contexts log |
| Session | `app.web.php` | Console has no HTTP session -- will crash if defined in `app.php` |
| CORS filter | `app.web.php` | Only relevant for HTTP requests |
| Custom console controller | `app.console.php` | Only relevant for CLI |

### Split example

```php
// config/app.php -- shared: cache, queue, mutex, mailer, search, log
return [
    'components' => [
        'cache' => [/* ... */],
        'mutex' => [/* ... */],
        'queue' => [/* ... */],
    ],
    'modules' => [
        'my-module' => \modules\Module::class,
    ],
    'bootstrap' => ['my-module'],
];

// config/app.web.php -- web only: session, CORS
return [
    'components' => [
        'session' => function() { /* ... */ },
    ],
    'as corsFilter' => [/* ... */],
];

// config/app.console.php -- console only (rarely needed)
return [];
```

See [Complete Production Example](#complete-production-example) for fully fleshed-out versions of all three files.

## Cache Component

### Database Cache (default)

Craft uses `yii\caching\DbCache` by default. No config needed -- it works out of the box using the `cache` database table.

### Redis Cache

The most common production upgrade. Requires `yiisoft/yii2-redis` (`ddev composer require yiisoft/yii2-redis`).

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'cache' => [
            'class' => yii\redis\Cache::class,
            'redis' => [
                'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                'port' => App::env('REDIS_PORT') ?: 6379,
                'password' => App::env('REDIS_PASSWORD') ?: null,
                'database' => 0,
            ],
            'defaultDuration' => 86400,
            'keyPrefix' => 'craft_', // Optional, prevents collisions
        ],
    ],
];
```

### APCu Cache

Good for single-server deployments where cache does not need to be shared across servers.

```php
// config/app.php
return [
    'components' => [
        'cache' => [
            'class' => yii\caching\ApcCache::class,
            'useApcu' => true,
        ],
    ],
];
```

### Memcached

```php
// config/app.php
return [
    'components' => [
        'cache' => [
            'class' => yii\caching\MemCache::class,
            'useMemcached' => true,
            'servers' => [
                ['host' => 'memcached', 'port' => 11211, 'weight' => 100],
            ],
        ],
    ],
];
```

### Key notes

- Set `CRAFT_APP_ID` env var to prevent cache key collisions between multiple Craft installs sharing a cache backend.
- Use different Redis `database` indexes for cache (e.g. `0`) and session (e.g. `1`). Flushing cache on database 0 will not touch sessions on database 1.
- Redis databases are numbered 0-15 by default. This is configurable in `redis.conf` but the default is fine for most setups.

## Session Component

Session MUST be configured in `config/app.web.php` -- not `app.php`. Console commands have no HTTP session, and defining a session component in the shared config will cause CLI crashes.

### Database Session (default)

Craft uses database-backed sessions by default via `craft\web\Session`. No config needed.

### Redis Session

```php
// config/app.web.php
use craft\helpers\App;

return [
    'components' => [
        'session' => function() {
            // Start from Craft's base config -- this attaches SessionBehavior
            $config = App::sessionConfig();
            $config['class'] = yii\redis\Session::class;
            $config['redis'] = [
                'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                'port' => App::env('REDIS_PORT') ?: 6379,
                'password' => App::env('REDIS_PASSWORD') ?: null,
                'database' => 1, // Different from cache!
            ];
            return Craft::createObject($config);
        },
    ],
];
```

### Why the closure and helper matter

Always use `App::sessionConfig()` as the base -- it attaches Craft's `SessionBehavior` which the CP depends on for flash messages, return URLs, and other session features. Skipping this helper breaks CP functionality. The closure ensures the session object is only created when needed, avoiding unnecessary Redis connections.

## Queue Component

The queue component lives in `app.php` because jobs are dispatched from web requests and processed by console commands.

### Basic configuration

```php
// config/app.php
return [
    'components' => [
        'queue' => [
            'ttr' => 900,        // Time-to-reserve: 15 min per job (default: 300)
            'attempts' => 3,     // Max retry attempts (default: 1)
            'channel' => 'queue', // Channel name for multi-app setups
        ],
    ],
];
```

### Redis Queue (via proxyQueue)

Craft 5 wraps the underlying queue driver in `craft\queue\Queue`, which provides the CP progress UI. To use Redis as the backend while preserving the UI, configure `proxyQueue`:

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'queue' => [
            'proxyQueue' => [
                'class' => yii\queue\redis\Queue::class,
                'redis' => [
                    'class' => yii\redis\Connection::class,
                    'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                    'port' => App::env('REDIS_PORT') ?: 6379,
                    'password' => App::env('REDIS_PASSWORD') ?: null,
                    'database' => 2,
                ],
            ],
            'channel' => 'queue',
            'ttr' => 900,
        ],
    ],
];
```

Requires both `yiisoft/yii2-redis` and `yiisoft/yii2-queue[redis]`.

In production, set `runQueueAutomatically` to `false` in `config/general.php` and run `ddev craft queue/listen --verbose` as a daemon or supervisor job. For most projects, the default database-backed queue without `proxyQueue` is sufficient.

## Mutex Component

### File Mutex (default)

No config needed. Uses the `storage/mutex/` directory for lock files.

### Redis Mutex

Required for multi-server deployments or NFS/shared filesystems where file-based locks do not work reliably.

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'mutex' => function() {
            return Craft::createObject([
                'class' => craft\mutex\Mutex::class,
                'mutex' => [
                    'class' => yii\redis\Mutex::class,
                    'redis' => [
                        'class' => yii\redis\Connection::class,
                        'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                        'port' => App::env('REDIS_PORT') ?: 6379,
                        'password' => App::env('REDIS_PASSWORD') ?: null,
                        'database' => 0,
                    ],
                    'expire' => 30, // Lock auto-expires after 30 seconds
                ],
            ]);
        },
    ],
];
```

Note the `craft\mutex\Mutex` wrapper -- do not use the Yii redis mutex class directly as the top-level component. Switch from file mutex when: NFS/shared filesystems where `flock()` fails, multi-server deployments, or Docker/Kubernetes with ephemeral storage.

## Mailer / Mail Transport

### How it works

Craft's mailer (`craft\mail\Mailer`) wraps Symfony Mailer. Transport is configured either via the CP (Settings > Email) or programmatically in `app.php`. CP settings are stored in project config and are the recommended approach for most setups.

### CP Configuration (Settings > Email)

Configures: System Email Address, Reply-To, Sender Name, HTML Email Template (receives `body` variable), Transport adapter, and per-site overrides (Craft 5.6+). Settings are stored in project config. Use the **Test** button to verify delivery before saving.

### Built-in Transport Adapters

**SMTP** (most common for production):

Usually configured in CP Settings > Email. For programmatic override:

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'mailer' => function() {
            // Start from Craft's config to preserve CP settings
            $config = App::mailerConfig();

            $adapter = craft\helpers\MailerHelper::createTransportAdapter(
                craft\mail\transportadapters\Smtp::class,
                [
                    'host' => App::env('SMTP_HOST'),
                    'port' => App::env('SMTP_PORT'),
                    'username' => App::env('SMTP_USERNAME'),
                    'password' => App::env('SMTP_PASSWORD'),
                    'encryptionMethod' => 'tls',
                ]
            );

            $config['transport'] = $adapter->defineTransport();
            return Craft::createObject($config);
        },
    ],
];
```

**Gmail**: Requires an App Password (not a regular Google password). Standard password authentication was removed by Google in May 2022. Enable IMAP access in Gmail settings, then generate an App Password from Google Account security.

**Sendmail**: Uses `/usr/sbin/sendmail -bs`. Unreliable unless the host has a properly configured MTA. Avoid in production.

### Plugin Transport Adapters

Third-party plugins provide API-based transport that communicates over HTTP instead of SMTP:

| Plugin | Package | Service |
|--------|---------|---------|
| Amazon SES | `craftcms/aws-ses` | AWS Simple Email Service |
| Mailgun | `craftcms/mailgun` | Mailgun |
| Postmark | `craftcms/postmark` | Postmark |
| Sendgrid | `craftcms/sendgrid` | SendGrid |

After installing, the adapter appears in Settings > Email transport dropdown. More reliable than SMTP for high-volume sending.

### Development: DDEV + Mailpit

DDEV includes Mailpit out of the box. All outgoing mail is captured at `https://yoursite.ddev.site:8026` -- no configuration needed. For non-DDEV environments, use `testToEmailAddress` in `config/general.php` to redirect all mail to a single address.

### Environment-Specific Transport

When you need different transports per environment (e.g., Mailpit in dev, SES in production), use a conditional override:

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'mailer' => function() {
            $config = App::mailerConfig();

            if (Craft::$app->getConfig()->getGeneral()->devMode) {
                $adapter = craft\helpers\MailerHelper::createTransportAdapter(
                    craft\mail\transportadapters\Smtp::class,
                    [
                        'host' => App::env('MAILPIT_SMTP_HOSTNAME') ?: 'localhost',
                        'port' => App::env('MAILPIT_SMTP_PORT') ?: 1025,
                    ]
                );
                $config['transport'] = $adapter->defineTransport();
            }

            return Craft::createObject($config);
        },
    ],
];
```

In production, this falls through to the CP-configured transport (e.g., AWS SES plugin). In dev, it overrides with Mailpit.

### Important notes

- `App::mailerConfig()` is essential when overriding -- without it, system email address, sender name, and CP settings are lost.
- Changes in `app.php` are NOT reflected when testing from Settings > Email -- the test button uses CP settings directly.
- Multi-site: mail settings use the user's preferred site for per-site overrides (Craft 5.6+).

## Search Component

```php
// config/app.php
return [
    'components' => [
        'search' => [
            'useFullText' => true,        // Default: true (MySQL only, ignored on PostgreSQL)
            'minFullTextWordLength' => 4,  // Must match MySQL's innodb_ft_min_token_size
        ],
    ],
];
```

### Why this matters

MySQL fulltext search silently ignores words shorter than its configured minimum token size. If Craft's `minFullTextWordLength` is lower than MySQL's actual `innodb_ft_min_token_size` (default: 3 for InnoDB), Craft assumes short words are indexed but MySQL ignores them. Search results go missing with no error.

### Configuration steps

1. Check your MySQL config:

```sql
SHOW VARIABLES LIKE 'innodb_ft_min_token_size';
-- Default: 3 for InnoDB
```

2. Set Craft's `minFullTextWordLength` to match the MySQL value.
3. After changing, rebuild the search index:

```
ddev craft db/search-indexes
```

### Interaction with GeneralConfig

The `defaultSearchTermOptions` setting in `config/general.php` controls search behavior at query time. Setting `subLeft => true` forces `LIKE` queries that bypass fulltext entirely -- useful for "starts with" matching but slower on large datasets. See `config-general.md` for details.

### PostgreSQL

PostgreSQL does not support MySQL-style fulltext indexing. Craft falls back to `LIKE` queries automatically. The `useFullText` setting is ignored on PostgreSQL. For better PostgreSQL search performance, consider external search services like Typesense, Meilisearch, or Algolia.

## Log Component

```php
// config/app.php
return [
    'components' => [
        'log' => function() {
            $config = craft\helpers\App::logConfig();
            if ($config) {
                // Add a custom file target
                $config['targets']['custom'] = [
                    'class' => yii\log\FileTarget::class,
                    'logFile' => '@storage/logs/custom.log',
                    'categories' => ['my-plugin'],
                    'levels' => ['error', 'warning', 'info'],
                ];

                // Example: Sentry target (requires sentry/sdk)
                // $config['targets']['sentry'] = [
                //     'class' => \sentry\log\SentryTarget::class,
                //     'levels' => ['error', 'warning'],
                // ];
            }
            return $config ? Craft::createObject($config) : null;
        },
    ],
];
```

### Default behavior

- Web requests log to `storage/logs/web.log`
- Console commands log to `storage/logs/console.log`
- In `devMode`, additional per-category log files are written (e.g. `storage/logs/web-craft-queue.log`)

### Filtering by category

Yii log categories follow a hierarchical naming pattern. Setting `categories` to `['my-plugin']` captures all messages logged with that category. Use `['my-plugin*']` (wildcard) to match subcategories like `my-plugin/services` and `my-plugin/controllers`.

### Suppressing noisy categories

```php
$config['targets']['file']['except'] = [
    'yii\db\Command::query',
    'yii\db\Command::execute',
];
```

## CORS Filter

Brief coverage here -- see `headless.md` for the full headless/hybrid pattern.

```php
// config/app.web.php
return [
    'as corsFilter' => [
        'class' => craft\filters\Cors::class,
        'cors' => [
            'Origin' => ['https://mysite.com', 'https://app.mysite.com'],
            'Access-Control-Request-Method' => ['GET', 'POST', 'OPTIONS'],
            'Access-Control-Request-Headers' => ['Authorization', 'Content-Type', 'X-Craft-Token'],
            'Access-Control-Allow-Credentials' => true,
            'Access-Control-Max-Age' => 86400,
        ],
    ],
];
```

Must be in `app.web.php` -- CORS is an HTTP concern with no meaning in console context.

The `as corsFilter` key attaches this as a Yii2 behavior on the application object, so it runs on every web request. The `craft\filters\Cors` class extends Yii's CORS filter with Craft-specific defaults.

## Database Replicas

Read replicas offload SELECT queries from the primary database to one or more replica servers.

```php
// config/app.php
use craft\helpers\App;

return [
    'components' => [
        'db' => function() {
            $config = App::dbConfig();
            $config['replicaConfig'] = [
                'username' => App::env('DB_REPLICA_USER'),
                'password' => App::env('DB_REPLICA_PASSWORD'),
                'tablePrefix' => App::env('CRAFT_DB_TABLE_PREFIX'),
                'attributes' => [PDO::ATTR_TIMEOUT => 10],
                'charset' => 'utf8',
            ];
            $config['replicas'] = [
                ['dsn' => App::env('DB_REPLICA_DSN_1')],
                ['dsn' => App::env('DB_REPLICA_DSN_2')],
            ];
            return Craft::createObject($config);
        },
    ],
];
```

Caveats: replication lag means read-after-write may return stale data. Craft handles this for its own operations but custom queries may see stale results. Each replica adds a database connection -- monitor limits. Most Craft projects do not need read replicas.

## Module Registration

```php
// config/app.php
return [
    'modules' => [
        'my-module' => \modules\Module::class,
    ],
    'bootstrap' => ['my-module'],
];
```

`modules` registers the class mapping -- Craft knows it exists but does not initialize it until requested. `bootstrap` initializes on every request -- only add modules here if they register event listeners, behaviors, or routes. Modules that only respond to specific controller actions do not need bootstrapping.

### Multiple modules

```php
return [
    'modules' => [
        'site-module' => \modules\sitemodule\Module::class,
        'api-module' => \modules\apimodule\Module::class,
    ],
    'bootstrap' => ['site-module'], // Only bootstrap modules that need it
];
```

## Multi-Site Component

Craft has a soft cap of 100 sites. Override in `app.php` for large multi-site installations:

```php
// config/app.php
return [
    'components' => [
        'sites' => [
            'maxSites' => 5000,
        ],
    ],
];
```

This is a Craft-level setting, not a hosting constraint. Be aware that 100+ sites significantly increases project config file size, migration complexity, and general performance overhead. Test thoroughly before scaling to large site counts.

## Complete Production Example

A full production config with Redis for cache/session/mutex, SMTP mailer, and search tuning.

```php
// config/app.php
use craft\helpers\App;

return [
    'id' => App::env('CRAFT_APP_ID'),
    'components' => [
        'cache' => [
            'class' => yii\redis\Cache::class,
            'redis' => [
                'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                'port' => App::env('REDIS_PORT') ?: 6379,
                'password' => App::env('REDIS_PASSWORD') ?: null,
                'database' => 0,
            ],
            'defaultDuration' => 86400,
        ],
        'mutex' => function() {
            return Craft::createObject([
                'class' => craft\mutex\Mutex::class,
                'mutex' => [
                    'class' => yii\redis\Mutex::class,
                    'redis' => [
                        'class' => yii\redis\Connection::class,
                        'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                        'port' => App::env('REDIS_PORT') ?: 6379,
                        'password' => App::env('REDIS_PASSWORD') ?: null,
                    ],
                ],
            ]);
        },
        'queue' => [
            'ttr' => 900,
            'attempts' => 3,
        ],
        'search' => [
            'minFullTextWordLength' => 3,
        ],
        'log' => function() {
            $config = craft\helpers\App::logConfig();
            if ($config) {
                $config['targets']['custom'] = [
                    'class' => yii\log\FileTarget::class,
                    'logFile' => '@storage/logs/application.log',
                    'categories' => ['application', 'modules\*'],
                    'levels' => ['error', 'warning'],
                ];
            }
            return $config ? Craft::createObject($config) : null;
        },
    ],
    'modules' => [
        'site-module' => \modules\sitemodule\Module::class,
    ],
    'bootstrap' => ['site-module'],
];
```

```php
// config/app.web.php
use craft\helpers\App;

return [
    'components' => [
        'session' => function() {
            $config = App::sessionConfig();
            $config['class'] = yii\redis\Session::class;
            $config['redis'] = [
                'hostname' => App::env('REDIS_HOSTNAME') ?: 'localhost',
                'port' => App::env('REDIS_PORT') ?: 6379,
                'password' => App::env('REDIS_PASSWORD') ?: null,
                'database' => 1,
            ];
            return Craft::createObject($config);
        },
    ],
];
```

```
# .env (production)
CRAFT_APP_ID=mysite-production
CRAFT_ENVIRONMENT=production
CRAFT_SECURITY_KEY=your-secret-key-here
CRAFT_DEV_MODE=0
CRAFT_ALLOW_ADMIN_CHANGES=0
CRAFT_RUN_QUEUE_AUTOMATICALLY=0

REDIS_HOSTNAME=redis.internal
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```
