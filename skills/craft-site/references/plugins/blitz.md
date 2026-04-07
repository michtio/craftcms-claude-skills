# Blitz

Full-page static caching by putyourlightson. Converts Craft pages into static HTML files, reducing TTFB from 600-900ms to ~25ms. Smart invalidation on content changes, CDN purging, cache warming, and dynamic content injection.

`putyourlightson/craft-blitz` — $99

## Documentation

- Overview: https://putyourlightson.com/plugins/blitz
- Configuration: https://putyourlightson.com/plugins/blitz#configuration
- Twig API: https://putyourlightson.com/plugins/blitz#template-tags
- Dynamic content: https://putyourlightson.com/plugins/blitz#dynamic-content
- Hints utility: https://putyourlightson.com/plugins/blitz#hints

When unsure about a Blitz feature, `web_fetch` the plugin page.

## Common Pitfalls

- Caching pages with CSRF tokens — forms with CSRF tokens get frozen in the cache. Use `{% dynamicInclude %}` for form partials or Blitz's CSRF injection (`injectScriptEvent`).
- Including user-specific content in cached pages — anything that varies per user (cart counts, logged-in state, dashboards) must use `{% dynamicInclude %}` or be loaded client-side.
- Not excluding API endpoints and sitemaps — with `cacheNonHtmlResponses` enabled, XML sitemaps and JSON API responses get cached too. Add them to `excludedUriPatterns`.
- Setting `refreshMode` to clear+regenerate on high-traffic sites — clearing the entire cache causes a cold-start stampede. Use expire+regenerate (mode `2`) instead, which serves stale content while regenerating in the background.
- Forgetting the Nginx/Apache rewrite rule — without it, every request still hits PHP to serve the cached file. The rewrite serves static files directly, bypassing PHP entirely.
- Not warming the cache after deployment — first visitors hit cold cache. Use the cache warming utility or Cache Igniter.
- Caching pages behind authentication — `account/*`, admin areas, and any authenticated routes must be excluded.

## Config File

```php
// config/blitz.php
use craft\helpers\App;

return [
    '*' => [
        'cachingEnabled' => (bool)App::env('ENABLE_TEMPLATE_CACHING'),
        'refreshMode' => 3,  // Clear + regenerate in queue
        'sendPoweredByHeader' => false,
        'debug' => false,

        'includedUriPatterns' => [
            ['siteId' => '', 'uriPattern' => '.*'],
        ],

        'excludedUriPatterns' => [
            ['siteId' => '', 'uriPattern' => 'account/.*'],
            ['siteId' => '', 'uriPattern' => 'api/.*'],
            ['siteId' => '', 'uriPattern' => 'actions/.*'],
        ],

        'excludedQueryStringParams' => [
            ['siteId' => '', 'queryStringParam' => 'gclid'],
            ['siteId' => '', 'queryStringParam' => 'fbclid'],
            ['siteId' => '', 'queryStringParam' => 'utm_.*'],
        ],

        'queryStringCaching' => 0,  // Don't cache URLs with query strings
    ],
    'production' => [
        'debug' => false,
    ],
    'dev' => [
        'cachingEnabled' => false,
        'debug' => true,
    ],
];
```

## Refresh Modes

| Mode | Value | Behavior | Best for |
|------|-------|----------|----------|
| Expire + manual | `0` | Marks pages stale, waits for manual/organic regeneration | Full control |
| Clear + manual | `1` | Deletes cached files, waits for next visitor | Simple setups |
| Expire + queue | `2` | Marks stale, regenerates in background. Serves stale until done | **High-traffic sites** |
| Clear + queue | `3` | Deletes files, regenerates in background queue job | Most common |

Mode `2` is best for production — visitors never see uncached responses because stale pages are served while regeneration runs in the background.

## Twig API

### Dynamic Content

For user-specific or real-time content within cached pages:

```twig
{# Include a template dynamically (never cached) #}
{% dynamicInclude '_includes/cart-count' with {
    userId: currentUser.id ?? null
} %}
```

The included template is rendered on every request, even when the parent page is served from cache.

### Cache Inclusion Tags

```twig
{# Include a cached template (cached separately, shared across pages) #}
{{ craft.blitz.includeCached('_includes/global-nav') }}

{# Include with parameters #}
{{ craft.blitz.includeCached('_includes/sidebar', { section: 'news' }) }}

{# Dynamic fetch (AJAX-loaded after page render) #}
{{ craft.blitz.fetchUri('/includes/user-menu') }}
```

### Cache Control

```twig
{# Prevent this page from being cached #}
{% do craft.blitz.options.noCache() %}

{# Set cache expiry for this specific page #}
{% do craft.blitz.options.expiryDate(now|date_modify('+1 hour')) %}

{# Add custom tags for targeted invalidation #}
{% do craft.blitz.options.tags(['homepage', 'featured']) %}
```

### CSRF Token Injection

