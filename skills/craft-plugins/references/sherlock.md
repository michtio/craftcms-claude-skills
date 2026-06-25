# Sherlock

Security scanner and monitor by PutYourLightsOn. Scans for vulnerabilities — file permissions, HTTP headers, CMS configuration, encrypted connections, critical updates, Content Security Policy. Supports scheduled scans, IP-based CP/front-end access restriction, monitoring with email alerts, and integrations with Bugsnag/Rollbar/Sentry. Used in 6/6 projects.

`putyourlightson/craft-sherlock` — Lite (free) / Plus ($199) / Pro ($299)

## Documentation

- Docs: https://putyourlightson.com/plugins/sherlock
- GitHub: https://github.com/putyourlightson/craft-sherlock

When unsure about a feature, `WebFetch` the docs page.

## Editions

| Feature | Lite | Plus | Pro |
|---------|------|------|-----|
| Security scans | ✅ | ✅ | ✅ |
| Encrypted connections | ✅ | ✅ | ✅ |
| Critical updates | ✅ | ✅ | ✅ |
| CMS configuration | ✅ | ✅ | ✅ |
| Header protection | — | ✅ | ✅ |
| Content Security Policy | — | ✅ | ✅ |
| Scheduled scans | — | ✅ | ✅ |
| Monitoring (email alerts) | — | — | ✅ |
| CP access restriction | — | — | ✅ |
| Front-end access restriction | — | — | ✅ |
| Basic auth | — | — | ✅ |
| API | — | — | ✅ |
| Integrations | — | — | ✅ |

## Setup

1. Install via Plugin Store or Composer
2. CP → Sherlock → run first security scan
3. Review results and fix flagged issues

## Scheduled Scans

Set up a cron job for automatic scanning:

```bash
# Daily scan at 3 AM
0 3 * * * cd /path/to/project && ddev craft sherlock/scans/run
```

## Config File

```php
// config/sherlock.php
return [
    '*' => [
        // 'standard' or 'high' security level
        'highSecurityLevel' => false,

        // Maximum number of scan records to keep
        'maxScans' => 50,
    ],
    'production' => [
        'highSecurityLevel' => true,
    ],
];
```

Copy the config template from the plugin's `config.php` for all available settings.

## What It Scans

- **File permissions** — writable directories, exposed config files
- **HTTP headers** — X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- **CORS** — cross-origin resource sharing configuration
- **CSRF** — cross-site request forgery protection
- **Encrypted connections** — HTTPS enforcement on front-end and CP
- **CMS config** — `devMode`, `allowAdminChanges`, `enableCsrfProtection`, etc.
- **Critical updates** — CMS version, plugin versions, PHP version
- **Plugin vulnerabilities** — checks against PutYourLightsOn's vulnerability feed

## Common Pitfalls

- Running in `high` security level on development — some checks only make sense in production. Use environment-based config.
- Ignoring header warnings — HTTP security headers are low-effort, high-impact fixes. Don't dismiss them.
- Not scheduling scans — running manually is better than nothing, but automated daily/weekly scans catch regressions.
- Using Plus when Pro is needed — if you need IP restriction or monitoring, you need Pro edition.

## Pair With

- **Knock Knock** — Sherlock secures the production site, Knock Knock password-protects staging
- **Password Policy** — Sherlock checks CMS config, Password Policy enforces strong user passwords
