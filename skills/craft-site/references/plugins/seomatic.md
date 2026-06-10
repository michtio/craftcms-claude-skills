# SEOMatic

Comprehensive SEO toolkit by nystudio107. Auto-renders HTML meta tags, JSON-LD structured data, OpenGraph, Twitter Cards, XML sitemaps, robots.txt, and humans.txt. Used on every project.

`nystudio107/craft-seomatic` — $99

## Documentation

- Overview: https://nystudio107.com/docs/seomatic/
- Configuration: https://nystudio107.com/docs/seomatic/configuring/
- Twig templating: https://nystudio107.com/docs/seomatic/using/
- Advanced usage: https://nystudio107.com/docs/seomatic/advanced.html
- Content SEO: https://nystudio107.com/docs/seomatic/content.html
- Site settings: https://nystudio107.com/docs/seomatic/site.html

When unsure about an SEOMatic feature, `WebFetch` the relevant docs page.

## Common Pitfalls

- Putting SEOMatic Twig variables inside `{% cache %}` tags — SEOMatic dynamically generates meta on each request using its own cache. Wrapping in `{% cache %}` freezes the output after the first render.
- Using `entry` as the variable name in custom element config files — custom element types use their own `refHandle()` (e.g., `job` for a Job element, not `entry`). Check the element class's `refHandle()` method.
- Setting SEO values in Twig that are already mapped in Content SEO — Content SEO mappings (`{seoField}` → entry fields) take precedence unless you override in Twig with `{% do seomatic.meta.seoTitle("...") %}`.
- Forgetting that `seomatic-config` files only apply on initial bundle creation — changes after the bundle exists have no effect unless you bump `bundleVersion` in `Bundle.php`.
- Not configuring Content SEO per-section — SEOMatic's power is in automatic field mapping. If you rely only on the SEO Settings field, you're doing extra work.
- Missing `{% hook 'seomaticRender' %}` when headless — auto-rendering works for traditional templates. Headless/hybrid setups need explicit rendering or the GraphQL API.
- Hardcoding JSON-LD in templates instead of using SEOMatic's container system — breaks the cascade and loses CP configurability. (Exception: complex per-entry structured data with real field values is often cleaner as a Twig partial — see "Managing DB-Backed Settings via Content Migrations".)
- Assuming Site Settings, the robots.txt template, and Content SEO sync via project config — they're **DB-backed** (the `seomatic_metabundles` table), not project config. Change them reproducibly with a content migration (`JSON_SET` + `clearAllCaches()`) on any host. See "Managing DB-Backed Settings via Content Migrations".
- `fromField` Content SEO source pointed at a field that's empty on some entries — SEOMatic falls back to the global/homepage meta, giving every such entry the **same** description (sitewide duplicate meta). Use `fromCustom` with an object-template fallback chain instead.
- Confusing `mainEntityOfPage` (per-page schema type, e.g. `Article`) with `siteType`/`siteSubType`/`siteSpecificType` (the global `Organization`/`LocalBusiness` identity) — they live in different columns and do different jobs.

## Meta Cascade

SEOMatic's meta values cascade from broad to specific. Each level can override the previous:

1. **Global SEO** — site-wide defaults (identity, creator, social, sitemap)
2. **Content SEO** — per-section/category/product-type mappings (fields → meta)
3. **SEO Settings Field** — per-entry overrides (optional field, not required)
4. **Twig Overrides** — template-level `{% do seomatic.meta.seoTitle("...") %}`

In most cases, Global SEO + Content SEO mapping covers everything. The SEO Settings field is only needed when editors need per-entry override capability.

## Template Integration

### Auto-Rendering (Default)

SEOMatic auto-injects meta into `<head>` on every front-end request. No Twig code needed. This is how most projects work — including all of ours.

### Explicit Rendering

If you need control over placement or are using headless:

```twig
{# Render all SEOMatic meta in one call #}
{% hook 'seomaticRender' %}
```

### Disable Auto-Rendering

In `config/seomatic.php`:

```php
return [
    'renderEnabled' => false,
];
```

Then render manually via the hook or GraphQL.

## Twig API

### Reading Values

