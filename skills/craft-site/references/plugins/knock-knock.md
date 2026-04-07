# Knock Knock

Site-wide password protection by Verbb. Locks the entire front-end behind a password prompt — ideal for staging, client preview, and pre-launch sites. Simple config-file driven, no database tables.

`verbb/knock-knock` — Free

## Documentation

- Docs: https://verbb.io/craft-plugins/knock-knock/docs
- GitHub: https://github.com/verbb/knock-knock

## Common Pitfalls

- Leaving Knock Knock enabled in production — the most common mistake. Use environment-aware config to ensure it's only active on staging/preview.
- Not excluding health check or webhook URLs — external services (uptime monitors, CI/CD webhooks, n8n) get blocked by the password wall. Exclude their paths.
- Forgetting that Knock Knock uses a cookie — once authenticated, the cookie persists. If you change the password, existing authenticated sessions remain valid until the cookie expires.

## Config File

```php
// config/knock-knock.php
use craft\helpers\App;

return [
    '*' => [
        'enabled' => false,
        'password' => App::env('KNOCK_KNOCK_PASSWORD'),
        'loginPath' => 'knock-knock/who-is-there',
        'template' => '',                    // Custom template path (optional)
        'forcedRedirect' => '',              // Redirect after login (optional)

        // URLs that bypass the password wall
        'unprotectedUrls' => [
            'api/.*',                        // API endpoints
            'actions/.*',                    // Craft action URLs
            'webhooks/.*',                   // Webhook endpoints
        ],
    ],
    'staging' => [
        'enabled' => true,
    ],
    'production' => [
        'enabled' => false,
    ],
];
```

## Environment Setup

Add to `.env` on staging only:

```bash
KNOCK_KNOCK_PASSWORD=clientPreview2025
```

## Custom Login Template

Override the default login page with your own template:

```php
'template' => '_knock-knock/login',
```

Then create `templates/_knock-knock/login.twig` with your branded login form.

## Pair With

- **Blitz** — Knock Knock checks run before Blitz serves cached pages, so protected sites work correctly with static caching.
