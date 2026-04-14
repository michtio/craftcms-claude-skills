# Debugging & Performance

## Documentation

- Element queries: https://craftcms.com/docs/5.x/development/element-queries.html
- Eager loading: https://craftcms.com/docs/5.x/development/eager-loading.html
- Query batching: https://craftcms.com/knowledge-base/query-batching-batch-each
- Template caching: https://craftcms.com/docs/5.x/reference/twig/tags.html#cache
- Deprecation warnings: https://craftcms.com/docs/5.x/system/deprecation-warnings.html

## Common Pitfalls

- Element query inside a loop without eager loading -- classic N+1.
- Using `->all()` when you only need `->count()`, `->ids()`, or `->exists()`.
- Choosing ElementQuery when ActiveRecord or direct Query builder would be more appropriate.
- Forgetting `->status(null)` on cached element queries -- status changes over time create different cache keys.
- Using Yii's `$query->batch()` instead of `Db::each()` -- Yii's version doesn't handle unbuffered MySQL properly.
- Not disabling Xdebug when not debugging -- significant overhead even when idle.
- Transform generation during page load -- push to queue or pre-generate.
- Wrapping dynamic content in `{% cache %}` tags -- stale output for logged-in users, CSRF tokens, live dates.
- Using `entry.relatedEntries.all()` inside a loop instead of eager loading on the parent query.
- Calling `craft.entries.section('x').all()|length` to count -- loads all element objects into memory just to count them.

## Contents

