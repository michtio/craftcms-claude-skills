# Cache Igniter

Edge cache warming by putyourlightson. Keeps CDN caches warm globally after Blitz refreshes pages. Warms from multiple geographic locations so the first visitor from any region gets a fast HIT, not a cold MISS. Blitz's companion plugin.

`putyourlightson/craft-cache-igniter` — $99

## Documentation

- Overview: https://putyourlightson.com/plugins/cache-igniter
- GitHub: https://github.com/putyourlightson/craft-cache-igniter

## Common Pitfalls

- Using Cache Igniter without Blitz — it's designed as a Blitz companion. Without Blitz generating static pages, there's nothing to warm.
- Warming all pages on large sites — CDN warming is an HTTP request per page per location. On a 10,000-page site with 5 locations, that's 50,000 requests per refresh. Limit to important pages.
- Not setting `refreshDelay` — when editors save multiple entries in quick succession, each save triggers a Blitz refresh. The delay batches them so warming runs once, not per-save.
- Expecting instant warming — warming is queued and runs asynchronously. There's a brief window after refresh where some edge locations are cold.

## Config File

```php
// config/cache-igniter.php
return [
    // Warmer driver — GlobalPing warms from multiple locations
    'warmerType' => 'putyourlightson\cacheigniter\drivers\warmers\GlobalPingWarmer',
    'warmerSettings' => [
        'locations' => [
            'US West',
            'US East',
            'UK',
            'Germany',
            'Australia',
        ],
    ],

    // Delay warming after Blitz refresh (seconds) — batches rapid edits
    'refreshDelay' => 30,

    // Only warm important pages (reduces API calls)
    'includedUriPatterns' => [
        ['siteId' => '', 'uriPattern' => '^$'],           // Homepage
        ['siteId' => '', 'uriPattern' => 'services/.*'],   // Services
        ['siteId' => '', 'uriPattern' => 'about'],          // About
    ],

    // Exclude pages from warming
    'excludedUriPatterns' => [
        ['siteId' => '', 'uriPattern' => 'account/.*'],
    ],
];
```

## How It Works

1. Content editor saves an entry
2. Blitz refreshes the affected cached pages
3. Cache Igniter detects the refresh (after `refreshDelay`)
4. Sends HTTP requests to warmed pages from each configured location
5. CDN edge nodes cache the fresh response — visitors get HITs

## Warmer Drivers

| Driver | Description |
|--------|-------------|
| GlobalPingWarmer | Warms from multiple geographic locations via GlobalPing |
| HttpWarmer | Simple HTTP requests from the server (single location) |

GlobalPingWarmer is the primary value — without it, only the origin server's closest edge node is warm.

## Pair With

- **Blitz** — required. Cache Igniter hooks into Blitz's refresh events.
- **Cloudflare** — Cache Igniter + Blitz Cloudflare purger ensures edge cache is purged then immediately re-warmed.
