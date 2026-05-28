# Cloud Limitations and Plugin Compatibility

What Cloud doesn't support, what's force-enabled or force-disabled, and a community-knowledge map of which third-party plugins work, conflict, or are redundant on Cloud.

The first section is documented limitations from Pixel & Tonic. The plugin-compatibility section at the end is **community knowledge, not Pixel & Tonic-blessed** — verify against your own project's needs and the plugin author's current Cloud-compatibility statements.

## Documentation

- Services and compatibility: https://craftcms.com/docs/cloud/compatibility
- Quotas: https://craftcms.com/docs/cloud/quotas
- FAQ: https://craftcms.com/docs/cloud/faq

## Table of contents

- [Documented unsupported features](#documented-unsupported-features)
  - [Filesystems](#filesystems)
  - [Database](#database)
  - [Mail](#mail)
  - [Server access](#server-access)
  - [Force-enabled settings](#force-enabled-settings)
  - [Strongly discouraged](#strongly-discouraged)
  - [Deploy](#deploy)
  - [Runtime caps](#runtime-caps)
  - [Plan quotas](#plan-quotas-from-httpscraftcmscomdocscloudquotas)
- [Authored-content gaps](#authored-content-gaps)
  - [Mail (community recommendations)](#mail-community-recommendations)
  - [Logs (the gap)](#logs-the-gap)
  - [Per-PR preview environments](#per-pr-preview-environments)
  - [Rollback](#rollback)
- [Plugin compatibility (community knowledge)](#plugin-compatibility-community-knowledge)
- [What to do when something doesn't work](#what-to-do-when-something-doesnt-work)

## Documented unsupported features

### Filesystems
- **Local filesystems don't work.** Convert all asset volumes to the Cloud filesystem type (see `assets-and-transforms.md`).
- **Third-party S3 plugins for asset storage.** Use Cloud's bundled filesystem type, not `craftcms/aws-s3` or similar — Cloud's filesystem is wired to the platform-managed bucket.
- **Direct server filesystem access.** No way to read or write arbitrary paths on the underlying Lambda container.

### Database
- **MariaDB is not supported.** MySQL 8.0 or Postgres 15 only.
- **`tablePrefix` is unsupported.** Run `php craft db/drop-table-prefix` before migrating.
- **`CRAFT_DB_TABLE_PREFIX` env var is unsupported.**
- **Custom `backupCommand` settings.** Will produce unreliable backups — use Cloud's backup interface.
- **CP Database Backup utility is disabled.**

### Mail
- **No built-in mail service.** The default `sendmail` adapter will not work. Configure your own SMTP transport.

### Server access
- **No SSH.** Console command runner is the only way to execute commands (255-char cap, 15-min cap, no shell features). See `commands-and-cron.md`.
- **No `.htaccess` or nginx config editing.** Use `redirects:` and `rewrites:` in `craft-cloud.yaml`. See `config-file.md`.

### Force-enabled settings
- **`asyncCsrfInputs` is force-enabled.** Required for static caching to work. Plugins must use the `csrfInput()` Twig function — never raw token output. See `plugin-development.md` (CSRF).

### Strongly discouraged
- **`devMode` and `allowAdminChanges` are technically possible** but Pixel & Tonic explicitly warns against enabling them on Cloud: "Making changes to your project's schema on Cloud can result in your database and Project Config files diverging, as well as data loss." Treat the prod environment as read-only at the schema level; make schema changes in code and deploy.

### Deploy
- **Forked Git repositories can't be deployed.** Must be the upstream repo.
- **No automated environment cloning.** Moving content between environments is manual (DB export/import + asset sync).
- **No region change post-creation.** Pick the right region at project creation — see https://craftcms.com/docs/cloud/regions.
- **No per-PR preview environments.** Cloud supports per-branch environments only — pull requests don't get an ephemeral environment automatically. Workaround: dedicate one of your environments to a `preview` branch and merge PR branches into it for staging review.

### Runtime caps
| Limit | Value |
|---|---|
| Web request timeout | 60 seconds |
| Web response size | 6MB (CP asset uploads exempt) |
| File upload | 200MB |
| Build duration | 15 minutes |
| CLI command duration | 15 minutes |
| Queue job duration | 15 minutes |
| Console command argument length | 255 characters (after `craft`) |
| Console command history retention | 6 months |
| Scheduled commands per environment | 5 |
| Scheduled command minimum interval | 1 hour |

### Plan quotas (from https://craftcms.com/docs/cloud/quotas)

| Plan | Environments | Storage / env | Bandwidth / month |
|---|---|---|---|
| Team | 2 | 10 GB | 250 GB |
| Pro | 3 | 20 GB | 500 GB |

Additional environments are not purchasable. Additional root domains can be purchased — pricing in Console.

## Authored-content gaps

The following topics are real concerns Pixel & Tonic's docs cover thinly or not at all. The material below is **community knowledge** synthesized from the Cloud extension source and community discussion as of 2026-05-28.

### Mail (community recommendations)

Cloud has no built-in mail service. The supported pattern is: bring your own SMTP transport and configure it via `config/app.php` or env vars.

Common adapters (none Cloud-blessed):

| Adapter | Use when |
|---|---|
| Postmark | Transactional volume, easy DNS verification, good deliverability defaults |
| Amazon SES | High volume, already in AWS, comfortable with the email-reputation lifecycle |
| SendGrid | Established choice; complex pricing |
| Resend | Modern API, developer-friendly, smaller deliverability footprint than incumbents |
| Plain SMTP (Mailgun, Mailtrap, your own) | Sensible defaults for staging or low-volume production |

A typical Postmark config in `config/app.php`:

```php
return [
    'components' => [
        'mailer' => function() {
            $settings = App::mailSettings();
            $settings->transportType = \craft\mailer\transportadapters\Smtp::class;
            $settings->transportSettings = [
                'host' => App::env('SMTP_HOST'),
                'port' => 587,
                'useAuthentication' => true,
                'username' => App::env('SMTP_USERNAME'),
                'password' => App::env('SMTP_PASSWORD'),
                'encryptionMethod' => 'tls',
            ];
            $mailer = Craft::createObject(App::mailerConfig($settings));
            return Craft::createObject($mailer);
        },
    ],
];
```

Set `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` in the Console env vars per environment. See the `craftcms` skill's `email.md` for the full Craft mailer surface.

### Logs (the gap)

Cloud routes `Craft::info/warning/error()` to a Cloud-managed log target, but there is **no log-tailing UI documented today**. The de-facto surface is:

- Console command output — when you run a command via the Console runner, output (including any logs from that command's execution) is captured in the command history.
- Web request logs — not directly tailable. You can see error-level events through the Console UI's monitoring sections.

For persistent operational logs in production, route to an external service via Monolog handler in `config/app.php`:

```php
return [
    'components' => [
        'log' => [
            'targets' => [
                [
                    'class' => \yii\log\SyslogTarget::class,
                    // or PapertrailHandler, LogglyHandler, etc.
                    'levels' => ['error', 'warning'],
                ],
            ],
        ],
    ],
];
```

This is **community pattern**, not Pixel & Tonic doctrine. Verify the specific handler config against the third-party library's docs.

### Per-PR preview environments

Cloud doesn't auto-create environments per pull request. The supported model is per-branch — each environment tracks one branch.

Workarounds:

- **Shared preview environment.** Designate one Cloud environment as `preview`. Merge PR branches into a `preview` branch (or push directly) when you want stakeholder review. Reset state between previews if needed.
- **Branch-per-feature with environment swap.** Available on the Pro plan with 3 environments — keep one staging environment that can be retargeted per active PR. Manual environment retargeting.
- **External preview infrastructure.** Spin up a separate Craft instance (DDEV-share, ngrok tunnel, scratch VPS) for PR previews when Cloud's per-branch model isn't sufficient. Costs more to operate.

### Rollback

There is no one-click rollback to a prior build. The supported recovery pattern:

```sh
git revert <bad-commit>
git push
```

This triggers a new build that deploys the prior state. Both Build and Migrate phases run again — if the prior state had a migration that's already applied, Craft's standard migration tracking handles the no-op.

For schema rollbacks (a migration introduced a problem), the right path is to write a forward migration that undoes the bad change, not to try to "roll back" the schema. Craft's migration history is append-only.

## Plugin compatibility (community knowledge)

The table below reflects the community's current understanding of how popular third-party plugins behave on Cloud. **Not Pixel & Tonic-blessed.** Plugin authors update their Cloud-compatibility frequently — when in doubt, check the plugin's GitHub README or the plugin store's "Tested on Craft Cloud" badge.

| Plugin | Cloud status | Notes |
|---|---|---|
| **ImageOptimize** (nystudio107) | **Don't use** | Cloud handles transforms at the edge via Cloudflare Images. ImageOptimize duplicates the work and can produce stale references. Remove during migration. |
| **Imager-X** (spacecatninja) | **Don't use for transforms** | Same reason as ImageOptimize — Cloud's edge transforms supersede. If you only used Imager-X for advanced features (focus points, color extraction), evaluate per-feature. |
| **Blitz** (putyourlightson) | **Largely redundant** | Cloud's edge static caching covers the same job. Running both produces conflicting cache layers. Remove Blitz or use one or the other, not both. |
| **SEOmatic** (nystudio107) | **Works** | No filesystem writes that conflict; meta-tag generation is standard Craft. |
| **Sprig** (putyourlightson) | **Works** | HTMX-based, no Cloud-specific concerns. |
| **Formie** (verbb) | **Works** | Watch the file-upload field — uploads go through the asset volume system, which uses Cloud's filesystem correctly. |
| **CKEditor** (craftcms) | **Works** | First-party, Cloud-tested. |
| **Typesense / Algolia / Meilisearch integrations** | **Works as external services** | Search runs on the third-party platform, not on Cloud. Cloud doesn't host the search engine itself. |
| **Redactor** (craftcms) | **Works** | First-party, Cloud-tested. |
| **Commerce** (craftcms) | **Works** | First-party, Cloud-tested. |
| **Freeform** (solspace) | **Verify** | Generally works; verify file-upload fields work with Cloud's filesystem. Check Solspace's Cloud-compatibility note. |
| **Spam Hammer / honeypot plugins** | **Works** | Pure logic, no filesystem dependencies. |
| **MatrixMate / Field Manager** (verbb) | **Works** | CP UI plugins, no Cloud-specific concerns. |
| **Schematic / Migration Manager** | **Verify** | Project Config-related plugins; verify they don't bypass Craft's project-config sync mechanism that Cloud relies on. |
| **Plugins with custom queue workers** | **Verify** | Cloud auto-processes queue jobs. A plugin that ships its own queue worker (rare) may conflict. |
| **Plugins that write to disk** | **Verify per plugin** | If the plugin doesn't use `Craft::$app->getPath()->...` or gate on `App::isEphemeral()`, writes are silently lost on Cloud. Check the plugin's repo for `App::isEphemeral` or `getTempPath` usage. |

This table is **a snapshot as of 2026-05-28**. Verify current status before relying on it. Plugin authors actively update Cloud-compatibility, and Cloud itself evolves.

## What to do when something doesn't work

Cloud's troubleshooting page (https://craftcms.com/docs/cloud/troubleshooting) covers the platform-side failure modes (repo not visible, build failures, certificate issues). For Craft-side issues that surface only on Cloud:

1. **Reproduce locally with `CRAFT_EPHEMERAL=true`** if the issue is filesystem-related. See `local-dev.md` (Optional: testing ephemeral code paths).
2. **Check Console command output** for recent migrations and `cloud/up` runs — they often surface the underlying error.
3. **Compare with a working environment.** If staging works and production doesn't, diff the env vars in Console.
4. **Reach out via the Craft Discord** (`#cloud` channel) — community and Pixel & Tonic staff respond to specific issues.

Last verified against https://craftcms.com/docs/cloud/compatibility and https://craftcms.com/docs/cloud/quotas on 2026-05-28. Plugin-compatibility table is community knowledge and may drift faster than the official surface.
