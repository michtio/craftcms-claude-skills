# Feed Me

First-party data import plugin by Pixel & Tonic. Imports XML, JSON, CSV, RSS, ATOM, and Google Sheets into Craft elements (entries, categories, users, assets, Commerce products). GUI-based field mapping, duplicate handling, CLI automation. Used for content migrations, external data sync, and recurring imports.

`craftcms/feed-me` — Free

## Documentation

- GitHub: https://github.com/craftcms/feed-me
- Plugin Store: https://plugins.craftcms.com/feed-me

When unsure about a Feed Me feature, `WebFetch` the GitHub README.

## Common Pitfalls

- Memory limits on large feeds — PHP's default `memory_limit` is often too low for feeds with thousands of items. Increase to `512M` or higher in `php.ini` for CLI imports. Disable `devMode` and the debug toolbar during imports — they consume enormous memory by logging every query.
- Queue vs direct processing — web-based "Direct" processing is subject to PHP `max_execution_time` and proxy timeouts. For feeds with more than a few hundred items, always queue the feed and process via CLI with `ddev craft queue/run`. This avoids timeouts entirely.
- Element ID mapping trap — never map an external system's numeric ID to Craft's element ID. Craft auto-assigns element IDs. If you need to track external IDs, store them in a custom field and use that field as the unique identifier.
- Unique identifier fragility — the unique identifier determines whether an existing element is updated or a new one is created. If an editor changes the field value that serves as the unique identifier (e.g., editing a title used for matching), the next import creates a duplicate instead of updating.
- Debug mode runs the import — the "Debug" button in the CP processes the feed for real against your database. It is not a dry run or preview. Use it only in dev environments.
- Empty values clearing existing data — by default, blank/missing values in the feed can overwrite existing field values with empty content. Configure the "Set empty values" option per field mapping to control this behavior. Set to "Don't update" for fields that should only be written when the feed provides a value.
- Matrix unique identifiers are unreliable — Feed Me's duplicate detection for nested Matrix entries does not work consistently. Expect Matrix blocks to be re-created on each import unless you carefully test your specific mapping.
- devMode kills import performance — with `devMode` on, Craft logs every database query. A 5,000-entry import can generate millions of log entries, consuming memory and slowing the import by 10x or more. Always disable `devMode` when running production imports.

## Import Strategy (Duplicate Handling)

Configure these options per feed to control how imports interact with existing content:

| Option | Behavior | Use when |
|--------|----------|----------|
| Create new elements | Inserts elements that don't match the unique identifier | Initial import, ongoing sync with new items |
| Update existing elements | Updates elements that match the unique identifier | Recurring sync where source data changes |
| Disable missing elements | Disables elements not present in the current feed | Source is authoritative — missing = inactive |
| Delete missing elements | Permanently deletes elements not in the current feed | Source is authoritative — missing = removed |

Common combinations:

- **Initial migration:** Create new only.
- **Recurring sync:** Create new + Update existing. Keeps Craft in sync with the external source without touching items that disappeared from the feed.
- **Authoritative source:** Create new + Update existing + Disable missing. The feed is the single source of truth. Items removed from the feed get disabled in Craft so editors can review before permanent deletion.
- **Full mirror:** Create new + Update existing + Delete missing. Dangerous — items removed from the feed are permanently deleted. Use only when the external system is the sole authority and you have backups.

## CLI Commands

```bash
ddev craft feed-me/feeds/queue 1        # Queue feed by ID
ddev craft feed-me/feeds/queue --all    # Queue all configured feeds
ddev craft queue/run                     # Process the queue (runs all queued jobs)
```

Useful flags for `feed-me/feeds/queue`:

- `--limit=100` — process only the first N items from the feed
- `--offset=50` — skip the first N items (combine with `--limit` for batching)
- `--continue-on-error` — don't stop the entire feed if one element fails

For large imports, combine limit/offset to process in batches:

```bash
ddev craft feed-me/feeds/queue 1 --limit=500 --offset=0 && ddev craft queue/run
ddev craft feed-me/feeds/queue 1 --limit=500 --offset=500 && ddev craft queue/run
```

## Config (`config/feed-me.php`)

```php
// config/feed-me.php
return [
    '*' => [
        // Log feed processing details (stored in storage/logs/feed-me.log)
        'logging' => true,

        // Parse Twig expressions in feed URLs — allows dynamic URLs like
        // {{ now|date('Y-m-d') }} in feed URLs configured in the CP
        'parseTwig' => false,

        // Request options passed to Guzzle when fetching feed URLs
        'requestOptions' => [
            'timeout' => 60,
            'verify' => true,
        ],

        // Queue TTR (time-to-reserve) in seconds — increase for slow feeds
        'queueTtr' => 300,

        // Sleep time in microseconds between element saves (throttling)
        'sleepBetweenSaves' => 0,
    ],
    'production' => [
        'logging' => true,
    ],
    'dev' => [
        'logging' => true,
        'parseTwig' => true,
    ],
];
```

## Events

Feed Me fires events for custom processing at key points:

```php
use craft\feedme\events\FeedProcessEvent;
use craft\feedme\services\Process;
use yii\base\Event;

// Before each element is saved
Event::on(
    Process::class,
    Process::EVENT_BEFORE_PROCESS_FEED,
    function(FeedProcessEvent $event) {
        // $event->feedData — raw data from feed
        // $event->element — the Craft element being populated
    }
);

// After each element is saved
Event::on(
    Process::class,
    Process::EVENT_AFTER_PROCESS_FEED,
    function(FeedProcessEvent $event) {
        // Post-processing: trigger external API calls, logging, etc.
    }
);
```

## When to Use vs Custom Scripts

| Scenario | Use Feed Me | Use custom import script |
|----------|-------------|--------------------------|
| One-time content migration | Yes — fast setup via GUI | Only if data needs heavy transformation |
| Recurring sync from simple API | Yes — schedule with cron + CLI | If the API requires auth flows or pagination beyond simple URLs |
| Complex data transformation | No | Yes — PHP gives full control over mapping logic |
| Conditional logic per row | No | Yes — Feed Me applies the same mapping to every row |
| Importing into multiple sections from one feed | No — one feed = one element type | Yes — a script can route rows to different sections |
| Non-technical editors managing imports | Yes — the CP GUI is accessible | No — scripts require developer involvement |

For complex migrations, consider Feed Me for the straightforward content types and a custom console command (via a module) for anything that needs conditional logic or multi-step processing.

## Multi-Site

Feed Me is site-aware. Each feed targets a specific site. When importing content that should exist across multiple sites, configure the entry's propagation method in the section settings — Feed Me creates the element on the target site, and Craft's propagation handles the rest.

For multi-site imports where content differs per site (e.g., translated content), create separate feeds per site pointing to site-specific data sources.

## Pair With

- **Blitz** — enable the FeedMeIntegration in Blitz config to auto-refresh cached pages after imports
- **Element API** — import external data via Feed Me, expose it as JSON via Element API
- **Retour** — set up redirects for any URLs that change as a result of re-imported content