```twig
{{ seomatic.meta.seoTitle }}
{{ seomatic.meta.seoDescription }}
{{ seomatic.meta.seoImage }}
{{ seomatic.meta.canonicalUrl }}
{{ seomatic.meta.robots }}
```

### Setting Values

```twig
{% do seomatic.meta.seoTitle("Custom Title") %}
{% do seomatic.meta.seoDescription("Custom description for this page.") %}
{% do seomatic.meta.seoImage(entry.heroImage.one().url ?? '') %}
{% do seomatic.meta.robots("noindex,nofollow") %}
```

### Parsed Values (Final Output)

```twig
{{ seomatic.meta.parsedValue('seoDescription') }}
```

### Accessing Tag Objects Directly

```twig
{# Get a specific meta tag #}
{% set robotsTag = seomatic.tag.get('robots') %}
{% do robotsTag.content("noindex") %}

{# Disable a tag entirely #}
{% do seomatic.tag.get('description').include(false) %}

{# Add custom data attributes #}
{% set tag = seomatic.tag.get('description') %}
{% if tag|length %}
    {% do tag.tagAttrs({ 'data-type': 'seo' }) %}
{% endif %}
```

### Accessing JSON-LD

```twig
{# Modify the main entity JSON-LD #}
{% set jsonLd = seomatic.jsonLd.get('mainEntityOfPage') %}
{% do jsonLd.setAttributes({
    'name': 'Custom Name',
    'description': 'Custom description',
}) %}
```

### Helper Functions

```twig
{# Sanitize user input before setting SEO values #}
{% set safeValue = seomatic.helper.sanitizeUserInput(someUnsafeInput) %}

{# Truncate text to SEO-friendly length #}
{% set truncated = seomatic.helper.truncate(longText, 160) %}

{# Extract text from a CKEditor/rich text field #}
{% set plainText = seomatic.helper.extractTextFromField(entry.body) %}
```

## Config File

Copy the plugin's default settings to `config/seomatic.php` for environment-aware overrides:

```php
// config/seomatic.php
return [
    '*' => [
        'pluginName' => 'SEO',
        'renderEnabled' => true,
        'sitemapsEnabled' => true,
        'headlessMode' => false,
        'lowMemoryMode' => false,
    ],
    'production' => [
    ],
    'dev' => [
        'sitemapsEnabled' => false,
    ],
];
```

## Custom Element SEO Bundles

For custom element types (plugins like Cockpit), create per-element config overrides in `config/seomatic-config/{handle}meta/`:

```
config/seomatic-config/
└── jobpostmeta/
    ├── Bundle.php           # Bundle version, source template
    ├── BundleSettings.php   # Field mappings
    ├── GlobalVars.php       # Meta variable templates
    ├── JsonLdContainer.php  # JSON-LD structured data
    ├── LinkContainer.php    # Link tags (canonical, etc.)
    ├── ScriptContainer.php  # Script tags
    ├── SitemapVars.php      # Sitemap settings
    ├── TagContainer.php     # Meta tags
    └── TitleContainer.php   # Title tag template
```

The directory name must match `{refHandle}meta` — where `refHandle` comes from the element class's `refHandle()` method (e.g., `job` → `jobpostmeta`).

### GlobalVars.php Example (Custom Element)

```php
return [
    '*' => [
        'mainEntityOfPage' => 'WebPage',
        'seoTitle' => '{{ job.title }}',         // Uses refHandle, NOT 'entry'
        'seoDescription' => '{{ job.description }}',
        'canonicalUrl' => '{{ job.url }}',
        'robots' => 'all',
        'ogType' => 'website',
        'ogTitle' => '{{ seomatic.meta.seoTitle }}',
        'ogDescription' => '{{ seomatic.meta.seoDescription }}',
        'twitterCard' => 'summary_large_image',
        // ... remaining OG/Twitter fields cascade from seomatic.meta
    ],
];
```

### JsonLdContainer.php Example (JobPosting)

