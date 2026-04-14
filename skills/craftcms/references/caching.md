# Caching Reference

Complete reference for all caching strategies in Craft CMS 5 -- template caching, data caching, static caching, and the decision framework for choosing between them. For cache backend configuration (Redis, Memcached, etc.), see `config-app.md`. For `enableTemplateCaching` and other general settings, see `config-general.md`.

## Documentation

- Template caching (`{% cache %}` tag): https://craftcms.com/docs/5.x/reference/twig/tags.html#cache
- Data caching (development guide): https://craftcms.com/docs/5.x/development/caching.html
- Yii2 caching guide: https://www.yiiframework.com/doc/guide/2.0/en/caching-overview
- `craft\services\TemplateCaches`: https://docs.craftcms.com/api/v5/craft-services-templatecaches.html

## Common Pitfalls

- Wrapping dynamic or user-specific content in `{% cache %}` -- serves stale or wrong content to other users. CSRF tokens, cart counts, login state, and personalized greetings must never be inside a cache block.
- Using `{% cache %}` around variable assignments needed outside the block -- cached variables do not leak out. A `{% set x %}` inside a cache block is invisible to code after `{% endcache %}`.
- Caching everything instead of targeting expensive queries -- adds key lookup and storage overhead for operations that are already cheap. Only cache blocks that contain slow element queries or external API calls.
- Not setting `enableTemplateCaching => false` in dev -- debugging cached output is confusing because changes to templates do not appear until cache expires or is cleared.
- Forgetting `asyncCsrfInputs` when using full-page static caching (Blitz) -- CSRF tokens get frozen into cached HTML, causing form submissions to fail for all users except the one who warmed the cache.
- Skipping cache warming after deploy -- first visitors hit a cold cache and experience slow page loads. Use Blitz Cache Warmer or a custom queue job to pre-warm critical pages.
- Not understanding invalidation boundaries -- Craft auto-invalidates template caches when elements referenced inside the block change, but custom data caches (`Craft::$app->getCache()`) need manual invalidation via `TagDependency` or explicit `delete()` calls.
- Using the same Redis `database` index for cache and session -- flushing cache kills all active sessions. See `config-app.md` for the correct separation.
- Prefixing data cache keys inconsistently -- without a plugin-handle prefix, keys from different plugins or modules can collide silently.

## Contents

