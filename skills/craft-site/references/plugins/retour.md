# Retour

Intelligent redirect manager by nystudio107. Handles static and regex redirects, tracks 404s, automatically creates redirects on slug changes, supports CSV import/export, and provides a GraphQL API. SEOMatic's companion for URL management — used in 5/6 projects.

`nystudio107/craft-retour` — $59

## Documentation

- Overview: https://nystudio107.com/docs/retour/
- Configuration: https://nystudio107.com/docs/retour/configuring.html
- Using: https://nystudio107.com/docs/retour/using.html

When unsure about a Retour feature, `web_fetch` the relevant docs page.

## Common Pitfalls

- Not enabling automatic slug-change redirects — this is Retour's killer feature. When an editor changes an entry's slug, Retour auto-creates a redirect from the old URL to the new one. Enable it in Settings.
- Creating exact-match redirects when regex is needed — for URL pattern changes (e.g., `/blog/2024/*` → `/articles/*`), use regex redirects. Exact matches won't catch variations.
- Not reviewing the 404 dashboard regularly — Retour tracks 404s with hit counts. High-traffic 404s indicate broken links or missing redirects.
- Redirect loops — creating a redirect from A → B when B already redirects to A. Retour doesn't detect loops automatically.
- Using Retour for canonical URL handling — redirects and canonicals serve different purposes. Use SEOMatic for canonicals, Retour for redirects.
- Importing CSV without matching column format — Retour expects specific column ordering. Export first to see the format, then match your import file.

## Config File

```php
// config/retour.php
return [
    '*' => [
        // Create redirects automatically when entry slugs change
        'createUriChangeRedirects' => true,

        // Preserve query strings when redirecting
        'preserveQueryString' => true,

        // Strip query strings from 404 tracking (reduces noise)
        'stripQueryStringFromStats' => true,

        // How many 404 stats to keep per URL
        'statsStoredLimit' => 1000,

        // Redirect status code for auto-created redirects
        'uriChangeRedirectSrcMatch' => 'pathonly',

        // Enable the dashboard widget
        'enableDashboardWidget' => true,

        // Additional headers to send with redirects
        'additionalHeaders' => [],
    ],
];
```

## Redirect Types

| Type | Match | Use Case |
|------|-------|----------|
| Exact Match | `/old-page` → `/new-page` | Single URL redirects |
| Regex Match | `/blog/(.*)` → `/articles/$1` | Pattern-based URL restructuring |
| 301 | Permanent | Default — SEO weight transfers |
| 302 | Temporary | Short-term redirects (promotions, maintenance) |

## CSV Import/Export

### Export

CP → Retour → Redirects → Export CSV. Downloads all redirects in Retour's format.

### Import

CP → Retour → Redirects → Import CSV. Columns must match the export format:

| Column | Description |
|--------|-------------|
| Legacy URL | Source URL pattern |
| Redirect To | Destination URL |
| Match Type | `exactmatch` or `regexmatch` |
| Status Code | `301` or `302` |

### Console Commands

```bash
# Clear all 404 statistics
ddev craft retour/stats/clear

# Trim 404 stats to configured limit
ddev craft retour/stats/trim
```

## 404 Dashboard

CP → Retour → 404s shows:

- URLs generating 404 errors
- Hit count per URL
- Last hit timestamp
- Referrer information
- Quick "create redirect" action per 404

Use this to identify broken inbound links and fix them systematically.

## Twig API

Retour doesn't have a front-end Twig API — it operates at the routing layer before templates render. Redirects are processed on every request before Craft's template rendering kicks in.

## GraphQL

```graphql
{
  retour {
    redirects {
      legacyUrl
      redirectDestUrl
      redirectHttpCode
      hitCount
      hitLastTime
    }
  }
}
```

## Multi-Site

Redirects can be scoped per-site or applied globally across all sites. Site-specific redirects take precedence over global ones.

## Pair With

- **SEOMatic** — handles all SEO meta; Retour handles all redirects (SEOMatic explicitly does not handle redirects)
- **Blitz** — Retour redirects are processed before Blitz serves cached pages
