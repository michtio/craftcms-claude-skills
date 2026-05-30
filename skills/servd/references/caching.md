# Caching — Servd Static Cache + Blitz Alongside It

Servd ships a built-in **static cache**: when enabled, the platform serves HTML snapshots straight from its proxy layer without booting PHP. You configure it in the dashboard, exclude the routes that must stay dynamic, and reach into cached pages with the `{% dynamicInclude %}` Twig tag for per-request islands. Blitz, if you want it, runs **alongside** the static cache in reverse-proxy mode — not as a replacement. See `asset-storage.md` for the `servd/craft-asset-storage` plugin that backs the CSRF and cache-busting behavior here, `deploy-and-environments.md` for `SERVD_BUNDLE_HASH`, and `limitations.md` for the load-balanced filesystem that dictates Blitz's mode.

## Documentation

- Static caching: https://servd.host/docs/static-caching
- Caching with Blitz: https://servd.host/docs/caching-with-blitz
- Cache busting: https://servd.host/docs/cache-busting
- Plugin console commands: https://servd.host/docs/servd-plugin-console-commands

## Common Pitfalls

- **Treating Blitz as a replacement for Servd's static cache.** On Servd you run Blitz *alongside* it. Configure Blitz in reverse-proxy mode — Blitz's default server-rewrite setup is broken by Servd's load-balanced instances. See the Blitz section below.
- **Leaving the control panel cacheable.** Add URL-prefix exceptions in the dashboard for the CP and any user-specific pages at minimum, or you'll serve one user's authenticated page to another.
- **Reaching for `craft.blitz.includeDynamic()` on a Servd-only setup.** That's a Blitz *function*. Servd's native equivalent is the `{% dynamicInclude %}` *Twig tag* — different mechanism, different syntax.
- **Frozen CSRF tokens in cached forms.** A statically cached page bakes in a stale CSRF token, so form posts fail. Enable Servd's CSRF token injection (plugin setting) — it swaps the baked token for an uncached value via injected JS.
- **Filename-hashed asset busting under static caching.** Hashed filenames baked into cached HTML 404 after the next deploy serves new filenames. Prefer query-string busting with `SERVD_BUNDLE_HASH` (below).
- **Expecting Tag-Based purge to be exhaustive.** Servd's docs warn it "might, in some edge case circumstances, result in some URLs being missed." Use Full Purge if absolute freshness matters more than traffic spikes.

## Enabling Static Caching

In the dashboard go to **Environment > Static Caching**, toggle it on, set a **Default Cache TTL** (or choose **Use Origin Headers** to respect the `Cache-Control` headers your responses emit), then click **Sync** to deploy the change. Once active, matching requests are served as HTML snapshots from Servd's proxy without hitting PHP.

## Purge Strategies

Two automatic strategies, set in the same dashboard panel:

- **Full Purge** — brute force. "Destroys the entire static cache immediately whenever a 'live' Craft Element is updated." Simple and always correct; causes a traffic spike as the whole cache rebuilds.
- **Automated Tag-Based Purge** — tracks which Elements render each URL during the render pass. On update, only the affected URLs purge, so traffic stays smooth. The trade-off: the tagging system is complex and "might, in some edge case circumstances, result in some URLs being missed."

The **automatic trigger** is configurable independently:

- **None** — never purge automatically.
- **Only when entries are updated via the control panel** — CP edits only.
- **When entries are updated in any way** — any entry save (front-end, console, queue, etc.).

## Excluding Pages

Add **URL-prefix exceptions** in **Environment > Static Caching**. Any incoming request whose path begins with one of these prefixes bypasses the static cache entirely and goes straight to PHP. At minimum exclude the Craft control panel and any user-specific pages (accounts, carts, dashboards). Craft's action URL is excluded by default on Servd — which is what makes `{% dynamicInclude %}` work.

## Dynamic Islands — `{% dynamicInclude %}`

