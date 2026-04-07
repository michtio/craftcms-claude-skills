# Debugging & Performance

## Documentation

- Element queries: https://craftcms.com/docs/5.x/development/element-queries.html
- Eager loading: https://craftcms.com/docs/5.x/development/eager-loading.html
- Query batching: https://craftcms.com/knowledge-base/query-batching-batch-each

## Common Pitfalls

- Element query inside a loop without eager loading — classic N+1.
- Using `->all()` when you only need `->count()`, `->ids()`, or `->exists()`.
- Choosing ElementQuery when ActiveRecord or direct Query builder would be more appropriate.
- Forgetting `->status(null)` on cached element queries — status changes over time create different cache keys.
- Using Yii's `$query->batch()` instead of `Db::each()` — Yii's version doesn't handle unbuffered MySQL properly.
- Not disabling Xdebug when not debugging — significant overhead even when idle.
- Transform generation during page load — push to queue or pre-generate.

## Query Strategy: When to Use What

Three query approaches, each with different tradeoffs:

### Element Queries — for element data you'll display or manipulate

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
->count()     // SELECT COUNT(*) — don't load objects just to count them
->ids()       // SELECT id only — when you just need IDs
->exists()    // SELECT 1 LIMIT 1 — existence check
->pairs()     // Key-value pairs from two columns
->asArray()   // Skip Element model hydration, return plain arrays
```

### ActiveRecord — for plugin config tables (non-element data)

Thin table mapping for your plugin's own config/settings tables (instances, match fields, site settings). Not for element data:

```php
/** @var MyRecord[] $records */
$records = MyRecord::find()
    ->where(['categoryId' => $categoryId])
    ->orderBy(['sortOrder' => SORT_ASC])
    ->all();
```

ActiveRecord gives you model objects with `save()`, `delete()`, and relation definitions, but no element lifecycle. Use for the `handleChangedItem()` pattern in project config handlers.

### Direct Query Builder — for performance-critical joins and aggregates

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

Also use for `eagerLoadingMap()` implementations — these need raw source→target ID mappings, not full element objects:

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

Craft 5 introduced lazy eager loading via `.eagerly()` — automatically batches relation loading in template loops. `.with()` supports nested dot notation for manual pre-declaration. These are template patterns, not plugin-side, but worth knowing when your element type is consumed in Twig.

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
// Element ownership — cascade delete when element is hard-deleted
$this->addForeignKey(null, Table::MY_ELEMENTS, ['id'], CraftTable::ELEMENTS, ['id'], 'CASCADE', null);

// Reference to config entity — null out when config entity deleted
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

Enabled when `devMode` is `true`. Users enable it under My Account → Preferences.

**Most useful panels:**
- **DB panel**: All queries, sortable by duration — fastest way to find N+1.
- **Profiling panel**: Custom `beginProfile`/`endProfile` blocks.
- **Logs panel**: All log messages for the request.

## Xdebug with DDEV

```bash
ddev xdebug on   # Enable step debugging
ddev xdebug off  # Disable when done — significant overhead
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
