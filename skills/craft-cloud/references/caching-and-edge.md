# Caching and Edge — Static Cache Rules + ESI

Cloud's edge layer (Cloudflare) caches HTML responses based on `cache.rules` in `craft-cloud.yaml`. For pages that need a dynamic island inside an otherwise cacheable response, the `cloud.esi(...)` Twig helper renders a fragment at request time without busting the surrounding cache.

## Documentation

- Static caching: https://craftcms.com/docs/cloud/static-caching
- ESI: https://craftcms.com/docs/cloud/esi
- Cache implementation source: https://github.com/craftcms/cloud-extension-yii2/blob/main/src/StaticCache.php
- ESI implementation source: https://github.com/craftcms/cloud-extension-yii2/blob/main/src/Esi.php

## Table of contents

- [Common Pitfalls](#common-pitfalls)
- [Two cache layers: data cache vs edge](#two-cache-layers-data-cache-vs-edge)
  - [Diagnosing which layer is stale](#diagnosing-which-layer-is-stale)
- [Static cache rules](#static-cache-rules)
  - [Required keys per rule](#required-keys-per-rule)
  - [`query-string` syntax](#query-string-syntax)
    - [Default ignored params](#default-ignored-params)
  - [`cookies` syntax](#cookies-syntax)
    - [Serving fresh HTML to logged-in users](#serving-fresh-html-to-logged-in-users)
  - [Rule ordering](#rule-ordering)
  - [Setting cache duration](#setting-cache-duration)
  - [Automatic bypass — and the store-vs-serve trap](#automatic-bypass--and-the-store-vs-serve-trap)
  - [Opting out of caching](#opting-out-of-caching)
  - [Keeping forms cacheable — the flash guard](#keeping-forms-cacheable--the-flash-guard)
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

- Writing a flat `cache.rules:` key, or the cookie-vary key as `session:`. **The structure is nested `cache:` → `rules:`, and the cookie key is `cookies:`** (a plain list). Both mistakes fail *silently* — malformed rules are ignored and you get default caching with no error. See [Static cache rules](#static-cache-rules).
- Assuming logged-in users automatically get fresh (uncached) HTML. **They don't** — once a URL's guest copy is cached, the edge serves it to logged-in requests too (`cf-cache-status: HIT`). `currentUser`-gated UI on a cacheable route silently vanishes for editors. Vary on the session cookie (`cookies: [CraftSessionId]`) to fix it. See [Serving fresh HTML to logged-in users](#serving-fresh-html-to-logged-in-users) and [Automatic bypass](#automatic-bypass--and-the-store-vs-serve-trap).
- Setting `duration: "1h"` inside a cache rule. **`duration` is not a rule key.** Duration is set via the `{% expires %}` Twig tag in the response or via response headers in a controller. Cache rules control *what to cache* and *how to vary the key*, not *for how long*.
- Writing a custom `query-string` rule and losing the built-in tracking-param exclusions. **A custom rule _replaces_ the default behavior and exclusion list** — your `mode: exclude, keys: [page]` rule means `?fbclid=…` now fragments the cache. Re-list the tracking params you care about, or use `mode: include` with only the params that genuinely change the response. See [Default ignored params](#default-ignored-params).
- Rendering the cart in the site header via `craft.commerce.carts.cart`. Commerce reads or writes a cart number to the session on every access, which sends no-cache headers — dynamic cart data on *every* page makes the whole site uncacheable. Scope cart access to on-session pages (cart, checkout, account) and load the header badge via Ajax or ESI.
- Using `path:` instead of `pattern:`. The actual key is `pattern`.
- Listing rules from generic to specific. **First match wins.** Order rules from most specific to least specific (descending specificity).
- Passing a non-scalar value to `cloud.esi(...)`. The docs are explicit: "Only scalar values can be passed to `cloud.esi()`." Pass IDs or handles, then re-fetch the object inside the included template.
- Assuming the included ESI template inherits the parent template's Twig context. It doesn't. The fragment runs as a fresh subrequest with only the variables you explicitly pass.
- Nesting `cloud.esi(...)` inside another ESI fragment. The docs "strongly discourage using edge-side includes inside one another."
- Writing manual `{{ csrfInput() }}` in cacheable templates expecting it to be a synchronous input. Cloud force-enables `asyncCsrfInputs`, so `csrfInput()` renders an async JS-fetched input. Building the input yourself by reading `craft\web\Request::getCsrfToken()` leaks tokens across users — the docs warn this explicitly.
- Using `{{ cloud.esi(...) }}` in a non-HTML response. Only `text/html` and `text/plain` responses are parsed for ESI tags.
- Assuming `clear-caches/*` clears the edge. It does **not** — every `clear-caches` option except `craft-cloud-caches` only clears Craft's *data* cache. "I cleared caches" can leave stale HTML live at the edge. See [Two cache layers](#two-cache-layers-data-cache-vs-edge).

## Two cache layers: data cache vs edge

Cloud has **two independent caches**, and the command that clears one usually doesn't touch the other. Conflating them is why "I deployed the fix" *or* "I cleared caches" can both still leave stale HTML live.

| Layer | Holds | Survives a deploy? | Busted by |
|---|---|---|---|
| **Craft data cache** | Craft's `cache` component — element/template caches, plugin caches (SEOmatic's rendered tags, etc.) | **Yes.** On Cloud this is Redis/Valkey when provisioned (else the DB cache table); Redis is managed separately from the build, so a deploy doesn't flush it. | any `clear-caches/*` option; element-save tag invalidation; `Craft::$app->getCache()` |
| **Edge HTML cache** | The whole rendered HTML response, cached at the Cloudflare edge per `cache.rules` | Purged on every deploy's **Release** step | the deploy (Release), **or** `clear-caches/craft-cloud-caches` — nothing else |

The asymmetry to internalize: **`clear-caches/<anything>` only clears Craft data caches — it never touches the edge.** The one exception is `clear-caches/craft-cloud-caches`, which the Cloud extension registers (`craft\cloud\StaticCache::handleRegisterCacheOptions()`) with an action of `purgeAll()` → `purgeGateway()` + `purgeCdn()` (`StaticCache.php`), purging the edge HTML cache and the CDN for the environment.

So a *code* fix shipped via a normal deploy is covered (Release purges the edge), but a **data-only change applied through the Console command runner** — a migration, a `resave`, a plugin cache clear — clears only the data cache and leaves the edge serving the old HTML until you also run `clear-caches/craft-cloud-caches`.

### Diagnosing which layer is stale

`cf-cache-status` on the response tells you whether the edge served it (`HIT`) or it reached the origin (`MISS`/`DYNAMIC`). To force an origin render and compare, append a unique query string:

```
https://example.com/page?cb=12345
```

A novel query string is a new edge cache key → `MISS` → the request renders at the origin, letting you see fresh HTML independent of the edge. Then:

- `?cb=` shows the fix but the bare URL doesn't → stale value is at the **edge**. Run `clear-caches/craft-cloud-caches`.
- `?cb=` *also* shows the stale value → it's at the **origin**: a Craft data cache (or a plugin's, e.g. SEOmatic) or the underlying data — not the edge.

> Caveat: `?cb=` only forces a MISS while your `cache.rules` let query strings vary the cache key. If a rule sets `query-string: { mode: exclude, keys: all }` for that path, the param is stripped from the key and won't miss — bust the edge with `clear-caches/craft-cloud-caches` instead.

Verified against `craftcms/cloud` `3.2.1` (`src/StaticCache.php`).

## Static cache rules

Cache rules live under a **nested `cache:` → `rules:`** key in `craft-cloud.yaml` — **not** a flat `cache.rules:` key. `rules` is a list, each entry matching a URL pattern and declaring how to vary the cache key. Getting the shape wrong (flat key, or the wrong sub-key name) fails *silently*: the platform ignores the malformed config and you get default caching with no error, which reads as "my rule had no effect."

```yaml
# Top-level key alongside php-version, webroot, etc.
cache:
  rules:
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
      cookies:
        - AD_SOURCE
    - pattern: "/*?"
      query-string:
        mode: exclude
        keys: all
```

### Required keys per rule

Each rule needs `pattern` and at least one of `query-string` or `cookies`.

- **`pattern`** — URL matcher using the same syntax as `redirects` / `rewrites`.
- **`query-string`** — how to handle query parameters in the cache key.
- **`cookies`** — a plain list of cookie names to fold into the cache key. **The key is `cookies:`, not `session:`** (an earlier version of this reference had this wrong — verified against the docs and a live deployment 2026-08-20).

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

Params in the cache key are **alphabetized** — `?page=3&category=widgets` and `?category=widgets&page=3` share one entry.

#### Default ignored params

With **no** custom `query-string` rule, Cloud already excludes a long list of tracking params from cache keys: Google (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid`, `gclsrc`, `dclid`, `wbraid`, `gbraid`), Facebook (`fbclid`, `fb_action_ids`, `fb_action_types`, `fb_source`), Microsoft (`msclkid`), Hubspot (`hsa_*`), Mailchimp (`mc_cid`, `mc_eid`), Klaviyo, and more — the full list is under "Ignored Params" at https://craftcms.com/docs/cloud/static-caching.

**A custom `query-string` rule replaces this default list**, it does not extend it. If you add a rule to vary on `?page`, tracking params start fragmenting your cache again unless you re-exclude them yourself.

### `cookies` syntax

```yaml
cookies:
  - AD_SOURCE
  - REFERRER_NETWORK
```

Each entry is a cookie name. If the cookie is present on the request, its value is added to the cache key — so different cookie values cache separately. Requests **without** the cookie all share one cookieless cache entry. This is a plain list nested directly under the rule (no `mode`/`keys` sub-structure like `query-string`).

#### Serving fresh HTML to logged-in users

The most important use of `cookies:` is the one that isn't obvious: **making logged-in users bypass a cached guest page.** Cloud does **not** do this automatically (see [Automatic bypass](#automatic-bypass--and-the-store-vs-serve-trap)). If a route is cacheable and renders any `currentUser`-gated UI server-side (an author edit link, member-only content), the first guest to hit the URL warms the edge with the logged-out copy, and every later request — including a logged-in editor's — is served *that* copy. The gated UI silently never appears.

Fix: fold the Craft session cookie into the cache key.

```yaml
cache:
  rules:
    - pattern: "/*?"
      query-string:
        mode: exclude
        keys: all
      cookies:
        - CraftSessionId
```

- Guests carry no `CraftSessionId` → they share one fast cached entry per URL. (This holds only if guest requests are genuinely cookieless — a Formie session-writing captcha or a `getCsrfToken()` read will start a session and defeat it; that's the P0-1 class of problem.)
- A logged-in request carries a unique `CraftSessionId` value → distinct cache key → MISS → fresh origin render with `currentUser` present. Logged-in users become effectively uncached on that route, which is correct for personalized output.

`CraftSessionId` is Craft's `phpSessionName` default (`GeneralConfig::$phpSessionName`), bound as the session cookie name in `App::sessionConfig()`. On Cloud the `craftcms/cloud` extension swaps the session class to `DbSession` but keeps the same cookie name. Verify the actual name against a live logged-in request if the site overrides `phpSessionName`. Verified on a production Craft Cloud deployment 2026-08-20.

### Rule ordering

**First match wins.** Order rules from most specific to least specific — the first matching pattern applies and subsequent rules are skipped.

```yaml
# Right — specific first
cache:
  rules:
    - pattern: "/account/*"
      query-string: { mode: include, keys: all }
    - pattern: "/blog/*"
      query-string: { mode: exclude, keys: all }
    - pattern: "/*?"
      query-string: { mode: exclude, keys: all }

# Wrong — /* swallows everything before more specific patterns run
cache:
  rules:
    - pattern: "/*?"
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

Two element-date interactions, same as Craft's own template caches:

- A page whose elements carry an **Expiry Date** sooner than `cacheDuration` is only cached until that content should stop being visible — the extension uses the same expiry information Craft does.
- There is **no mechanism to invalidate a cached page when an element with a future Post Date goes live.** A cached listing won't pick up the newly-published entry until the cache expires or is purged — schedule a `clear-caches/craft-cloud-caches` run, or keep durations short on listing pages that use future Post Dates.

### Automatic bypass — and the store-vs-serve trap

**Correction (2026-08-20):** an earlier version of this reference claimed Cloud auto-bypasses the cache "for any request carrying an authenticated Craft session cookie." That is **wrong**, and it's a dangerous thing to believe. Empirically, a logged-in front-end request to a warmed URL returns `cf-cache-status: HIT` — the edge serves the logged-in user the cached guest copy. The official static-caching docs describe no logged-in auto-bypass.

The confusion comes from conflating two different things:

- **Storing.** Craft's no-cache machinery (a session write, `getCsrfToken()`, `setNoCacheHeaders()`, Live Preview) sets `Cache-Control: no-cache` so that response is **never stored** at the edge. This is what protects authenticated/personalized responses from *being cached and leaked to others*. Merely reading `currentUser` for a **cookieless guest** does not start a session, so it does not block storing (that's why guest pages still cache).
- **Serving.** Once a URL's guest copy **is** stored, the edge serves it to every later request to that URL — logged-in or not — unless the request's cache key differs. No-cache headers on a *response* do nothing to stop the edge serving an *already-stored* copy to a *different* request.

So: no-cache headers prevent leakage (good, automatic), but they do **not** give logged-in users fresh HTML on a cacheable route. To do that you must vary the cache key on the session cookie via [`cookies: [CraftSessionId]`](#serving-fresh-html-to-logged-in-users). If a page is fully dynamic and should never be cached at all, opt it out per-response instead (below).

### Opting out of caching

When a specific response should never be cached even though it matches a `cache.rules` entry:

- Twig: `{% expires %}` (no duration).
- PHP: `$this->response->setNoCacheHeaders();`.

Both ultimately set `Expires`, `Pragma`, and `Cache-Control` headers that tell the edge layer not to cache this response.

### Keeping forms cacheable — the flash guard

Reading session flashes sends no-cache headers, so a form template that unconditionally renders flash messages is never cached — even on the initial GET, when there are no flashes to show. POST submissions are never cached anyway, so the trick is to only touch the session when a submission actually happened, flagged via the redirect URL:

```twig
{# Only read session data when the `success` query param is set: #}
{% if craft.app.request.getQueryParam('success') %}
  {% set flashes = craft.app.session.getAllFlashes(true) %}
  {% for level, flash in flashes %}
    <p>{{ flash }}</p>
  {% endfor %}
{% endif %}

<form method="post">
  {{ csrfInput() }}
  {{ redirectInput(url(craft.app.request.url, { success: true })) }}
  {# … #}
</form>
```

The initial page (no `?success`) never reads the session and stays cacheable (with async CSRF inputs); the post-submit redirect carries `?success=true`, reads flashes, and correctly sends no-cache headers for that render only.

### Cache invalidation

Cloud uses Craft's cache tag system. When you save an entry, asset, or any element, Craft emits the standard invalidation tags; Cloud's edge layer subscribes to those and purges matching cached responses automatically. You don't write invalidation code.

Manual purge: the **Craft Cloud caches** option in the Clear Caches utility (CLI `clear-caches/craft-cloud-caches`) is the only one that reaches the edge — every other option clears data caches only (see [Two cache layers](#two-cache-layers-data-cache-vs-edge)). With no prod CP on Cloud, run it via the Console command runner.

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
| Cookie forwarding | Not documented, and the source suggests ESI is the *wrong* tool for `currentUser`-gated fragments. The include is a signed subrequest to `cloud/esi/render-template` (`allowAnonymous = true`); its edge cache key is the signed src URL = template + scalar variables (no notion of *who* is asking), and `EsiController::actionRenderTemplate` strips the default no-cache headers so the fragment is cacheable. So a guest-first render of a login-gated fragment can be cached and served to everyone — the same bug the surrounding page had. For per-user content, vary the *page* cache on `cookies: [CraftSessionId]`, or render client-side. Verify empirically before relying on ESI for anything session-dependent. |

### When to use ESI

- Session-*starting* but not user-*specific* fragments — the canonical example is a newsletter form's CSRF token in an otherwise cacheable footer, so the rest of the page can cache. (For genuinely per-user content, see the Cookie forwarding constraint above — vary the page cache on the session cookie or fetch client-side instead.)
- Time-sensitive widgets (live scores, stock prices, news ticker) embedded in stable layouts.
- A/B test variants — render the test fragment fresh without invalidating the page cache.

ESI is not a silver bullet: each include is a subrequest, and a dynamic fragment on *every* page still holds up every page. For low-traffic fragments (that footer form), an Ajax fetch triggered by interaction criteria (scroll distance) often beats ESI.

### When not to use ESI

- The whole page is dynamic — set `cache.rules` to skip that route entirely, or use `{% expires %}` with no duration. ESI adds subrequest latency for no caching benefit.
- The dynamic content can be a client-side fetch. JS rendering avoids the edge subrequest cost altogether.
- The fragment depends on rich session state — passing scalars only is restrictive enough that complex personalization is awkward.

### Under the hood

`cloud.esi(...)` emits an `<esi:include>` tag at the edge. The Cloud gateway intercepts it, makes a signed subrequest to a Cloud-managed route, renders the template fresh, and inlines the result into the response. Tamper protection comes from URL signing — you can't construct an arbitrary ESI subrequest from outside the platform.

The implementation lives in `craft\cloud\Esi` and `craft\cloud\controllers\EsiController` in the extension package. You don't write a controller — point `cloud.esi(...)` at a template and the controller handles dispatch.

Last verified against https://craftcms.com/docs/cloud/static-caching, https://craftcms.com/docs/cloud/esi, and `craftcms/cloud-extension-yii2@main` on 2026-05-28. Corrected 2026-08-20 against the current docs and a live production deployment: the cache-rules structure is nested `cache:` → `rules:` (not flat `cache.rules:`), the cookie-vary key is `cookies:` (not `session:`), and there is **no** automatic cache bypass for logged-in users (they are served the cached guest copy unless the key varies on the session cookie). Default ignored params (and rule-replacement behavior), param alphabetization, expiry-date-bounded durations, the flash guard, and the Commerce cart caveat verified against `craftcms/docs@main` static-caching.md on 2026-09-02.