For a fragment that must render fresh inside an otherwise-cached page, use the `{% dynamicInclude %}` tag. It is a **Twig tag** (not a function) and its syntax mirrors a standard `{% include %}`:

```twig
{% dynamicInclude 'snippets/login' with {key: 'val'} only %}
```

The surrounding HTML stays cached; the included template is fetched dynamically per request via Craft's action URL (which is excluded from the cache by default). Pass only what the fragment needs with `with {...} only`, exactly as you would for an isolated include.

This is Servd's native equivalent of Blitz's `craft.blitz.includeDynamic()` function — do not confuse the two. If you're also running Blitz here, prefer one mechanism per fragment; see `craft-site` for the Blitz dynamic-include patterns.

## CSRF Token Injection

A statically cached page captures whatever CSRF token was current at snapshot time, so forms on cached pages submit with a stale token and fail. Servd's **CSRF token injection** setting (provided by the `servd/craft-asset-storage` plugin — see `asset-storage.md`) injects JavaScript that finds CSRF tokens in the cached HTML and replaces them with a freshly fetched, uncached value. Enable it whenever cached pages contain forms.

## Cache-Busting

The `servd/craft-asset-storage` plugin auto-busts the static cache on entry-save events (subject to the automatic-trigger setting above). For **assets across deploys**, use the `SERVD_BUNDLE_HASH` env var — Servd injects it at each bundle sync with "a unique hash of various aspects of the deployed bundle, e.g. the git commit hash, PHP version, etc." Append it as a query parameter so every deploy serves a distinct URL:

```twig
<link rel="stylesheet" href="/assets/main.css?v={{ getenv('SERVD_BUNDLE_HASH') }}">
```

Prefer this query-string approach over filename hashing: filename-hashed assets baked into cached HTML 404 after the next deploy rotates the filenames. (If you must hash filenames, clear the static cache in a Post-Deploy Task or ship historical asset copies in the bundle.) See `deploy-and-environments.md` for `SERVD_BUNDLE_HASH` in the build context.

## Manual Invalidation

- **CP** — **Utilities > Clear Caches**, check **Servd Static Cache**.
- **Entry edit pages** — a purge button on the entry's edit screen clears that entry's URLs.
- **CLI** — `./craft clear-caches/servd-static-cache` clears the entire static cache for the current environment.
- **CLI (edge)** — `./craft clear-caches/servd-edge-caches` clears Servd's web **and** asset edge caches for an environment. Available as of plugin **v3.7.0** / **v4.2.0**.

## Blitz Alongside Servd (Reverse-Proxy Mode)

Servd's docs are explicit: run Blitz **with** the static cache as a reverse-proxy cache, **not instead of it**. Blitz is a complementary plugin here, not a competitor to Servd's caching.

You **must** use reverse-proxy mode because "Servd has the ability to run your Craft project in a load balanced configuration, [so] it isn't directly compatible with Blitz's suggested 'server rewrites' setup." Multiple load-balanced instances break Blitz's default server-rewrite approach.

Configure Blitz's plugin settings:

- **Cache Storage** = **Yii Cache Storage**
- **Cache Generator** = **HTTP Generator**
- **Reverse Proxy Purging** = add the **Servd Static Cache Purger**

And the complementary Servd static-cache configuration:

- **Static Caching**: enabled
- **Default Cache TTL**: **Use Origin Headers** (Blitz drives the headers)
- **Include query params**: on, with all params selected

With the Servd Static Cache Purger in place, Blitz can purge URLs within Servd's static cache as needed, so cache rules live entirely in Blitz's settings while Servd's layer does the serving. For Blitz template integration (cache tags, dynamic includes, injected content), see the `craft-site` skill's Blitz docs.

Last verified against https://servd.host/docs/static-caching, https://servd.host/docs/caching-with-blitz, https://servd.host/docs/cache-busting, and https://servd.host/docs/servd-plugin-console-commands on 2026-05-30.
