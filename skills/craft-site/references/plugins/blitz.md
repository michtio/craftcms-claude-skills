# Blitz

Full-page static caching by putyourlightson. Converts Craft pages into static HTML files, reducing TTFB from 600-900ms to ~25ms. Smart invalidation on content changes, CDN purging, cache warming, and dynamic content injection.

`putyourlightson/craft-blitz` — $99

## Documentation

- Overview: https://putyourlightson.com/plugins/blitz
- Configuration: https://putyourlightson.com/plugins/blitz#configuration
- Twig API: https://putyourlightson.com/plugins/blitz#template-tags
- Dynamic content: https://putyourlightson.com/plugins/blitz#dynamic-content
- Hints utility: https://putyourlightson.com/plugins/blitz#hints

When unsure about a Blitz feature, `WebFetch` the plugin page.

## Common Pitfalls

- Leaving Craft's native `{% cache %}` tags in Blitz-cached templates — full-page caching makes template caching redundant, and `{% cache %}` can interfere with Blitz invalidation. Remove `{% cache %}` from templates Blitz caches (see "Blitz vs `{% cache %}`" below).
- Caching pages with CSRF tokens — forms with CSRF tokens get frozen in the cache. Render the token dynamically with `craft.blitz.csrfInput()` (or use `craft.blitz.includeDynamic()` for the whole form partial).
- Including user-specific content in cached pages — anything that varies per user (cart counts, logged-in state, dashboards) must use `craft.blitz.includeDynamic()` / `craft.blitz.fetchUri()` or be loaded client-side.
- Caching pages behind authentication — `account/*`, admin areas, and any authenticated routes must be excluded via `excludedUriPatterns`.

## What to Exclude From the Cache

The URI/query-string patterns a site builder cares about live in `config/blitz.php`. Exclude anything personalized or non-HTML:

```php
// config/blitz.php (excerpt — front-end-relevant keys only)
'excludedUriPatterns' => [
    ['siteId' => '', 'uriPattern' => 'account/.*'],   // authenticated routes
    ['siteId' => '', 'uriPattern' => 'api/.*'],        // JSON endpoints
    ['siteId' => '', 'uriPattern' => 'actions/.*'],    // controller actions
],
'excludedQueryStringParams' => [
    ['siteId' => '', 'queryStringParam' => 'gclid'],
    ['siteId' => '', 'queryStringParam' => 'fbclid'],
    ['siteId' => '', 'queryStringParam' => 'utm_.*'],
],
```

With `cacheNonHtmlResponses` enabled, XML sitemaps and JSON API responses get cached too — exclude them. All settings support per-site config via `siteId` (empty string `''` matches all sites). See Blitz's [configuration docs](https://putyourlightson.com/plugins/blitz#configuration) for the full set, and "Refresh Modes" below for `refreshMode`.

## Refresh Modes

`refreshMode` (in `config/blitz.php`) controls what happens to a cached page when its content changes. The default is `3`. The integer values map to Blitz's `SettingsModel` constants:

| Mode | Value | Behavior | Best for |
|------|-------|----------|----------|
| Expire + manual | `0` | Marks pages stale; regenerated manually (cron) or organically on next visit | Full control / lower traffic |
| Clear + manual | `1` | Deletes cached files; regenerated manually (cron) or organically | Simple setups |
| Expire + queue | `2` | Marks stale, regenerates in a queue job. Serves stale content until done | **High-traffic sites** |
| Clear + queue | `3` | Deletes files, regenerates in a queue job (default) | Most sites |

Expire modes (`0`/`2`) keep serving stale pages until regeneration finishes — no cold-start stampede. Clear modes (`1`/`3`) drop the file immediately, so the next visitor hits PHP until it regenerates. The "manual" modes (`0`/`1`) rely on you refreshing via cron (see "Console Commands").

## Blitz vs `{% cache %}`

Full-page caching makes Craft's native `{% cache %}` tag redundant, and the two don't always cooperate on invalidation. In templates Blitz caches, remove `{% cache %}` tags (or disable template caching). Keep `{% cache %}` only for fragments on pages Blitz does *not* cache.

## Twig API

### Dynamic Content

For user-specific or real-time content within cached pages. `craft.blitz.includeDynamic()` returns a script that renders the template via an AJAX request on every page view, even when the parent page is served from cache:

```twig
{# Render a template dynamically (never cached) #}
{{ craft.blitz.includeDynamic('_includes/cart-count', {
    userId: currentUser.id ?? null,
}) }}

{# Fetch a URI's contents via AJAX after page render #}
{{ craft.blitz.fetchUri('/includes/user-menu') }}
```

### Cached Includes

`craft.blitz.includeCached()` caches a template separately and shares it across pages (server-side / edge-side include):

```twig
{{ craft.blitz.includeCached('_includes/global-nav') }}

{# With parameters #}
{{ craft.blitz.includeCached('_includes/sidebar', { section: 'news' }) }}
```

