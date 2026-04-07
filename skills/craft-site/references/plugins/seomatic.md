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

When unsure about an SEOMatic feature, `web_fetch` the relevant docs page.

## Common Pitfalls

- Putting SEOMatic Twig variables inside `{% cache %}` tags — SEOMatic dynamically generates meta on each request using its own cache. Wrapping in `{% cache %}` freezes the output after the first render.
- Using `entry` as the variable name in custom element config files — custom element types use their own `refHandle()` (e.g., `job` for a Job element, not `entry`). Check the element class's `refHandle()` method.
- Setting SEO values in Twig that are already mapped in Content SEO — Content SEO mappings (`{seoField}` → entry fields) take precedence unless you override in Twig with `{% do seomatic.meta.seoTitle("...") %}`.
- Forgetting that `seomatic-config` files only apply on initial bundle creation — changes after the bundle exists have no effect unless you bump `bundleVersion` in `Bundle.php`.
- Not configuring Content SEO per-section — SEOMatic's power is in automatic field mapping. If you rely only on the SEO Settings field, you're doing extra work.
- Missing `{% hook 'seomaticRender' %}` when headless — auto-rendering works for traditional templates. Headless/hybrid setups need explicit rendering or the GraphQL API.
- Hardcoding JSON-LD in templates instead of using SEOMatic's container system — breaks the cascade and loses CP configurability.

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