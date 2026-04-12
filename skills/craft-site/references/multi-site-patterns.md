# Multi-Site & Multi-Language Patterns

> Front-end Twig reference for multi-site and multi-language Craft CMS 5 development.

## Documentation

- Multi-site setup: https://craftcms.com/docs/5.x/system/sites.html
- Element queries: https://craftcms.com/docs/5.x/development/element-queries.html
- Static translations: https://craftcms.com/docs/5.x/system/sites.html#static-message-translations

## Table of Contents

- [Common Pitfalls](#common-pitfalls) | [Site Architecture](#site-architecture-patterns) | [Language Switchers](#language-switcher-patterns) | [Hreflang Tags](#hreflang-tags)
- [Cross-Site Queries](#cross-site-queries) | [Static Translations](#static-translations) | [Site-Specific Templates](#site-specific-templates)
- [Multi-Site Forms](#multi-site-forms) | [Site Detection](#site-detection)

## Common Pitfalls

- **N+1 on language switchers** — Querying `entry.localized` inside a loop fires a query per site. Use `.with(['localized'])` on the original query, or call `entry.localized.eagerly()` once and cache the result.
- **Missing `.site()` on cross-site queries** — Element queries default to the current site. Set `.site('*')` or `.site('de')` explicitly. Omitting this silently returns zero results for content on other sites.
- **Hardcoded language codes** — Use `currentSite.language` or `currentSite.language|slice(0,2)`, never string literals. Hardcoded values break when site languages change.
- **Stale CSRF tokens with static caching** — When using Blitz, the CSRF token baked into HTML is stale for subsequent visitors. Use `craft.blitz.csrfInput()` or JavaScript hydration.
- **Doubled subfolder in URIs** — If `baseUrl` includes the subfolder (e.g. `https://example.com/de/`), do not repeat it in the section URI format. `de/{slug}` + base URL `/de/` produces `/de/de/my-entry`.
- **Missing eager load for hreflang** — Generating `<link rel="alternate">` tags without eager loading fires one query per site on every page load.
- **Assuming entries exist on all sites** — Entries may be disabled or unpropagated. Always guard against null when iterating localized entries.

## Site Architecture Patterns

### Subfolder-per-language (most common)

```
Handle   Base URL                       Language
en       https://example.com/           en
de       https://example.com/de/        de
fr       https://example.com/fr/        fr
```

Pros: Single domain, single SSL, shared cookies, SEO consolidation. Cons: Primary language has no subfolder — mitigate with `x-default` hreflang.

### Domain-per-language

```
Handle   Base URL                       Language
en       https://example.com/           en
de       https://example.de/            de
fr       https://example.fr/            fr
```

Pros: Strong geo-targeting SEO signal, clean URLs. Cons: Multiple SSL certs, separate DNS, no shared cookies.

### Subdomain-per-language

```
Handle   Base URL                       Language
en       https://en.example.com/        en
de       https://de.example.com/        de
fr       https://fr.example.com/        fr
```

Pros: Single root domain, wildcard SSL possible. Cons: Search engines treat subdomains as separate sites, cookies need `domain=.example.com`.

### Multi-brand (site groups)

```
Group     Handle       Base URL                   Language
Brand A   brandA_en    https://brand-a.com/       en
Brand A   brandA_de    https://brand-a.com/de/    de
Brand B   brandB_en    https://brand-b.com/       en
Brand B   brandB_fr    https://brand-b.com/fr/    fr
```

Pros: Shared CMS, cross-brand content reuse. Cons: Complex permissions, template branching per brand. Use `currentSite.group.handle` to branch brand-specific logic. Use `craft.app.sites.getSitesByGroupId(currentSite.groupId)` to scope switchers to the current brand.

## Language Switcher Patterns

### Entry page switcher (eager loaded)

Use on entry pages where the current entry has localized versions.

```twig
{%- set localizedEntries = entry.localized.eagerly().all() -%}

<nav aria-label="{{ 'Language'|t }}">
    <ul>
        {%- for localizedEntry in localizedEntries -%}
            {%- set site = localizedEntry.site -%}
            <li>
                <a href="{{ localizedEntry.url }}"
                   lang="{{ site.language }}"
                   hreflang="{{ site.language }}"
                   {% if site.id == currentSite.id %}aria-current="page"{% endif %}
                >{{- site.name -}}</a>
            </li>
        {%- endfor -%}
    </ul>
</nav>
```

### Global switcher (non-entry pages)

Use on pages without an entry context (custom routes, search, error pages). Links to each site's homepage.

```twig
<nav aria-label="{{ 'Language'|t }}">
    <ul>
        {%- for site in craft.app.sites.allSites -%}
            {%- if site.enabled -%}
                <li>
                    <a href="{{ site.baseUrl }}"
                       lang="{{ site.language }}"
                       hreflang="{{ site.language }}"
                       {% if site.id == currentSite.id %}aria-current="page"{% endif %}
                    >{{- site.name -}}</a>
                </li>
            {%- endif -%}
        {%- endfor -%}
    </ul>
</nav>
```

### Fallback switcher (entry may not exist on all sites)

Guard against entries disabled or unpropagated on some sites. Fall back to site homepage.

```twig
{%- set localizedEntries = entry is defined and entry
    ? entry.localized.eagerly().all()|index('site.id')
    : []
-%}

<nav aria-label="{{ 'Language'|t }}">
    <ul>
        {%- for site in craft.app.sites.allSites -%}
            {%- if site.enabled -%}
                {%- set localizedEntry = localizedEntries[site.id] ?? null -%}
                {%- set url = localizedEntry ? localizedEntry.url : site.baseUrl -%}
                <li>
                    <a href="{{ url }}"
                       lang="{{ site.language }}"
                       hreflang="{{ site.language }}"
                       {% if site.id == currentSite.id %}aria-current="page"{% endif %}
                    >{{- site.name -}}</a>
                </li>
            {%- endif -%}
        {%- endfor -%}
    </ul>
</nav>
```

## Hreflang Tags

### Manual implementation

Place in `<head>`. Include `x-default` pointing to the primary site.

```twig
{# _boilerplate/_partials/hreflang.twig #}
{%- set localizedEntries = entry is defined and entry
    ? entry.localized.eagerly().all()
    : []
-%}

{%- if localizedEntries|length > 1 -%}
    {%- for localizedEntry in localizedEntries -%}
        <link rel="alternate" hreflang="{{ localizedEntry.site.language }}" href="{{ localizedEntry.url }}">
    {%- endfor -%}
    {%- set primarySite = craft.app.sites.primarySite -%}
    {%- set defaultEntry = localizedEntries|filter(e => e.site.id == primarySite.id)|first -%}
    {%- if defaultEntry -%}
        <link rel="alternate" hreflang="x-default" href="{{ defaultEntry.url }}">
    {%- endif -%}
{%- endif -%}

{%- if not localizedEntries|length -%}
    {%- for site in craft.app.sites.allSites if site.enabled -%}
        <link rel="alternate" hreflang="{{ site.language }}" href="{{ site.baseUrl }}">
    {%- endfor -%}
    <link rel="alternate" hreflang="x-default" href="{{ craft.app.sites.primarySite.baseUrl }}">
{%- endif -%}
```

Include from the layout:

```twig
{%- block head -%}
    {%- include '_boilerplate/_partials/hreflang' with { entry: entry ?? null } only -%}
{%- endblock -%}
```

### SEOmatic

SEOmatic generates hreflang tags automatically when multi-site is configured. Remove any manual hreflang partial to avoid duplicates. Verify output with View Source.

## Cross-Site Queries

### Query all sites

```twig
{%- set allEntries = craft.entries.section('news').site('*').all() -%}
```

### Query a specific site

```twig
{%- set deEntries = craft.entries.section('news').site('de').all() -%}
```

### Deduplicate across sites

Use `.unique()` with `.preferSites()` to get one entry per element, preferring a specific site.

```twig
{%- set entries = craft.entries
    .section('news')
    .site('*')
    .unique()
    .preferSites([currentSite.handle, craft.app.sites.primarySite.handle])
    .all()
-%}
```

### Query by language

When multiple sites share a language (e.g. `en-US` and `en-GB`), query by language instead of handle.

```twig
{%- set englishEntries = craft.entries.section('news').site('*').language('en').all() -%}
```

### Eager load localized entries

Prevent N+1 queries on listing pages that show language switchers or hreflang per entry.

```twig
{%- set entries = craft.entries.section('news').with(['localized']).all() -%}

{%- for entry in entries -%}
    {%- for localizedEntry in entry.localized -%}
        {{ localizedEntry.url }}
    {%- endfor -%}
{%- endfor -%}
```

### Access a specific site's version

```twig
{%- set frenchEntry = entry.localized.site('fr').one() -%}
```

## Static Translations

### File structure

```
translations/
├── en/
│   └── site.php
├── de/
│   └── site.php
└── fr/
    └── site.php
```

### Translation file format (`translations/de/site.php`)

```php
<?php
return [
    'Read more' => 'Weiterlesen',
    'Search' => 'Suche',
    'No results found' => 'Keine Ergebnisse gefunden',
    'Welcome, {name}' => 'Willkommen, {name}',
    '{count, plural, =1{# result} other{# results}}' => '{count, plural, =1{# Ergebnis} other{# Ergebnisse}}',
];
```

### Usage in Twig

```twig
{# Basic — uses 'site' category by default #}
{{ 'Read more'|t }}

{# With parameters #}
{{ 'Welcome, {name}'|t({ name: currentUser.friendlyName }) }}

{# ICU pluralization #}
{{ '{count, plural, =1{# result} other{# results}}'|t({ count: totalResults }) }}

{# Explicit category for plugin or app strings #}
{{ 'Entries'|t('app') }}
{{ 'Submit'|t('formie') }}
```

### Translation categories

| Category | File | Use for |
|----------|------|---------|
| `site` | `site.php` | Custom site strings (default when no category specified) |
| `app` | `app.php` | Craft core string overrides |
| `{pluginHandle}` | `{pluginHandle}.php` | Plugin string overrides |

## Site-Specific Templates

Craft resolves templates with site-handle subdirectories taking priority over `templates/`.

For a request to the `de` site rendering `_views/view--page`:

1. `templates/de/_views/view--page.twig` (site-specific, checked first)
2. `templates/_views/view--page.twig` (base fallback)

```
templates/
├── _views/
│   └── view--page-landing.twig      ← Default for all sites
├── de/
│   └── _views/
│       └── view--page-landing.twig  ← German override
└── fr/
    └── _organisms/
        └── footers/
            └── footer--primary.twig ← French footer override
```

Use for site-specific navigation, brand-specific layouts, or region-specific legal content. Keep overrides minimal — prefer content-driven differences over template-driven differences.

## Multi-Site Forms

### CSRF tokens

CSRF tokens are session-bound and work across all sites in the same installation.

```twig
<form method="post">
    {{ csrfInput() }}
    {{ actionInput('entries/save-entry') }}
</form>
```

### Static caching

When using Blitz or another full-page cache, use Blitz's dynamic tag or JavaScript hydration:

```twig
{# Blitz dynamic CSRF #}
{{ craft.blitz.csrfInput() }}

{# Manual: fetch fresh token via JS #}
<form method="post" id="my-form">
    {{ actionInput('entries/save-entry') }}
</form>
<script>
fetch('/actions/users/session-info', { headers: { 'Accept': 'application/json' } })
    .then(r => r.json())
    .then(data => {
        const input = document.createElement('input');
        Object.assign(input, { type: 'hidden', name: data.csrfTokenName, value: data.csrfTokenValue });
        document.getElementById('my-form').prepend(input);
    });
</script>
```

### Cross-site form submissions

Include the target site ID to save content to a specific site.

```twig
{%- set targetSite = craft.app.sites.getSiteByHandle('en') -%}
<form method="post">
    {{ csrfInput() }}
    {{ actionInput('entries/save-entry') }}
    {{ hiddenInput('siteId', targetSite.id) }}
</form>
```

## Site Detection

Craft scores each site against the incoming request URL:

1. **Host matching** — Sites whose `baseUrl` host matches the request host score higher.
2. **Path length** — Among host matches, the site with the longest matching `baseUrl` path prefix wins. This differentiates subfolder-based sites.
3. **Primary site fallback** — If nothing matches, the primary site is used.

### Overriding detection

For headless, API, or CLI contexts: set `CRAFT_SITE=de` in `.env` or send the `X-Craft-Site: de` HTTP header.

### currentSite in Twig

```twig
{{ currentSite.handle }}    {# 'de' #}
{{ currentSite.language }}  {# 'de' #}
{{ currentSite.name }}      {# 'Deutsch' #}
{{ currentSite.baseUrl }}   {# 'https://example.com/de/' #}
{{ currentSite.groupId }}   {# 1 #}
```