### Per-Page Cache Options

`craft.blitz.options()` controls caching for the current page. Pass an object, or chain the methods (`cachingEnabled`, `cacheDuration`, `expiryDate`, `tags`, `trackElements`, `trackElementQueries`, `paginate`):

```twig
{# Object notation — disable caching for this page #}
{% do craft.blitz.options({ cachingEnabled: false }) %}

{# Expire this page at a specific date #}
{% do craft.blitz.options({ expiryDate: now|date_modify('+1 hour') }) %}

{# Chained — custom tags for targeted invalidation #}
{% do craft.blitz.options.tags(['homepage', 'featured']) %}

{# Chained — combine duration and tags #}
{% do craft.blitz.options.cacheDuration('P1D').tags(['home', 'listing']) %}
```

### CSRF in Cached Forms

A cached page would freeze a stale CSRF token. Render the token dynamically so forms keep working — these helpers fetch a fresh value at request time:

```twig
<form method="post">
    {{ craft.blitz.csrfInput() }}   {# full hidden input #}
    {# or, when you need the parts: #}
    {# craft.blitz.csrfParam() / craft.blitz.csrfToken() #}
    ...
</form>
```

## Server / Infrastructure Config (brief)

Beyond templates, Blitz has a pluggable driver system configured in `config/blitz.php` — not something a site builder normally touches:

- **Storage** — where HTML is written (file system vs Yii cache / Redis).
- **Generator** — how the cache is (re)generated (HTTP crawler, queue concurrency).
- **Purger** — clears an upstream CDN / reverse proxy on refresh (Cloudflare, CloudFront, KeyCDN, via add-on packages such as `putyourlightson/craft-blitz-cloudflare`).
- **Deployer** — pushes cached pages to a static host (e.g. the Git deployer).
- **Web-server rewrite** — an Nginx/Apache rule that serves cached files directly, bypassing PHP. The single biggest performance win, but a deploy/infra concern.

Configure these per Blitz's official [configuration docs](https://putyourlightson.com/plugins/blitz#configuration). General Craft caching strategy lives in the `craftcms` skill's `caching.md`. Blitz is a plugin and runs on any host; on platforms that already ship full-page/edge caching (e.g. Craft Cloud, Servd) running Blitz on top is often redundant — check your host's built-in caching model before adding it.

Integrations that auto-refresh the cache when other plugins change content (e.g. `SeomaticIntegration`, `FeedMeIntegration`) are enabled via the `integrations` config key.

## Console Commands

Run via DDEV locally (`ddev craft …`) or `php craft …` on a server — the backbone of cron-driven cache maintenance:

```bash
php craft blitz/cache/refresh           # Clear, flush, purge, generate + deploy everything
php craft blitz/cache/refresh-expired   # Refresh only expired pages
php craft blitz/cache/refresh-urls      # Refresh pages matching given URLs
php craft blitz/cache/refresh-tagged    # Refresh pages with given tags (e.g. home,listing)
php craft blitz/cache/generate          # Queue a full cache generation
php craft blitz/cache/clear             # Delete all cached pages
php craft blitz/cache/flush             # Delete all cache database records
php craft blitz/cache/purge             # Purge the reverse proxy / CDN
php craft blitz/cache/deploy            # Queue a remote deploy of cached files
```

All commands accept `--queue=1` to force queuing instead of immediate execution.

### Server cron + queue setup

For the "manual" refresh modes (`0`/`1`) and for keeping the cache warm, schedule refreshes with cron:

```cron
# Refresh expired pages hourly, 5 past the hour
5 * * * * php /path/to/craft blitz/cache/refresh-expired

# Refresh specific tagged pages daily at 6am
0 6 * * * php /path/to/craft blitz/cache/refresh-tagged home,listing
```

The "queue" refresh modes (`2`/`3`) and `generate`/`deploy` push Craft queue jobs. On a content-heavy site, run the Craft queue with a **daemonised queue runner** (a systemd service or supervisor process running `php craft queue/listen`) instead of the default web-triggered runner — this avoids PHP timeouts and memory exhaustion during large refreshes. See Blitz's [configuration docs](https://putyourlightson.com/plugins/blitz#configuration).

## Performance Hints

Enable the Hints utility (`'hintsEnabled' => true`) to surface template performance issues. CP → Utilities → Blitz Hints shows eager-loading opportunities, N+1 queries, and other optimization suggestions for your templates.

## Pair With

- **SEOMatic** — enable the `SeomaticIntegration` so the cache auto-refreshes on SEO changes.
- **Feed Me** — enable the `FeedMeIntegration` so imports auto-refresh the cache.
- **Cache Igniter** (`putyourlightson/craft-cache-igniter`) — warms CDN edge caches from multiple regions after a refresh (infra / global-site concern).