```php
'data' => [
    'mainEntityOfPage' => [
        'type' => 'JobPosting',
        'name' => '{{ seomatic.meta.seoTitle }}',
        'description' => '{{ seomatic.meta.seoDescription }}',
        'url' => '{{ seomatic.meta.canonicalUrl }}',
        'datePosted' => '{{ job.postDate|date("c") }}',
        'hiringOrganization' => [
            'type' => 'Organization',
            'name' => '{{ job.department.one().title ?? "" }}',
        ],
        'jobLocation' => [
            'type' => 'Place',
            'address' => [
                'type' => 'PostalAddress',
                'addressLocality' => '{{ job.city ?? "" }}',
                'addressCountry' => 'BE',
            ],
        ],
    ],
],
```

These files are only read when initially creating a meta bundle (plugin install or new section created). Bump `bundleVersion` in `Bundle.php` to force a re-read.

## Managing DB-Backed Settings via Content Migrations

Many SEOMatic settings are **DB-backed, not project config** — they live in the `seomatic_metabundles` table and **do not sync via project config**:

- **Site Settings** — Identity (`genericUrl`, organization/person name, social profiles)
- **The robots.txt template** (and humans.txt)
- **Per-section Content SEO** — field mappings, sources, per-section meta templates

Because they're not in project config, the reproducible way to change them — version-controlled, repeatable across every environment, no manual CP clicking — is a **content migration** that edits the JSON columns with MySQL `JSON_SET`, then clears SEOMatic's caches with `Seomatic::$plugin->clearAllCaches()`.

This is **host-independent**: the migration is identical on self-hosted, shared hosting, Servd, Craft Cloud, and locally — SEOMatic stores these settings in the database the same way everywhere. It's simply the *only* option on a host that gives you no production CP access (e.g. Craft Cloud), and the right approach everywhere else for the same reasons you'd migrate any other configuration rather than hand-editing prod.

> Project-config-backed settings (`config/seomatic.php` and the `seomatic-config/` bundle files above) deploy normally. This section is only about the settings that *aren't* in project config.

### `seomatic_metabundles` Table Shape

| `sourceBundleType` | Keyed by | Rows | Holds |
|---|---|---|---|
| `__GLOBAL_BUNDLE__` | `sourceSiteId` | one per site | `metaSiteVars` (identity, `genericUrl`, social), `frontendTemplatesContainer` (robots.txt, humans.txt) |
| `section` | `sourceHandle` | **two per section** — section-level (`typeId` NULL) **and** entry-type-level (`typeId` set) | `metaGlobalVars`, `metaBundleSettings` (Content SEO) |

The columns `metaGlobalVars`, `metaSiteVars`, `metaBundleSettings`, and `frontendTemplatesContainer` are JSON stored in **text columns**, but MySQL's `JSON_SET` / `JSON_EXTRACT` operate on them fine.

Two things that bite:

- **Per-section bundles exist at two levels.** A section usually has a section-level row (`typeId IS NULL`) *and* an entry-type-level row per entry type (`typeId` set), sharing the same `sourceHandle`. **Both normally need the same edit** — filtering on `sourceHandle` alone (no `typeId` predicate) hits all of them, which is usually what you want.
- **`frontendTemplatesContainer` holds the robots.txt template as a JSON-escaped string**, and its line endings vary per site. `JSON_EXTRACT` it first to confirm the exact path and current value before you `JSON_SET` a replacement.
- **Confirm every JSON path first.** SEOMatic's internal nesting shifts between versions (e.g. exactly where `genericUrl` and the social profiles sit under `metaSiteVars`). `SELECT JSON_EXTRACT([[<column>]], '$') FROM {{%seomatic_metabundles}} WHERE …` and eyeball the structure before composing `JSON_SET` paths — don't trust a path from memory.

### Worked Migration