Blitz can automatically inject fresh CSRF tokens into cached pages via JavaScript:

```php
// config/blitz.php
'injectScriptEvent' => 'DOMContentLoaded',
```

This replaces frozen CSRF tokens in forms with fresh ones after the page loads client-side.

## Driver Architecture

Blitz uses a pluggable driver system for storage, generation, purging, and deployment.

### Storage Drivers

| Driver | Package | Description |
|--------|---------|-------------|
| File Storage | Built-in | Writes HTML to `@webroot/cache/blitz/` |
| Yii Cache | Built-in | Stores in Craft's cache (Redis, Memcached) |

```php
'cacheStorageType' => 'putyourlightson\blitz\drivers\storage\FileStorage',
'cacheStorageSettings' => [
    'folderPath' => '@webroot/cache/blitz',
    'createGzipFiles' => true,
    'countCachedFiles' => true,
],
```

### Generator Drivers

```php
'cacheGeneratorType' => 'putyourlightson\blitz\drivers\generators\HttpGenerator',
'cacheGeneratorSettings' => ['concurrency' => 3],
```

### Purger Drivers

| Driver | Package | Description |
|--------|---------|-------------|
| Cloudflare | `putyourlightson/craft-blitz-cloudflare` | Purges Cloudflare cache on refresh |
| CloudFront | `putyourlightson/craft-blitz-cloudfront` | Purges AWS CloudFront |
| KeyCDN | Community | Purges KeyCDN cache |

```php
'cachePurgerType' => 'putyourlightson\blitzcloudflare\CloudflarePurger',
'cachePurgerSettings' => [
    'authenticationMethod' => 'apiToken',
    'apiToken' => App::env('CLOUDFLARE_API_TOKEN'),
    'zoneIds' => [
        'site-uid-here' => [
            'zoneId' => App::env('CLOUDFLARE_ZONE_ID'),
        ],
    ],
],
```

### Deployer Drivers

Blitz can deploy cached pages to static hosts:

```php
'deployerType' => 'putyourlightson\blitz\drivers\deployers\GitDeployer',
'deployerSettings' => [
    'gitRepositories' => [
        'site-uid-here' => [
            'repositoryPath' => '@root/path/to/repo',
            'branch' => 'main',
            'remote' => 'origin',
        ],
    ],
    'commitMessage' => 'Blitz auto deploy',
],
```

## Nginx Rewrite

Serve cached files directly without hitting PHP:

```nginx
location / {
    try_files /cache/blitz/$http_host/$uri/$args/index.html
              /cache/blitz/$http_host/$uri/index.html
              $uri $uri/ /index.php?$query_string;
}
```

This is the single biggest performance win — PHP is completely bypassed for cached pages.

## Cache Warming

### Built-in Utility

CP → Utilities → Blitz Cache → Generate Cache. Crawls all included URIs and pre-generates the cache.

### Console Commands

```bash
ddev craft blitz/cache/refresh        # Refresh (invalidate + regenerate)
ddev craft blitz/cache/refresh-all    # Refresh all sites
ddev craft blitz/cache/clear          # Clear cache
ddev craft blitz/cache/generate       # Generate all cached pages
ddev craft blitz/cache/generate-all   # Generate for all sites
```

### With Cache Igniter

Cache Igniter (`putyourlightson/craft-cache-igniter`, $99) warms CDN edge caches from multiple geographic locations after Blitz refreshes. Essential for global sites where the CDN cache is cold after a Blitz refresh.

## Performance Hints

Enable the Hints utility to identify template performance issues:

```php
'hintsEnabled' => true,
```

CP → Utilities → Blitz Hints shows eager loading opportunities, N+1 queries, and other optimization suggestions for your templates.

## Integrations

Blitz has built-in integrations that auto-refresh cache when specific plugins update content:

```php
'integrations' => [
    'putyourlightson\blitz\drivers\integrations\FeedMeIntegration',
    'putyourlightson\blitz\drivers\integrations\SeomaticIntegration',
],
```

## Multi-Site

All Blitz settings support per-site configuration via `siteId` in URI patterns. Set `siteId` to an empty string (`''`) to match all sites. Cache is stored per-site per-host automatically.

## Blitz + Cloudflare Setup

1. Proxy your domain through Cloudflare (orange cloud)
2. Install `putyourlightson/craft-blitz-cloudflare`
3. Create a Cloudflare API token with Zone.Cache Purge permissions
4. Configure the purger in `config/blitz.php`
5. Create a Cloudflare Cache Rule: match all requests → "Eligible for cache", edge TTL from origin headers
6. Blitz auto-purges Cloudflare cache when content changes

## Pair With

- **Cache Igniter** — edge cache warming from multiple geographic locations
- **SEOMatic** — enable the SeomaticIntegration for auto-refresh on SEO changes
- **Feed Me** — enable FeedMeIntegration for auto-refresh on feed imports
