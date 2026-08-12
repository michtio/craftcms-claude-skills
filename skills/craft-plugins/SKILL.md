---
name: craft-plugins
description: "Index and router for plugin-specific Craft CMS 5 guidance — configuration, Twig API, PHP API, migrations, deployment, and pitfalls for the plugins this pack documents. A plugin task routes here at any altitude: front-end, back-end PHP, content modeling, or deployment. Triggers whenever a task names one of these plugins in ANY context (build, configure, style, render, query, import, migrate, deploy, cache, debug): Formie (forms, submissions, File Upload, form in a migration, notifications, translations), SEOmatic (meta, sitemaps, JSON-LD, SEO field), Blitz (static/page caching, purge), Feed Me (XML/JSON/CSV import), Imager-X (transforms, srcset), ImageOptimize (OptimizedImages), CKEditor (rich text, nested entries), Sprig (reactive, htmx), Element API (JSON endpoints), Retour (redirects, 404s), Navigation (nav menus), Hyper (link field), Colour Swatches, Password Policy (HIBP), Typogrify, Cache Igniter, Knock Knock (staging password), Elements Panel (N+1 debug), Sherlock (security scan), Amazon SES (SES/SNS bounce), Embedded Assets (oEmbed), Timeloop (recurring dates), Vite (craft.vite.*, asset bundling), Warp (passwordless login, magic link, one-time code/OTP, passkeys, WebAuthn, craft.warp, member sessions). Also load for passwordless or magic-link auth with NO plugin named. Always load when a task names one of these plugins — read references/<plugin>.md first. Do NOT trigger for Craft core with no plugin named (craftcms), template architecture (craft-site), or content modeling (craft-content-modeling)."
---

# Craft CMS 5 — Plugin References (Index & Router)

This skill is a **router**, not a tutorial. Its job is to make per-plugin
guidance discoverable from any task framing — front-end, back-end PHP, content
migration, deployment, or config — and point you at the right reference file.

Each plugin's curated reference lives in `references/<plugin>.md` and covers
configuration, the Twig and/or PHP API, and the real-world pitfalls. Read the
matching reference **before** implementing anything plugin-specific.

## How to use this skill

1. Identify the plugin(s) named in the task (by name, package, or feature).
2. Open the matching `references/<plugin>.md` from the table below.
3. If the task is back-end (PHP, content migration, events, deployment), check
   the reference's back-end / programmatic sections specifically — several
   plugins (Formie, Feed Me, Element API, Amazon SES) are primarily or
   substantially back-end despite historically living under the front-end skill.

## Routing table