```php
<?php

namespace craft\contentmigrations;

use Craft;
use craft\db\Migration;
use nystudio107\seomatic\Seomatic;

/**
 * Updates DB-backed SEOMatic settings (the seomatic_metabundles table) via a
 * migration, then clears caches so the change is reproducible across every
 * environment. Host-independent — same on self-hosted, Servd, Cloud, and local.
 *
 * @author Acme
 */
class m260610_090000_seomatic_settings extends Migration
{
    // Public Methods
    // =========================================================================

    /**
     * @inheritdoc
     */
    public function safeUp(): bool
    {
        $db = Craft::$app->getDb();

        // --- Global bundle (per site): Identity genericUrl ---
        // metaSiteVars is JSON; JSON_SET edits keys in place. One row per site,
        // so scope by sourceSiteId (genericUrl usually differs per site).
        $db->createCommand(
            <<<SQL
            UPDATE {{%seomatic_metabundles}}
            SET [[metaSiteVars]] = JSON_SET([[metaSiteVars]], '$.identity.genericUrl', :url)
            WHERE [[sourceBundleType]] = '__GLOBAL_BUNDLE__' AND [[sourceSiteId]] = :siteId
            SQL,
            [':url' => 'https://example.com', ':siteId' => 1]
        )->execute();

        // --- Per-section Content SEO: fix the empty-field fallback (see gotcha) ---
        // No typeId predicate → updates BOTH the section-level row (typeId NULL)
        // and the entry-type-level row(s), matched by handle.
        $db->createCommand(
            <<<SQL
            UPDATE {{%seomatic_metabundles}}
            SET [[metaBundleSettings]] = JSON_SET([[metaBundleSettings]], '$.seoDescriptionSource', 'fromCustom'),
                [[metaGlobalVars]]     = JSON_SET([[metaGlobalVars]], '$.seoDescription', :tmpl)
            WHERE [[sourceBundleType]] = 'section' AND [[sourceHandle]] = :handle
            SQL,
            [
                ':handle' => 'blog',
                // Object-template with its own fallback chain (see gotcha below).
                ':tmpl' => '{{ entry.seoSummary ?: entry.summary ?: entry.title }}',
            ]
        )->execute();

        // robots.txt lives in frontendTemplatesContainer as a JSON-escaped string.
        // Inspect the exact path + current value first (line endings vary per site):
        //   SELECT JSON_EXTRACT([[frontendTemplatesContainer]], '$') FROM {{%seomatic_metabundles}}
        //   WHERE [[sourceBundleType]] = '__GLOBAL_BUNDLE__' AND [[sourceSiteId]] = 1;
        // then JSON_SET the template key you find with the full replacement string.

        // Reset SEOMatic's caches so the edited bundles take effect.
        Seomatic::$plugin->clearAllCaches();

        return true;
    }

    /**
     * @inheritdoc
     */
    public function safeDown(): bool
    {
        echo "m260610_090000_seomatic_settings cannot be reverted.\n";
        return false;
    }
}
```

Scaffold the stub with `ddev craft migrate/create seomatic_settings` (a content migration in `migrations/`), commit it, and it runs on every environment's next migrate — `ddev craft up` locally, the migrate step of your deploy in prod, on whatever host. `clearAllCaches()` invalidates the in-DB meta containers. If a host runs an edge or static cache in front (Cloud's Cloudflare layer, Servd's static cache, any CDN), its post-deploy purge clears the rendered meta; locally there's nothing to purge. For multi-site, loop sites (or drop the `sourceSiteId` predicate when the value is genuinely site-agnostic — `genericUrl` rarely is).

### Gotcha — Empty-Field Fallback (Sitewide Duplicate Descriptions)

`metaBundleSettings.seoTitleSource` / `seoDescriptionSource` / `seoImageSource` are each one of `sameAsSeo` | `fromField` | `fromCustom`. With **`fromField` pointed at a field that's empty on an entry**, SEOMatic falls back to the global/homepage meta — so every entry with an empty SEO field gets the **same** description. Classic sitewide-duplicate-meta bug, and a real ranking problem.

Fix: set the source to **`fromCustom`** and put an object-template in `metaGlobalVars.seoTitle` / `seoDescription` with its **own fallback chain**, so an empty primary field cascades to a sensible per-entry value instead of the global:

```twig
{{ entry.seoDescription ?: entry.summary ?: entry.title }}
```

> The object-template variable is commonly `entry`, but **verify per install** — custom element types use their own `refHandle()` (e.g. `job`), not `entry`. Check before relying on it.

### Gotcha — Per-Page Schema Type vs Global Identity

Two different settings, easily confused:

