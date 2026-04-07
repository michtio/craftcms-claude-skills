# Elements Panel

Debug toolbar plugin by PutYourLightsOn. Adds an Elements panel and an Eager-Loading panel to Craft's debug toolbar for benchmarking template performance. Shows element population counts, duplicates, and missed eager-loading opportunities. Essential development-time tool — used in 5/6 projects.

`putyourlightson/craft-elements-panel` — Free (MIT)

## Documentation

- Docs: https://putyourlightson.com/plugins/elements-panel
- GitHub: https://github.com/putyourlightson/craft-elements-panel

## Setup

Install, then enable the debug toolbar:

1. CP → My Account → Preferences → check "Show the debug toolbar on the front end"
2. Visit the front-end — the Elements and Eager-Loading panels appear in the debug toolbar

No config file. No settings. Just install and use.

## Elements Panel

Shows how many elements were populated during the request, grouped by element type. Flags **duplicates** — the same element populated more than once.

A duplicate means an element was fetched multiple times during a single request. Fix with eager-loading (`.with()` / `.eagerly()`) or memoizing the query result to a variable.

Some duplicates are acceptable (globals, navigation nodes accessed from multiple templates). The warning is when duplicates "explode" — e.g., 200 duplicate entries from an N+1 inside a loop.

## Eager-Loading Panel

Shows element queries that **could** have been eager-loaded. Grouped by field name. Flags duplicate queries — the same relation field queried multiple times when it could have been eager-loaded.

Use this to identify:
- Relation fields inside loops missing `.eagerly()`
- Matrix blocks whose nested relations aren't eager-loaded
- Asset transforms not being preloaded

## Common Pitfalls

- Not enabling the debug toolbar — the panels don't appear unless it's active. This is a per-user setting, not global.
- Ignoring it in development — this is the fastest way to catch N+1 problems before they hit production. Check it on every template.
- Treating all duplicates as problems — some duplication is normal (globals, user elements). Focus on high-count duplicates.
- Only checking on simple pages — test on index pages with many entries and deep relation chains. That's where N+1 problems surface.

## Pair With

- **Blitz** — fix N+1 issues found by Elements Panel, then cache the optimized pages with Blitz
- **Web Vitals skill** — Elements Panel surfaces the template-level performance issues that affect TTFB