- [Caching Decision Guide](#caching-decision-guide)
- [Template Caching (`{% cache %}`)](#template-caching-cache)
- [Data Caching (PHP)](#data-caching-php)
- [Static Caching (Blitz)](#static-caching-blitz)
- [Edge Caching / CDN](#edge-caching--cdn)
- [Layered Caching Strategy](#layered-caching-strategy)
- [Cache Invalidation Patterns](#cache-invalidation-patterns)
- [Development and Debugging](#development-and-debugging)

## Caching Decision Guide

Not every site needs every caching layer. Start with the simplest solution that solves the actual performance problem, and add layers only when profiling shows they are needed.

### When to use what

| Scenario | Solution | Why |
|----------|----------|-----|
| Expensive element queries in templates | `{% cache %}` tag | Craft tracks element dependencies and auto-invalidates |
| External API data with TTL | Data cache (`Craft::$app->getCache()`) | No element dependency tracking needed, just time-based expiry |
| Full pages that rarely change (marketing, docs) | Static caching (Blitz) | Eliminates PHP entirely, TTFB drops from ~700ms to ~25ms |
| Dynamic pages with expensive fragments | `{% cache %}` on the fragment only | Cache the slow part, render the dynamic parts fresh |
| User-specific content mixed with public content | Static cache + `{% dynamicInclude %}` or client-side JS | Cache the shell, load personalized bits asynchronously |
| CDN edge caching | Blitz + Cloudflare/Fastly purger | Blitz manages purge requests when content changes |
| Computed values or aggregations in PHP | Data cache with `TagDependency` | Cache the result, invalidate when source data changes |
| Search results, filtered listings | Do not cache (or very short TTL) | URL params and user input create unbounded cache key space |

### Traffic-based guidance

| Monthly Visits | Recommended Layers |
|----------------|-------------------|
| < 1,000 | None, or `{% cache %}` on the slowest queries |
| 1,000 - 50,000 | `{% cache %}` fragments for expensive queries |
| 50,000 - 500,000 | `{% cache %}` + Redis cache backend + consider Blitz |
| 500,000+ | Blitz + CDN + Redis + fragment caching where needed |

## Template Caching (`{% cache %}`)

Craft's `{% cache %}` tag caches the rendered HTML output of a template block. It automatically tracks which element queries run inside the block and invalidates the cache when those elements are saved, deleted, or have their status changed.

### Basic usage

```twig
{% cache %}
    {% set entries = craft.entries.section('blog').limit(10).all() %}
    {% for entry in entries %}
        <article>
            <h2>{{ entry.title }}</h2>
            <p>{{ entry.postDate|date('M j, Y') }}</p>
        </article>
    {% endfor %}
{% endcache %}
```

On the first request, the block renders normally and Craft stores the HTML output. Subsequent requests serve the cached HTML without executing the element queries.

### All options

| Option | Example | Effect |
|--------|---------|--------|
| `globally` | `{% cache globally %}` | Share cache across all URLs. Default is per-URL. |
| `using key "x"` | `{% cache using key "sidebar" %}` | Custom cache key. Changing the key forces a fresh render. |
| `for` | `{% cache for "1 hour" %}` | Explicit TTL. Accepts: sec, min, hour, day, week, month, year. |
| `until` | `{% cache until entry.eventDate %}` | Expire at a specific DateTime object. |
| `if` | `{% cache if not currentUser %}` | Only cache when the condition is true. |
| `unless` | `{% cache unless currentUser %}` | Cache unless the condition is true. Same as `if not`. |
| `tag('x')` | `{% cache tag('nav') %}` | Tag for manual invalidation via CLI or API. |

### Combining options

Options can be chained in any order after `{% cache %}`:

```twig
{% cache globally using key "footer-nav" for "6 hours" tag('navigation') %}
    {% set navEntries = craft.entries.section('pages').level(1).all() %}
    <nav>
        {% for entry in navEntries %}
            <a href="{{ entry.url }}">{{ entry.title }}</a>
        {% endfor %}
    </nav>
{% endcache %}
```

### Dynamic cache keys

Use variables in the key to create per-context caches:

```twig
{# Per-category cache #}
{% cache using key "blog-list-#{category.id}" %}
    {% set entries = craft.entries.section('blog').relatedTo(category).all() %}
    {# ... #}
{% endcache %}

{# Per-page cache for paginated content #}
{% cache using key "blog-page-#{craft.app.request.pageNum}" %}
    {% set entries = craft.entries.section('blog').limit(10).all() %}
    {# ... #}
{% endcache %}
```

### Invalidation

**Automatic (element-based):** Craft tracks which element queries execute inside a `{% cache %}` block. When any of those elements are created, saved, deleted, or have their status changed, Craft invalidates the relevant cache entries. This is the primary invalidation mechanism and works without any configuration.

**Manual via CLI:**

```bash
# Invalidate all template caches
ddev craft invalidate-tags/template

# Invalidate all caches (template + data)
ddev craft invalidate-tags/all

# Invalidate by tag
ddev craft invalidate-tags --tag=navigation
```

**Manual via CP:** Utilities > Clear Caches > Template caches.

**Manual via PHP (in plugins/modules):**

```php
use craft\services\TemplateCaches;

// Invalidate all template caches
Craft::$app->getTemplateCaches()->invalidateAllCaches();

// Invalidate by element (Craft does this automatically on save, but useful for custom triggers)
Craft::$app->getTemplateCaches()->invalidateCachesByElementId($elementId);
```

### When NOT to cache

- **Static text with no queries** -- the cache lookup overhead exceeds the render cost of plain HTML.
- **Variable assignments needed outside the block** -- `{% set %}` inside `{% cache %}` does not propagate to the outer scope after the block is served from cache.
- **Per-request dynamic content** -- CSRF tokens, nonces, timestamps, `now` references, logged-in user info.
- **Randomized content** -- `shuffle` filters, random entry queries. The first render is frozen.
- **Content that varies by URL params you did not account for** -- the default cache key includes the full URL, but if you use `globally` or a custom `key`, param-based variation is lost.

### Performance notes

- Template caches are stored in the configured cache backend (database by default, Redis if configured in `app.php`).
- Each `{% cache %}` block adds one cache read on hit, or one cache write on miss. Keep blocks coarse-grained -- one block wrapping 5 queries is better than 5 blocks wrapping 1 query each.
- Nested `{% cache %}` blocks work but add complexity. The inner block caches independently from the outer block. Usually unnecessary.

## Data Caching (PHP)

For plugin and module code that needs to cache computed values, API responses, or other non-element data. Uses the Yii2 cache component configured in `config/app.php` (see `config-app.md`).

### Basic operations

```php
$cache = Craft::$app->getCache();

// Set with TTL (seconds)
$cache->set('my-plugin.api-data', $data, 3600);

// Get (returns false on miss)
$data = $cache->get('my-plugin.api-data');

// Get or set (cache-aside pattern -- preferred)
$data = $cache->getOrSet('my-plugin.api-data', function() {
    return $this->fetchFromApi();
}, 3600);

// Delete a specific key
$cache->delete('my-plugin.api-data');

// Check existence without retrieving
$exists = $cache->exists('my-plugin.api-data');

// Set with no expiry (lives until manually deleted or cache flushed)
$cache->set('my-plugin.static-config', $config, 0);
```

### Tag-based invalidation

Use `TagDependency` to group related cache entries and invalidate them together:

```php
use yii\caching\TagDependency;

$cache = Craft::$app->getCache();

// Set with tag dependency
$cache->set(
    'my-plugin.product-stats',
    $stats,
    3600,
    new TagDependency(['tags' => ['my-plugin', 'my-plugin.products']])
);

// Multiple tags for fine-grained invalidation
$cache->set(
    'my-plugin.category-5-products',
    $products,
    3600,
    new TagDependency(['tags' => ['my-plugin', 'my-plugin.category.5']])
);

// Invalidate everything tagged with 'my-plugin'
TagDependency::invalidate($cache, 'my-plugin');

// Invalidate only category 5 caches
TagDependency::invalidate($cache, 'my-plugin.category.5');
```

### Cache-aside with dependencies

```php
use yii\caching\TagDependency;

$cache = Craft::$app->getCache();

$data = $cache->getOrSet(
    'my-plugin.expensive-computation',
    function() {
        return $this->computeExpensiveData();
    },
    3600,
    new TagDependency(['tags' => ['my-plugin']])
);
```

### Key naming conventions

Always prefix cache keys with the plugin handle to avoid collisions:

```
my-plugin.api-data              -- good
my-plugin.category.5.products   -- good, hierarchical
api-data                        -- bad, will collide with other plugins
```

`CRAFT_APP_ID` prevents cross-install collisions at the backend level, but key prefixing prevents cross-plugin collisions within the same install.

### What can be cached

Any serializable PHP value: strings, numbers, arrays, objects implementing `Serializable` or with public properties. Element objects can be cached but this is usually a bad idea -- they are large and may hold stale references. Cache the computed result, not the element.

```php
// Good -- cache the computed value
$cache->set('my-plugin.entry-count', $count, 3600);

// Bad -- caching a full element object
$cache->set('my-plugin.featured-entry', $entry, 3600); // Large, stale references
```

## Static Caching (Blitz)

Blitz (by PutYourLightsOn) converts Craft pages into static HTML files served directly by the web server, bypassing PHP entirely. This is the most impactful caching layer for content-heavy sites.

### What Blitz does

On first request (or during cache warming), Blitz renders the page through Craft normally, then saves the output as a static HTML file. Subsequent requests are served by Nginx/Apache directly -- PHP never runs. When content changes in Craft, Blitz intelligently invalidates and regenerates only the affected pages.

**Performance impact:** TTFB drops from 600-900ms (typical PHP render) to ~25ms (static file).

### When to use Blitz

- Marketing sites, documentation, blogs -- pages that change only when content is published
- High-traffic sites where PHP render time is the bottleneck (> 50k monthly visits)
- Sites already behind a CDN where Blitz can manage purge requests
- Any site where the majority of pages are the same for all visitors

### When NOT to use Blitz

- Highly dynamic pages (search results, filtered listings with unbounded URL params)
- Pages where every visitor sees different content and there is no shared shell
- Sites with < 1,000 monthly visits -- the configuration complexity is not justified
- During active development -- Blitz adds a layer of indirection that complicates debugging

### Key architecture decisions

**CSRF handling:** `asyncCsrfInputs` MUST be set to `true` in `config/general.php` when using Blitz. Without it, CSRF tokens are baked into the cached HTML, and form submissions fail for every visitor except the one who originally warmed the cache.

```php
// config/general.php
return [
    '*' => [
        'asyncCsrfInputs' => true,
    ],
];
```

**Forms:** Even with `asyncCsrfInputs`, forms inside Blitz-cached pages need careful handling. Use `{% dynamicInclude %}` for form blocks, or use Sprig components that fetch fresh tokens on load.

**User-specific content:** Cart counts, login/logout state, personalized greetings, and other per-user content must be loaded client-side via JavaScript or through `{% dynamicInclude %}` blocks that are excluded from the static cache.

**Refresh modes:**

| Mode | Behavior | Best For |
|------|----------|----------|
| 1 -- Expire only | Marks pages as expired but does not regenerate | Low-traffic sites where occasional cold hits are acceptable |
| 2 -- Expire and regenerate | Marks expired, then regenerates in background | High-traffic sites -- serves stale content while regenerating |
| 3 -- Clear and regenerate | Deletes cached file, then regenerates | When stale content must never be served (e.g., pricing pages) |

Mode 2 is the safest default for production high-traffic sites -- visitors always get a response (stale-while-revalidate pattern), and regeneration happens asynchronously.

### Blitz + CDN architecture

```
User --> CDN (Cloudflare/Fastly) --> Blitz static HTML --> (miss) --> Nginx --> PHP --> Craft
```

Blitz ships with purger drivers for Cloudflare, Fastly, and custom endpoints. When content changes in Craft, Blitz sends purge requests to the CDN so edge caches are cleared alongside the local static files. Cache Warmer (built into Blitz) pre-warms pages after purge to avoid cold hits.

### Blitz configuration

Blitz is configured in the CP under Settings > Blitz: included/excluded URI patterns, query string handling, refresh mode, cache purger (Cloudflare/Fastly/custom), and cache warmer URLs. Full Blitz documentation: https://putyourlightson.com/plugins/blitz

## Edge Caching / CDN

CDN caching sits in front of the entire application and serves responses from edge nodes closest to the visitor.

### With Blitz

Blitz manages the CDN integration end-to-end:

- **Cloudflare:** Blitz Cloudflare Purger sends zone-level or URL-level purge requests when content changes.
- **Fastly:** Blitz Fastly Purger uses surrogate keys (cache tags) for fine-grained purge by content type.
- **Custom:** Blitz supports custom purger classes for other CDNs.

### Without Blitz

If Blitz is not in use, manage CDN caching manually via `Cache-Control` headers:

```twig
{# Set cache headers for a specific response #}
{% header "Cache-Control: public, max-age=3600, s-maxage=86400" %}
```

You must manage CDN purge requests manually -- via API calls in a Craft module, queue jobs triggered on element save events, or external CI/CD pipelines. This is significantly more work than using Blitz's built-in purger.

### Static assets

Cache static assets aggressively regardless of page caching strategy. Use Vite's content-hashed filenames (see `plugin-vite.md`) to enable immutable caching -- the filename changes when content changes, so cache busting is automatic.

## Layered Caching Strategy

A production site may use multiple caching layers simultaneously. Each layer operates at a different level of the request lifecycle.

### The five layers

| Layer | Technology | What it caches | Invalidation |
|-------|-----------|----------------|--------------|
| 1. CDN | Cloudflare, Fastly | Full responses at edge nodes | Purge API (manual or via Blitz) |
| 2. Static | Blitz | Full HTML pages as files on disk | Automatic on element save (Blitz) |
| 3. Fragment | `{% cache %}` | Rendered HTML of template blocks | Automatic on element save (Craft) |
| 4. Data | `Craft::$app->getCache()` | API responses, computed values | Manual (`delete()` or `TagDependency`) |
| 5. Query | Craft internals | Element query results | Automatic (Craft manages internally) |

### Which layers to use

Not every site needs all five layers. Choose based on traffic and performance requirements:

**Low-traffic site (< 1,000 monthly visits):**
- Layer 3 (fragment) on the slowest template blocks, if any
- Layer 5 is always active (Craft's internal query cache)

**Medium-traffic site (1,000 - 50,000 monthly visits):**
- Layer 3 (fragment) for expensive queries
- Layer 4 (data) for external API calls in modules/plugins
- Redis cache backend for better performance than database

**High-traffic marketing site (50,000+ monthly visits):**
- All five layers
- Blitz + Cloudflare for full-page caching
- Fragment caching as fallback for non-Blitz pages (search, filtered listings)
- Redis for the cache backend

**Headless / API site:**
- Layer 4 (data) for expensive computations
- CDN with short TTL on API responses
- Template caching is irrelevant (no Twig rendering)

## Cache Invalidation Patterns

### Template cache invalidation (automatic)

Craft tracks element queries inside `{% cache %}` blocks. When an element that was queried is:

- Created
- Saved (content or status change)
- Deleted
- Moved (structure sections)
- Has its expiry date pass

All template cache entries that referenced that element are invalidated. This happens automatically -- no configuration needed.

**Limitation:** If the cache block uses a query that would now return *new* elements (e.g., a new entry was created in the section), the cache also invalidates. Craft tracks the query parameters, not just the specific results.

### Data cache invalidation (manual)

Data caches have no automatic element tracking. You must invalidate them explicitly:

```php
// Pattern 1: Event-based invalidation in a module/plugin
use craft\elements\Entry;
use craft\events\ModelEvent;
use yii\caching\TagDependency;

Event::on(
    Entry::class,
    Entry::EVENT_AFTER_SAVE,
    function(ModelEvent $event) {
        $entry = $event->sender;
        if ($entry->section->handle === 'products') {
            $cache = Craft::$app->getCache();
            TagDependency::invalidate($cache, 'my-plugin.products');
        }
    }
);

// Pattern 2: TTL-based expiry (simplest)
// Just set a reasonable TTL and let stale data expire naturally
$cache->set('my-plugin.api-data', $data, 300); // 5 minutes

// Pattern 3: Explicit delete after a known mutation
$this->updateExternalApi($data);
$cache->delete('my-plugin.api-response');
```

### Blitz invalidation

Blitz hooks into Craft's element save events and:

1. Determines which cached pages contain the changed element
2. Marks those pages as expired (or deletes them, depending on refresh mode)
3. Queues regeneration of affected pages
4. Sends purge requests to CDN if configured

This is automatic for element-based content. For non-element changes (e.g., global set changes, config changes), Blitz may need manual hints via its API or a full cache clear.

## Development and Debugging

### Disable template caching in dev

```php
// config/general.php
return [
    'dev' => [
        'enableTemplateCaching' => false,
    ],
];
```

This causes `{% cache %}` tags to execute their contents on every request without reading or writing cache entries. Essential for development -- without this, template changes appear not to work because stale cached HTML is served.

### Debugging cache behavior

**Check if a block is being served from cache** -- add timestamps inside and outside the block:

```twig
<p>Page rendered: {{ now|date('H:i:s') }}</p>
{% cache %}
    <p>Cache block rendered: {{ now|date('H:i:s') }}</p>
    {# ... your cached content ... #}
{% endcache %}
```

If the timestamps differ, the inner block is being served from cache.

**Inspect cache entries:** With Redis, use `ddev redis-cli KEYS "*template*"`. With the default database backend, template caches are stored in the `templatecaches` and `templatecachequeries` tables.

### Clearing caches

```bash
# Clear all template caches
ddev craft invalidate-tags/template

# Clear all caches (template + data)
ddev craft invalidate-tags/all

# Clear specific tagged caches
ddev craft invalidate-tags --tag=navigation

# Clear from CP
# Utilities > Clear Caches > Template caches
# Utilities > Clear Caches > Data caches
```

### Common debugging scenarios

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Template changes not appearing | `enableTemplateCaching` is true in dev | Set to `false` for dev environment |
| Stale content after saving entry | Cache key does not include the element query | Verify the query runs inside the `{% cache %}` block |
| CSRF token errors on forms | Token cached inside `{% cache %}` or Blitz page | Move form outside cache block, or use `asyncCsrfInputs` |
| Different users see same personalized content | User-specific content inside `{% cache %}` | Move personalized content outside cache, load via JS |
| Cache grows unboundedly | `{% cache globally %}` with dynamic keys based on URL params | Add `for` TTL or restrict which params generate keys |
| Data cache not updating | No invalidation trigger for data cache | Add `TagDependency` and invalidate on element events |