| Reference | Plugin (vendor) | Primary altitude | Key surface |
|-----------|-----------------|------------------|-------------|
| `references/formie.md` | Formie (verbb) | Front-end **and** back-end | Form rendering (one-line/granular), theme config; **programmatic form creation in a content migration**, editing an existing form's field in a migration, forms as DB elements (not project config), cross-environment deployment, multi-site/static translation, overriding Formie's bundled strings (server + client `window.FormieTranslations`), native min/max length validation & its two message keys, `required`+`min` interaction, File Upload volume + file renaming, notification attachments, captcha & caching |
| `references/seomatic.md` | SEOmatic (nystudio107) | Front-end + config | Meta cascade, Twig get/set API, JSON-LD, custom element SEO bundles, sitemaps, GraphQL |
| `references/blitz.md` | Blitz (putyourlightson) | Mixed (front-end + ops) | Refresh modes, Twig dynamic content, driver architecture (storage/purger/deployer), Nginx rewrite, Cloudflare integration |
| `references/feed-me.md` | Feed Me (craftcms) | **Back-end / ops** | Data import from XML/JSON/CSV, field mapping, duplicate handling, CLI automation, scheduled imports |
| `references/imager-x.md` | Imager-X (spacecatninja) | Front-end + config | Advanced image transforms, batch generation, named presets, effects, optimizers, external storage |
| `references/image-optimize.md` | ImageOptimize (nystudio107) | Front-end + field config | OptimizedImages field, `imgTag()`/`pictureTag()` builders, loading strategies, transform methods, console commands |
| `references/ckeditor.md` | CKEditor (craftcms) | Mixed (field config + front-end) | Field settings (toolbar, headings, image mode), nested entries with chunk rendering and value helpers, link configuration, GraphQL Mode, ES-module custom plugins, HTML Purifier, Redactor migration |
| `references/sprig.md` | Sprig (putyourlightson) | Front-end | Reactive Twig components (htmx), live search, load more, pagination, filtering, form submissions without JS |
| `references/element-api.md` | Element API (craftcms) | **Back-end / config** | JSON API via config file, Fractal transformers, endpoint routing, pagination, caching |
| `references/retour.md` | Retour (nystudio107) | Ops / config | Redirect types (exact/regex), 404 tracking, CSV import, auto slug-change redirects, config |
| `references/navigation.md` | Navigation (verbb) | Front-end | Node querying, custom rendering, active states, custom fields on nodes, GraphQL |
| `references/hyper.md` | Hyper (verbb) | Front-end + field config | Link types, `getLinkAttributes()`, `getText()`, single/multi-link, element access, button atom integration |
| `references/colour-swatches.md` | Colour Swatches (craftpulse) | Mixed | Palette config, multi-colour swatches, Tailwind class mapping, Twig model API |
| `references/password-policy.md` | Password Policy (craftpulse) | **Back-end / config** | Validation rules, HIBP check, retention/expiry, console commands, recommended settings |
| `references/typogrify.md` | Typogrify (nystudio107) | Front-end | `\|typogrify`, `\|widont`, `\|truncateOnWord`, smart quotes, widow prevention |
| `references/cache-igniter.md` | Cache Igniter (putyourlightson) | Ops | GlobalPing warmer, geographic locations, refresh delay, Blitz companion |
| `references/knock-knock.md` | Knock Knock (verbb) | Ops / config | Staging password protection, environment-aware config, URL exclusions |
| `references/timeloop.md` | Timeloop (craftpulse) | Mixed | Repeating date field, `craft.timeloop` variable API, `recurringDates()` function, GraphQL, period frequencies |
| `references/elements-panel.md` | Elements Panel (putyourlightson) | Dev tooling | Debug toolbar panels for element population counts, duplicate detection, eager-loading opportunities |
| `references/sherlock.md` | Sherlock (putyourlightson) | Ops / config | Security scanning, HTTP headers, CMS config checks, scheduled scans, IP restriction, monitoring |
| `references/embedded-assets.md` | Embedded Assets (spicyweb) | Mixed | oEmbed as first-class assets, `craft.embeddedAssets.get()`, iframe customization, GraphQL |
| `references/amazon-ses.md` | Amazon SES (putyourlightson) | **Back-end / config** | SES mail transport adapter, AWS credential config, SNS bounce tracking (no Twig API) |
| `references/warp.md` | Warp (craftpulse) | Front-end **and** back-end | Passwordless member auth: magic links (**`mlToken`**, never `token`), emailed one-time codes + segmented input, passkeys/WebAuthn, passwordless registration, session/device management. `craft.warp` variable, four fluent render builders (class accumulation + `resetClass`, key-by-key `data` merge, `renderCss`), `@layer warp` CSS escape, ten action routes (`returnUrl` vs Craft's `redirect` asymmetry, enumeration-safe responses, recent-auth-gated passkey routes), DOM contracts for hand-written markup |
| `references/vite.md` | Vite (nystudio107) | Front-end + buildchain | `craft.vite.*` Twig API (`script`, `register`, `entry`, `asset`, `integrity`, `inline`, `includeCriticalCssTags`, `devServerRunning`), `vite.php` config keys. Buildchain/`vite.config.ts` detail in the `craft-site` skill's `references/vite-buildchain.md` |

## Companion skills

- **`craftcms`** — for the Craft core APIs a plugin task builds on: element saving, events, migrations, queue jobs, field-value storage. Load alongside this skill for any plugin **PHP/migration** work.
- **`craft-site`** — for front-end template architecture the plugin output slots into (components, layouts, image presets). Load alongside this skill for plugin **rendering/styling** work.
- **`craft-content-modeling`** — when the plugin interacts with sections, fields, volumes, or multi-site propagation.
- **`craft-cloud` / `servd`** — when the plugin task involves deployment, edge caching, or ephemeral-filesystem constraints.
