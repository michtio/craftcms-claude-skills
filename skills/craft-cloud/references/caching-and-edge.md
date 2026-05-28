# Caching and Edge — Static Cache Rules + ESI

Cloud's edge layer (Cloudflare) caches HTML responses based on `cache.rules` in `craft-cloud.yaml`. For pages that need a dynamic island inside an otherwise cacheable response, the `cloud.esi(...)` Twig helper renders a fragment at request time without busting the surrounding cache.

## Documentation

- Static caching: https://craftcms.com/docs/cloud/static-caching
- ESI: https://craftcms.com/docs/cloud/esi
- Cache implementation source: https://github.com/craftcms/cloud-extension-yii2/blob/main/src/StaticCache.php
- ESI implementation source: https://github.com/craftcms/cloud-extension-yii2/blob/main/src/Esi.php

## Table of contents

- [Common Pitfalls](#common-pitfalls)
- [Static cache rules](#static-cache-rules)
  - [Required keys per rule](#required-keys-per-rule)
  - [`query-string` syntax](#query-string-syntax)
  - [`session` syntax](#session-syntax)
  - [Rule ordering](#rule-ordering)
  - [Setting cache duration](#setting-cache-duration)
  - [Automatic bypass](#automatic-bypass)
  - [Opting out of caching](#opting-out-of-caching)
  - [Cache invalidation](#cache-invalidation)
  - [Relationship to `{% cache %}`](#relationship-to--cache-)
- [ESI — `cloud.esi(...)`](#esi--cloudesi)
  - [Signature](#signature)
  - [Examples](#examples)
  - [Constraints](#constraints)
  - [When to use ESI](#when-to-use-esi)
  - [When not to use ESI](#when-not-to-use-esi)
  - [Under the hood](#under-the-hood)

## Common Pitfalls

- Setting `duration: "1h"` inside a `cache.rules` entry. **`duration` is not a cache.rules key.** Duration is set via the `{% expires %}` Twig tag in the response or via response headers in a controller. Cache.rules controls *what to cache*, not *for how long*.
- Using `path:` instead of `pattern:`. The actual key is `pattern`.
- Listing rules from generic to specific. **First match wins.** Order rules from most specific to least specific (descending specificity).
- Passing a non-scalar value to `cloud.esi(...)`. The docs are explicit: "Only scalar values can be passed to `cloud.esi()`." Pass IDs or handles, then re-fetch the object inside the included template.
- Assuming the included ESI template inherits the parent template's Twig context. It doesn't. The fragment runs as a fresh subrequest with only the variables you explicitly pass.
- Nesting `cloud.esi(...)` inside another ESI fragment. The docs "strongly discourage using edge-side includes inside one another."
- Writing manual `{{ csrfInput() }}` in cacheable templates expecting it to be a synchronous input. Cloud force-enables `asyncCsrfInputs`, so `csrfInput()` renders an async JS-fetched input. Building the input yourself by reading `craft\web\Request::getCsrfToken()` leaks tokens across users — the docs warn this explicitly.
- Using `{{ cloud.esi(...) }}` in a non-HTML response. Only `text/html` and `text/plain` responses are parsed for ESI tags.

## Static cache rules

`cache.rules` in `craft-cloud.yaml` is a list of rules, each matching a URL pattern and declaring how to vary the cache key.

```yaml
cache.rules:
  - pattern: "/account/*"
    query-string:
      mode: include
      keys: all
  - pattern: "/search"
    query-string:
      mode: include
      keys:
        - q
        - category
  - pattern: "/blog/*"
    query-string:
      mode: exclude
      keys:
        - utm_source
        - utm_medium
        - utm_campaign
    session:
      - AD_SOURCE
  - pattern: "/*"
    query-string:
      mode: exclude
      keys: all
```

### Required keys per rule

Each rule needs `pattern` and at least one of `query-string` or `session`.

- **`pattern`** — URL matcher using the same syntax as `redirects` / `rewrites` (regex with capture groups).
- **`query-string`** — how to handle query parameters in the cache key.
- **`session`** — cookie/session names to vary on.

### `query-string` syntax

```yaml
query-string:
  mode: include   # or "exclude"
  keys: all       # or a list of param names
```

- `mode: include` + `keys: all` — every query param participates in the cache key. `?a=1&b=2` and `?a=1&b=3` are separate cache entries.
- `mode: include` + `keys: [q, category]` — only the listed params vary the cache. Other params are stripped from the cache key (they still reach Craft, they just don't make the response cache uniquely).
- `mode: exclude` + `keys: [utm_source, utm_medium, ...]` — every param **except** the listed ones varies the cache. The classic "ignore UTM params" pattern.
- `mode: exclude` + `keys: all` — no params participate in the cache key. The cleanest "ignore everything" setting.

### `session` syntax

```yaml
session:
  - AD_SOURCE
  - REFERRER_NETWORK
```

Each entry is a cookie name. If the cookie is present on the request, its value is added to the cache key — so different cookie values cache separately. Cookies absent from the request are ignored.

### Rule ordering

**First match wins.** Order rules from most specific to least specific — the first matching pattern applies and subsequent rules are skipped.

```yaml
# Right — specific first
cache.rules:
  - pattern: "/account/*"
    query-string: { mode: include, keys: all }
  - pattern: "/blog/*"
    query-string: { mode: exclude, keys: all }
  - pattern: "/*"
    query-string: { mode: exclude, keys: all }

# Wrong — /* swallows everything before more specific patterns run
cache.rules:
  - pattern: "/*"
    query-string: { mode: exclude, keys: all }
  - pattern: "/account/*"
    query-string: { mode: include, keys: all }    # never matches
```

### Setting cache duration

Duration is set in the response, not in `cache.rules`. Three equivalent ways:

**Twig:**
```twig
{% expires in 1 hour %}
```

**Controller action:**
```php
$this->response->getHeaders()->set('Cache-Control', 'public, max-age=3600');
```

**Twig calling PHP directly:**
```twig
{% do craft.app.response.setNoCacheHeaders() %}
```

The `{% expires %}` tag accepts human-readable durations (`1 hour`, `30 minutes`, `1 day`). Without arguments, it explicitly opts the response out of caching for the current request.

### Automatic bypass

Cloud auto-bypasses the static cache for any request that:

- Carries an authenticated Craft session cookie.
- Accesses `currentUser` in the template (Craft's CSRF/session machinery detects this and emits no-cache headers).
- Reads session flashes.
- Runs in Live Preview.

You don't add manual `vary: cookie` entries to handle these — Craft handles the bypass headers automatically.

### Opting out of caching

When a specific response should never be cached even though it matches a `cache.rules` entry:

- Twig: `{% expires %}` (no duration).
- PHP: `$this->response->setNoCacheHeaders();`.

Both ultimately set `Expires`, `Pragma`, and `Cache-Control` headers that tell the edge layer not to cache this response.

### Cache invalidation

Cloud uses Craft's cache tag system. When you save an entry, asset, or any element, Craft emits the standard invalidation tags; Cloud's edge layer subscribes to those and purges matching cached responses automatically. You don't write invalidation code.

Manual purge: available in the CP Utilities screen ("Cache Utility") — the standard Craft cache utility, which now reaches Cloud's edge layer in addition to Craft's data caches.

### Relationship to `{% cache %}`

Craft's `{% cache %}` template tag still works on Cloud, but it's largely redundant with edge static caching. The edge layer caches the whole HTML response, not just a Twig fragment — so wrapping a block in `{% cache %}` saves rendering time only on cache misses (which are rarer when the whole page is cached at the edge). Keep `{% cache %}` for expensive query-heavy blocks; remove it from purely-presentational blocks where it adds maintenance burden without payoff.

## ESI — `cloud.esi(...)`

A Twig helper that embeds a dynamic fragment inside an otherwise cached page. The fragment is rendered fresh per request at the edge; the surrounding HTML stays cached.

### Signature

```twig
{{ cloud.esi(template, variables) }}
```

- `template` (string, required) — path to a Twig template, resolved like any `include`.
- `variables` (object, optional) — scalar values to pass to the included template.

### Examples

```twig
{# Cached page with a dynamic island #}
{% expires in 1 hour %}

<header>
    <h1>{{ entry.title }}</h1>
    {# Account widget renders fresh every request #}
    {{ cloud.esi('_partials/account-nav.twig') }}
</header>

<main>
    {{ entry.body|raw }}
</main>

<aside>
    {# Personalized recommendations — passing the entry ID as a scalar #}
    {{ cloud.esi('_partials/recommendations.twig', { sourceId: entry.id }) }}
</aside>
```

The output at the edge looks identical to a non-ESI render — the user can't tell which parts came from cache vs subrequest.

### Constraints

| Constraint | Behavior |
|---|---|
| Variable types | Scalar only — no objects, no collections. Pass IDs/handles, re-fetch inside the template. |
| Parent Twig context | Not inherited. Variables must be passed explicitly. |
| Response types | Only `text/html` and `text/plain` responses are parsed for ESI tags. |
| Nesting | Strongly discouraged — don't put `cloud.esi(...)` inside another ESI fragment. |
| Cookie forwarding | Not documented in detail — verify behavior empirically if your fragment depends on session cookies. |

### When to use ESI

- Per-user content (account name in header, cart badge count) inside a mostly-cacheable page.
- Time-sensitive widgets (live scores, stock prices, news ticker) embedded in stable layouts.
- A/B test variants — render the test fragment fresh without invalidating the page cache.

### When not to use ESI

- The whole page is dynamic — set `cache.rules` to skip that route entirely, or use `{% expires %}` with no duration. ESI adds subrequest latency for no caching benefit.
- The dynamic content can be a client-side fetch. JS rendering avoids the edge subrequest cost altogether.
- The fragment depends on rich session state — passing scalars only is restrictive enough that complex personalization is awkward.

### Under the hood

`cloud.esi(...)` emits an `<esi:include>` tag at the edge. The Cloud gateway intercepts it, makes a signed subrequest to a Cloud-managed route, renders the template fresh, and inlines the result into the response. Tamper protection comes from URL signing — you can't construct an arbitrary ESI subrequest from outside the platform.

The implementation lives in `craft\cloud\Esi` and `craft\cloud\controllers\EsiController` in the extension package. You don't write a controller — point `cloud.esi(...)` at a template and the controller handles dispatch.

Last verified against https://craftcms.com/docs/cloud/static-caching, https://craftcms.com/docs/cloud/esi, and `craftcms/cloud-extension-yii2@main` on 2026-05-28.