- **`metaGlobalVars.mainEntityOfPage`** — a string (`WebPage`, `Article`, `NewsArticle`, …). The **per-page** schema type, consumed by `MetaContainers` to build the page's `mainEntityOfPage` JSON-LD. This is what you set to make a blog entry an `Article`.
- **`metaBundleSettings.siteType` / `siteSubType` / `siteSpecificType`** — the **global identity** schema (the `LocalBusiness` / `Organization` cascade for Site Settings → Identity). Not per-page.

Setting `siteType` when you meant `mainEntityOfPage` (or vice versa) is a common reason the rendered structured data isn't what you expect.

### Complex Per-Entry Structured Data — Prefer a Twig Partial

For rich, field-driven structured data — a real-estate `Product`/`Offer`/`Place`, an event, a recipe — don't fight SEOMatic's JSON-LD container. Build a Twig `<script type="application/ld+json">` partial: assemble a hash from real field values and `json_encode` it. It's more testable, version-controlled, and far easier to reason about than templating JSON through container settings:

```twig
{# _partials/schema/listing.twig #}
{% set schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: entry.title,
    description: entry.summary ?: entry.title,
    offers: {
        '@type': 'Offer',
        price: entry.price,
        priceCurrency: 'EUR',
        availability: 'https://schema.org/' ~ (entry.isAvailable ? 'InStock' : 'SoldOut'),
    },
} %}
<script type="application/ld+json">{{ schema|json_encode|raw }}</script>
```

Use SEOMatic for the meta-tag cascade (title/description/OG/Twitter) and the global identity JSON-LD; reach for a partial when per-entry structured data needs real field values.

### MetaBundles Service Methods

`Seomatic::$plugin->metaBundles` exposes the bundle plumbing if you'd rather go through the service than raw SQL:

| Method | Use |
|---|---|
| `updateMetaBundle($metaBundle, $siteId)` | Persist an in-memory bundle back to its row |
| `syncBundleWithConfig(...)` | Reconcile a bundle against its `seomatic-config` files |
| `invalidateMetaBundleById($sourceBundleType, $sourceId, $siteId)` | Invalidate one bundle's cache |
| `createContentMetaBundles()` | (Re)build per-section/content bundles |
| `createGlobalMetaBundles()` | (Re)build the global per-site bundles |

Cache reset after any bundle edit: `Seomatic::$plugin->clearAllCaches();`.

> Raw `JSON_SET` migrations are usually simpler and more predictable than reconstructing full bundle objects through the service — but the service methods are there when you need a full rebuild from config.

Verified against `nystudio107/craft-seomatic ^5.1.16`.

## Sitemaps

SEOMatic auto-generates XML sitemaps for all sections, category groups, and Commerce product types with public URLs. Configure per-section in Content SEO:

- **Sitemap Enabled** — include/exclude from sitemap
- **Change Frequency** — how often the content changes
- **Priority** — relative priority (0.0–1.0)
- **Image Sitemaps** — include images in sitemap entries

### Disable Sitemaps in Dev

```php
// config/seomatic.php
return [
    'dev' => [
        'sitemapsEnabled' => false,
    ],
];
```

## GraphQL API

```graphql
{
  seomatic(uri: "/", siteId: 1) {
    metaTitleContainer
    metaTagContainer
    metaLinkContainer
    metaScriptContainer
    metaJsonLdContainer
    metaSiteVarsContainer
  }
}
```

Pass `asArray: true` for structured data instead of rendered HTML strings.

## Events

```php
use nystudio107\seomatic\events\IncludeContainerEvent;
use nystudio107\seomatic\base\Container;
use yii\base\Event;

// Conditionally exclude a container
Event::on(Container::class, Container::EVENT_INCLUDE_CONTAINER,
    function(IncludeContainerEvent $event) {
        if ($event->container->handle === 'script') {
            $event->include = false;
        }
    }
);
```

## Multi-Site

All settings are multi-site aware. Content SEO, Global SEO, and sitemaps can be configured independently per site. The `seomatic-config` directory applies globally — use Content SEO in the CP for per-site overrides.

## Pair With

- **Retour** — redirect management and 404 tracking (SEOMatic does not handle redirects)
- **Typogrify** — smart typography for SEO title/description rendering