- [Query Strategy: When to Use What](#query-strategy-when-to-use-what)
- [Eager Loading (Plugin-Side)](#eager-loading-plugin-side)
- [Indexes and Foreign Keys](#indexes-and-foreign-keys)
- [Batch Processing](#batch-processing)
- [Logging](#logging)
- [Profiling](#profiling)
- [Debug Toolbar](#debug-toolbar)
- [Template Debugging](#template-debugging)
- [Twig Cache Tag](#twig-cache-tag)
- [N+1 Detection and Fixes](#n1-detection-and-fixes)
- [Query Logging and Analysis](#query-logging-and-analysis)
- [Error Handling Patterns](#error-handling-patterns)
- [Deprecation Tracking](#deprecation-tracking)
- [Common Anti-Patterns](#common-anti-patterns)
- [Xdebug with DDEV](#xdebug-with-ddev)
- [Caching](#caching)

## Query Strategy: When to Use What

Three query approaches, each with different tradeoffs:

### Element Queries -- for element data you'll display or manipulate

The full Craft element system: field values, statuses, drafts, permissions, eager loading. Use when you need elements as objects with their full behavior:

```php
$entries = MyElement::find()
    ->status('live')
    ->categoryId($categoryId)
    ->orderBy('postDate DESC')
    ->limit(10)
    ->all();
```

**Performance shortcuts on element queries:**

```php
->count()     // SELECT COUNT(*) -- don't load objects just to count them
->ids()       // SELECT id only -- when you just need IDs
->exists()    // SELECT 1 LIMIT 1 -- existence check
->pairs()     // Key-value pairs from two columns
->asArray()   // Skip Element model hydration, return plain arrays
```

### ActiveRecord -- for plugin config tables (non-element data)

Thin table mapping for your plugin's own config/settings tables (instances, match fields, site settings). Not for element data:

```php
/** @var MyRecord[] $records */
$records = MyRecord::find()
    ->where(['categoryId' => $categoryId])
    ->orderBy(['sortOrder' => SORT_ASC])
    ->all();
```

ActiveRecord gives you model objects with `save()`, `delete()`, and relation definitions, but no element lifecycle. Use for the `handleChangedItem()` pattern in project config handlers.

### Direct Query Builder -- for performance-critical joins and aggregates

When you need complex JOINs, aggregations, subqueries, or bulk operations where neither ElementQuery nor ActiveRecord is appropriate:

```php
$stats = (new Query())
    ->select([
        'categoryId',
        'COUNT(*) as total',
        'SUM(CASE WHEN [[status]] = :live THEN 1 ELSE 0 END) as liveCount',
    ])
    ->from(Table::MY_ELEMENTS)
    ->groupBy('categoryId')
    ->addParams([':live' => 'live'])
    ->all();
```

Also use for `eagerLoadingMap()` implementations -- these need raw source-to-target ID mappings, not full element objects:

```php
$map = (new Query())
    ->select(['source' => 'id', 'target' => 'relatedItemId'])
    ->from(Table::MY_ELEMENTS)
    ->where(['id' => $sourceIds])
    ->all();
```

### Decision Guide

| Need | Use |
|------|-----|
| Elements with field values, statuses, permissions | Element Query |
| Plugin config/settings records (non-element tables) | ActiveRecord |
| Aggregations, complex JOINs, bulk reads | Query builder |
| Eager loading maps, raw ID lookups | Query builder |
| Project config handlers (`handleChanged`) | ActiveRecord |
| Element counts, ID lists, existence checks | Element Query with `->count()` / `->ids()` / `->exists()` |

## Eager Loading (Plugin-Side)

### Custom Eager Loading Map

For custom elements with relations to other elements, implement `eagerLoadingMap()`:

```php
public static function eagerLoadingMap(array $sourceElements, string $handle): array|null|false
{
    if ($handle === 'relatedItems') {
        $sourceIds = array_map(fn($el) => $el->id, $sourceElements);
        $map = (new Query())
            ->select(['source' => 'id', 'target' => 'relatedItemId'])
            ->from(Table::MY_ELEMENTS)
            ->where(['id' => $sourceIds])
            ->all();

        return ['elementType' => RelatedItem::class, 'map' => $map];
    }

    return parent::eagerLoadingMap($sourceElements, $handle);
}
```

### Pre-loading in Services

When your service returns elements that consumers will iterate over, pre-load relations:

```php
public function getItemsWithRelations(int $categoryId): array
{
    return MyElement::find()
        ->categoryId($categoryId)
        ->with(['relatedItems', 'relatedItems.thumbnail'])
        ->all();
}
```

### Twig-Side (Front-End Templates)

Craft 5 introduced lazy eager loading via `.eagerly()` -- automatically batches relation loading in template loops. `.with()` supports nested dot notation for manual pre-declaration. These are template patterns, not plugin-side, but worth knowing when your element type is consumed in Twig.

## Indexes and Foreign Keys

Design your migration indexes around how your element queries filter:

```php
// Compound index for the most common query pattern
$this->createIndex(null, Table::MY_ELEMENTS, ['categoryId', 'externalId'], true);

// Single-column indexes for date-based filtering and sorting
$this->createIndex(null, Table::MY_ELEMENTS, ['postDate']);
$this->createIndex(null, Table::MY_ELEMENTS, ['expiryDate']);
```

Foreign keys with appropriate ON DELETE behavior:

```php
// Element ownership -- cascade delete when element is hard-deleted
$this->addForeignKey(null, Table::MY_ELEMENTS, ['id'], CraftTable::ELEMENTS, ['id'], 'CASCADE', null);

// Reference to config entity -- null out when config entity deleted
$this->addForeignKey(null, Table::MY_ELEMENTS, ['categoryId'], Table::CATEGORIES, ['id'], 'SET NULL', null);
```

## Batch Processing

### `Db::each()` for Large Datasets

Craft's wrapper handles unbuffered MySQL connections:

```php
use craft\helpers\Db;

$query = MyElement::find()->categoryId($categoryId)->site('*')->status(null);

foreach (Db::each($query) as $element) {
    // Process one at a time, constant memory
}

// Or in batches of 100
foreach (Db::batch($query, 100) as $batch) {
    foreach ($batch as $element) {
        // Process batch
    }
}
```

### Memory Management

```php
App::maxPowerCaptain(); // Raises memory_limit, removes max_execution_time
```

Craft calls this automatically for queue jobs. For console commands, call explicitly at the start of long-running actions.

## Logging

```php
Craft::debug('Trace-level, devMode only', __METHOD__);
Craft::info('Info level, devMode only', 'my-plugin');
Craft::warning('Always logged', 'my-plugin');
Craft::error('Always logged', 'my-plugin');
```

**In production, only `warning` and above are logged.** Use the plugin handle as the category for easy filtering.

Log files: `storage/logs/web-{date}.log`, `console-{date}.log`, `queue-{date}.log`. For containers: `CRAFT_STREAM_LOG=true`.

## Profiling

```php
Craft::beginProfile('expensiveOperation', __METHOD__);
// ... code to profile ...
Craft::endProfile('expensiveOperation', __METHOD__);
```

Shows in the Debug Toolbar's Time panel.

## Debug Toolbar

Enabled when `devMode` is `true`. Users enable it under My Account > Preferences.

**Most useful panels:**
- **DB panel**: All queries, sortable by duration -- fastest way to find N+1.
- **Profiling panel**: Custom `beginProfile`/`endProfile` blocks and per-template render times.
- **Logs panel**: All log messages for the request.
- **Deprecation panel**: Deprecation warnings triggered during the request.
- **Mail panel**: Emails sent during the request (useful for verifying queue notifications).

## Template Debugging

### `dump()` and `dd()`

Both require `devMode` to be enabled:

```twig
{{ dump(entry) }}                          {# Dumps to debug bar, does not halt #}
{{ dd(entry) }}                            {# Dump and die -- halts execution #}
{{ dump(entry, category, currentUser) }}   {# Multiple variables #}
{{ dump() }}                               {# All variables in current scope #}
```

### Quick JSON inspection

Lightweight alternative to `dump()` for raw field values:

```twig
<pre>{{ entry.myMatrixField|json_encode(constant('JSON_PRETTY_PRINT')) }}</pre>
<pre>{{ craft.entries.section('blog').limit(3).ids()|json_encode }}</pre>
```

### devMode error display

When `devMode` is `true`, Craft shows verbose Yii error pages with full stack traces, query logs, and environment details. When `false`, Craft renders custom error templates (see [Error Handling Patterns](#error-handling-patterns)). Never leave `devMode` enabled in production -- stack traces expose file paths, database queries, and environment variables.

### Template profiling

The Profiling panel in the debug toolbar breaks down render time per template. Look for templates with high self-render time, templates called many times per request (unoptimized loops), and compilation overhead on first load.

## Twig Cache Tag

The `{% cache %}` tag caches rendered HTML. Craft tracks element queries inside the block and invalidates when those elements change.

### Basic usage

```twig
{% cache %}
    {% set entries = craft.entries.section('blog').limit(10).all() %}
    {% for entry in entries %}
        <article>{{ entry.title }}</article>
    {% endfor %}
{% endcache %}
```

### Options

| Option | Example | Effect |
|--------|---------|--------|
| `globally` | `{% cache globally %}` | Shared across all URLs (default: per-URL) |
| `using key` | `{% cache using key "sidebar-nav" %}` | Custom cache key |
| `for` | `{% cache for 3600 %}` or `{% cache for "1 hour" %}` | Explicit duration |
| `if` | `{% cache if not currentUser %}` | Conditional caching |
| `unless` | `{% cache unless craft.app.request.isPreview %}` | Inverse conditional |
| `tag` | `{% cache tag('blog-list') %}` | Tag-based invalidation group |

Options can be combined: `{% cache globally using key "footer-nav" for "6 hours" tag('navigation') %}`.

### Invalidation

Craft automatically tracks every element query inside a `{% cache %}` block. When those elements change, the cache is invalidated. For manual tag-based invalidation:

```bash
ddev craft invalidate-tags/template --tag=blog-list   # Specific tag
ddev craft invalidate-tags/all                         # All template caches
```

### Key notes

- `enableTemplateCaching` in `config/general.php` disables all `{% cache %}` tags when `false`. Use in development to avoid stale output. Cross-reference `config-general.md`.
- Do not cache dynamic content -- CSRF tokens, user names, timestamps become stale. Move dynamic parts outside the cache block.
- Cache blocks use the configured cache backend (database default, or Redis/Memcached via `app.php`).

## N+1 Detection and Fixes

### What N+1 looks like

1 query fetches a list, then N queries fire in the loop for relations. 50 entries with 1 relation = 51 queries instead of 2.

```twig
{# BAD: N+1 -- each iteration fires a query for relatedArticles #}
{% set entries = craft.entries.section('blog').limit(50).all() %}
{% for entry in entries %}
    {% set related = entry.relatedArticles.all() %}
{% endfor %}
```

### How to spot in the debug toolbar

Open the **DB panel**: many identical query patterns with different IDs = N+1. Sort by "Count" to find repeated templates. A listing page with 200+ queries almost always has an eager loading problem.

### Fix with `.with()` (PHP side)

```php
$entries = Entry::find()->section('blog')->limit(50)
    ->with(['relatedArticles', 'relatedArticles.featuredImage'])
    ->all();
```

### Fix with `.eagerly()` (Twig side)

```twig
{% for entry in entries %}
    {% set related = entry.relatedArticles.eagerly().all() %}
{% endfor %}
```

### Matrix/nested eager loading

```php
->with(['matrixField.blockTypeHandle:relationField', 'matrixField.blockTypeHandle:relationField.thumbnail'])
```

### Query count comparison

| Scenario | Without | With eager loading |
|----------|---------|-------------------|
| 50 entries, 1 relation each | 51 queries | 2 queries |
| 50 entries, 2 relations each | 101 queries | 3 queries |
| 50 entries + Matrix + nested relation | 151+ queries | 3-4 queries |

## Query Logging and Analysis

### devMode query logging

When `devMode` is `true`, every query is logged to the debug toolbar DB panel automatically.

### `CRAFT_DB_LOG_SQL` environment variable

For SQL logging outside devMode (staging, production debugging):

```bash
# .env -- remove after debugging, creates significant log volume
CRAFT_DB_LOG_SQL=1
```

Logs to `storage/logs/` or stdout with `CRAFT_STREAM_LOG=true`.

### Reading the DB panel

1. **Sort by Duration**: Queries over 100ms need investigation. Over 1s are highlighted.
2. **Sort by Count**: Repeated identical templates with different params = N+1.
3. **Total query count**: Typical page load is 20-60 queries. 200+ = eager loading problem.
4. **Explain plans**: Click a query to see MySQL `EXPLAIN` -- watch for `type: ALL` (full table scan).

## Error Handling Patterns

### Craft exception types

| Exception (`craft\errors\`) | When thrown |
|------------------------------|-----------|
| `ElementNotFoundException` | Element save fails -- element no longer exists |
| `MissingComponentException` | Referenced component class not found |
| `SiteNotFoundException` | Requested site ID/handle does not exist |
| `InvalidFieldException` | Field handle does not exist on the element |
| `MutexException` | Could not acquire a mutex lock |

### Try/catch in services

```php
use craft\errors\ElementNotFoundException;

public function processEntry(int $entryId): bool
{
    try {
        $entry = Entry::find()->id($entryId)->status(null)->one();
        if (!$entry) {
            throw new ElementNotFoundException("Entry $entryId not found");
        }
        Craft::$app->getElements()->saveElement($entry);
        return true;
    } catch (ElementNotFoundException $e) {
        Craft::warning("Skipping missing entry: {$e->getMessage()}", __METHOD__);
        return false;
    } catch (\Throwable $e) {
        Craft::error("Failed to process entry $entryId: {$e->getMessage()}", __METHOD__);
        throw $e;
    }
}
```

### Controller error responses

```php
// CP controller -- JSON or redirect based on Accept header
return $this->asFailure('Could not save the record.');

// Front-end -- throw HTTP exceptions for error templates
throw new \yii\web\NotFoundHttpException('Page not found');
throw new \yii\web\ForbiddenHttpException('Access denied');
```

### Custom error templates

Craft renders error templates based on HTTP status code:

```
templates/404.twig    -- Not Found
templates/500.twig    -- Internal Server Error
templates/error.twig  -- Fallback for unmatched codes
```

Use `errorTemplatePrefix` in `config/general.php` to organize in a subdirectory (e.g., `'_errors/'` makes Craft look for `templates/_errors/404.twig`).

Available variables: `statusCode` (HTTP code) and `message` (exception message in devMode, generic status text in production).

## Deprecation Tracking

### Logging deprecations in plugins

```php
Craft::$app->getDeprecator()->log(
    'myPlugin.oldMethod',           // Unique key -- Craft groups by this
    'The `oldMethod()` method has been deprecated. Use `newMethod()` instead.',
);
```

### Debug toolbar deprecation panel

Shows all deprecation warnings for the request with message, file/line, and stack trace. Also accessible in the CP via Utilities > Deprecation Warnings.

### Clearing and managing

```bash
ddev craft clear-deprecations   # Clear all stored warnings
```

### Craft 4 to 5 upgrade relevance

Before upgrading: enable `devMode`, browse all key pages, check the Deprecation Warnings utility, and fix all warnings. Deprecated APIs are removed in the next major version. Pay attention to Twig function/filter changes and element query parameter renames.

## Common Anti-Patterns

| Anti-Pattern | Impact | Fix |
|-------------|--------|-----|
| `entry.relatedEntries.all()` inside a loop | N+1 queries | `.with(['relatedEntries'])` on parent query or `.eagerly()` |
| `craft.entries.section('x').all()\|length` | Loads all elements to count | `.count()` instead |
| Transform generation during page load | Slow TTFB | `generateTransformsBeforePageLoad: false` in general config |
| `{% cache %}` wrapping dynamic content | Stale CSRF tokens, user data | Move dynamic parts outside cache block |
| No eager loading on Matrix blocks | N+1 on nested relations | `.with(['matrixField.blockType:relationField'])` |
| `entry.fieldHandle` without `.one()` or `.all()` | Returns query object, not results | Always terminate with `.one()`, `.all()`, or `.exists()` |
| `{% for entry in craft.entries.section('x').all() %}` no limit | Loads entire section | Add `.limit()` or paginate |
| Querying inside a Twig macro called per-iteration | Hidden N+1 | Pass data into the macro as a parameter |
| `\|merge` in a Twig loop | O(n^2) -- copies array each iteration | Build array in PHP, pass to template |

## Xdebug with DDEV

```bash
ddev xdebug on   # Enable step debugging
ddev xdebug off  # Disable when done -- significant overhead
```

DDEV pre-configures Xdebug 3 on port 9003. For VS Code `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [{
        "name": "Listen for Xdebug",
        "type": "php",
        "request": "launch",
        "port": 9003,
        "pathMappings": {
            "/var/www/html": "${workspaceFolder}"
        }
    }]
}
```

CLI debugging works automatically. Troubleshoot with `ddev xdebug-diagnose`.

## Caching

### Data Caches with Tag Dependency

```php
use yii\caching\TagDependency;

$dependency = new TagDependency(['tags' => ['my-plugin:items']]);
$data = Craft::$app->cache->getOrSet(
    'my-plugin:all-items',
    fn() => $this->_expensiveQuery(),
    3600,
    $dependency
);

// Invalidate when data changes
TagDependency::invalidate(Craft::$app->cache, 'my-plugin:items');
```

### Element Query Cache

```php
$results = MyElement::find()
    ->status('live')
    ->cache(60)  // Auto-invalidates via ElementQueryTagDependency
    ->all();
```
