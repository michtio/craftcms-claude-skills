# Architecture — Services, Models, Records, Project Config

## Documentation

- Services: https://craftcms.com/docs/5.x/extend/services.html
- Project config: https://craftcms.com/docs/5.x/extend/project-config.html
- Events: https://craftcms.com/docs/5.x/extend/events.html
- Module guide: https://craftcms.com/docs/5.x/extend/module-guide.html

## Common Pitfalls

- Forgetting to reset MemoizableArray cache (`$this->_items = null`) after data changes — stale data persists for the entire request.
- Including `id` in `getConfig()` — project config uses UIDs as cross-environment identifiers, never database IDs.
- Putting business logic in models or records — models validate, records map to tables, services contain logic.
- Exposing a bare `getApi()` without explicit context (instance, site, account) — always require the scoping parameter.
- Using `DateTimeHelper` in services — services use `Carbon` for date arithmetic.
- Not firing before/after events on save and delete — other plugins can't extend your code without them.
- Deleting managed entities without cleaning up Craft elements first — CASCADE on the FK won't touch the `elements` table.
- Skipping the rebuild handler — without `EVENT_REBUILD`, `project-config/rebuild` breaks your plugin's config.
- Treating project-config writes as always-available — they're mutex-guarded (`ProjectConfig::MUTEX_NAME`), so concurrent writes throw `BusyResourceException` / `StaleResourceException`. Uncaught in a controller that's a 500; catch and retry or return a 409. See `controllers.md` (Project-config writes from controllers), and the `craft-pest` skill's `craft-state.md` for why the same exceptions cascade inside rolled-back test transactions.
- Keeping plugin/operational settings (alert thresholds, notification routing, workflow mappings) in a DB-only column to allow "per-environment tuning" — project config is the canonical settings store; the real risk is YAML↔DB divergence, fixed by keeping project config authoritative, not by bypassing it. Use env vars / `config/{handle}.php` for genuinely per-environment values. See [Settings belong in project config](#settings-belong-in-project-config--including-operational-settings).
- Assigning ActiveRecord datetime columns directly to typed Model properties — ActiveRecord returns raw SQL strings, not `DateTime` objects. Use `DateTimeHelper::toDateTime($record->dateCreated) ?: null`. See [Record-to-Model Hydration Boundary](#record-to-model-hydration-boundary).
- Using `if ($cached !== false)` to check cache hits — Yii's `cache->get()` returns `false` for missing keys, which collides with a legitimately cached `false` value. If you cache booleans, use string sentinels (`'on'`/`'off'`) or check `cache->exists()` before `get()`.
- Plugin controller directory case not matching namespace — `controllers/Front/` vs `controllers/front/` works on macOS (case-insensitive APFS) but breaks on Linux containers, CI, and production (case-sensitive ext4). The directory name must exactly match the namespace segment casing.
- Shipping front-end example templates as bare body fragments (no `<html>`/`<head>`/`<body>`) — they render as broken pages if hit directly and give integrators nothing working to start from. Ship a complete, copyable bundle with its own layout shell plus an install console command. See [Front-End Output From Plugins](#front-end-output-from-plugins) and the craft-site skill's `example-templates.md`.
- A render-builder class whose config-array constructor silently ignores unknown keys — a typo (`{ digitz: 6 }`) then does nothing with no error. Make an unknown key throw so mistakes fail loudly. See [Front-End Output From Plugins](#front-end-output-from-plugins).
- Calling `Sites::refreshSites()` after creating a site and assuming element queries now filter by site — they don't. `refreshSites()` refreshes `_isMultiSite`, but `ElementQuery::beforePrepare()` gates its `siteId` clause on the separately-memoized `_isMultiSiteWithTrashed`. Also call `Craft::$app->getIsMultiSite(true, true)`. See [Creating or deleting sites at runtime](#creating-or-deleting-sites-at-runtime).
- Trusting in-process `Entries`/`Categories` service caches after `deleteSite()` — core prunes the project-config paths but never nulls those services' `MemoizableArray` memos, so section and category-group models still carry the deleted site. And delete the site *before* saving category groups: `Categories::saveGroup()` throws if `siteSettings` omits any currently-existing site. See [Creating or deleting sites at runtime](#creating-or-deleting-sites-at-runtime).
- Parsing a datetime column value with `strtotime()` or bare `new DateTime()` — the column holds a **naive UTC** string while Craft has set the process timezone to `system.timeZone`, so every comparison shifts by the full UTC offset on a non-UTC install (and is correct on a UTC one, so it passes CI). Use `DateTimeHelper::toDateTime()` or `Carbon::createFromFormat(..., 'UTC')`. See [Those strings are naive UTC](#those-strings-are-naive-utc--never-parse-them-with-ambient-timezone-functions).
- Passing a Yii operator tuple to an element-query param setter — `->title(['like', 'foo%'])` is parsed as two *literal values* OR'd into an `IN`, so it matches nothing, silently and permanently. Use `->andWhere(['like', 'elements_sites.title', 'foo%', false])`. See [Element-query param setters don't take Yii operator tuples](#element-query-param-setters-dont-take-yii-operator-tuples).
- Comparing a stored value that may end in `*` through a query-param helper — `Db::parseParam()` treats a leading or trailing asterisk as a SQL `LIKE` wildcard, so a "uniqueness check" silently matches by prefix. See [Db::parseParam() turns asterisks into wildcards](#dbparseparam-turns-asterisks-into-wildcards).
- Serializing a hash chain (or any ordered writer) without bounded retry on MySQL deadlocks — under concurrency the loser of a lock cycle throws SQLSTATE 40001 and, if the caller catches `Throwable` and continues, the write is lost silently. See [Serialized writers need bounded deadlock retry](#serialized-writers-need-bounded-deadlock-retry).
- Storing IPs (or comparable personal data) with no privacy story — no data inventory, no retention statement, no anonymization option. Ship `docs/privacy.md` and offer an `anonymizeIp` lightswitch applied at the storage boundary. See [Storing Personal Data](#storing-personal-data).

## Table of Contents

- [Scaffolding](#scaffolding)
- [Plugin Class Structure](#plugin-class-structure) — entry class naming, ServicesTrait + PluginTrait split
- [Services](#services)
- [Models](#models)
- [Records (ActiveRecord)](#records-activerecord)
- [Project Config](#project-config) — incl. creating or deleting sites at runtime (the two caches that don't refresh)
- [Yii2 Core Validators](#yii2-core-validators)
- [Custom Validators](#custom-validators)
- [Plugin Editions](#plugin-editions) — declaring, checking, feature gating, edition switching, helper methods, migrations
- [Front-End Output From Plugins](#front-end-output-from-plugins) — example-templates command, fluent render builders
- [Storing Personal Data](#storing-personal-data) — IP/PII data inventory, retention, lawful basis, `anonymizeIp`

## Scaffolding

```bash
ddev craft make service --with-docblocks
ddev craft make model --with-docblocks
ddev craft make record --with-docblocks
```

Then customize: add section headers, `@author`, `@since`, `@throws` chains.

## Plugin Class Structure

### Entry Class Naming

The entry file and class name match the plugin handle in PascalCase: handle `forum` → `src/Forum.php` / `class Forum`; handle `userProfile` → `src/UserProfile.php` / `class UserProfile`.

**Never ship a plugin as `src/Plugin.php` / `class Plugin`.** The Craft generator and most starter templates produce that default, but it has to be renamed before going further. Every plugin's main class would otherwise just be `Plugin`, distinguished only by namespace alias — call sites read `Plugin::getInstance()->tools` everywhere, which is ambiguous in multi-plugin source trees and grep-unfriendly. Renaming to `Forum::getInstance()->tools` is self-documenting and unique across the ecosystem.

Update `composer.json` `extra.class` to match the new FQN:

```json
{
    "extra": {
        "handle": "forum",
        "class": "vendor\\forum\\Forum"
    }
}
```

### Renaming an Existing Plugin

For plugins that shipped with `src/Plugin.php`, the migration is mechanical:

```bash
# 1. Rename file and class
git mv src/Plugin.php src/Forum.php
# Edit src/Forum.php: change `class Plugin` to `class Forum` and any self-type hints

# 2. Update composer.json extra.class to the new FQN

# 3. Sweep every reference
grep -rln 'vendor\\forum\\Plugin' src/ tests/ docs/
# Update each match: vendor\forum\Plugin → vendor\forum\Forum

# 4. Verify
ddev composer dump-autoload
ddev composer phpstan        # Catches any missed references
ddev craft pest/test
```

PHPStan is the safety net — unresolved class names surface immediately if any reference was missed.

### Trait Split

As the plugin grows, the entry class accumulates service wiring, event listeners, URL rule registration, and settings-form overrides — quickly becoming unreadable. Split these into two traits so the main class stays a thin orchestrator:

- **`src/services/ServicesTrait.php`** — service registration. Implements `static config()` (Craft reads this during plugin construction and merges it into the Yii config; no `setComponents()` call in `init()`), typed `getX(): X` accessors that wrap `$this->get('x')` with an `assert($component instanceof X)` narrowing call, and `@property X $name` docblocks on the trait class. **The trait owns the `@property` tags — never duplicate them on the main plugin class.**
- **`src/base/PluginTrait.php`** — private `_register*` methods (events, URL rules), plugin lifecycle overrides (`getSettingsResponse()`, `getReadOnlySettingsResponse()`, `createSettingsModel()`), and anything else that would clutter `init()`.

Adopt `ServicesTrait` as soon as a plugin has 2+ services. A plugin with 0 or 1 services can declare its component inline in the main class without the trait — the split exists to keep service wiring out of the way once the count grows.

The trait body holds the registration and the typed accessors. Each getter narrows Yii's `Component::get()` return (signed `?object`) with `assert($component instanceof Xxx)` so PHPStan level 8 resolves the type:

```php
/**
 * @property Items $items
 * @property Sync $sync
 */
trait ServicesTrait
{
    public static function config(): array
    {
        return [
            'components' => [
                'items' => ['class' => Items::class],
                'sync' => ['class' => Sync::class],
            ],
        ];
    }

    public function getItems(): Items
    {
        $component = $this->get('items');
        assert($component instanceof Items);
        return $component;
    }

    public function getSync(): Sync
    {
        $component = $this->get('sync');
        assert($component instanceof Sync);
        return $component;
    }
}
```

The `assert()` is load-bearing. Yii's `Component::get()` is declared `?object` — PHPStan can't narrow the return without help, so the getter signature `getItems(): Items` would fail strict typing without the assertion. The trait's `@property` tags make property-style access (`$plugin->items`) work alongside method-style (`$plugin->getItems()`); Yii's `__get('items')` walks the trait's `getItems()`.

The main plugin class then collapses to a thin shell. Its class-level docblock describes what the plugin **does** — not which services it registers. Any service enumeration in the docblock ("wires three services: X, Y, Z") drifts the moment a service is added or removed; let the trait be the source of truth for that map:

```php
/**
 * Forum — discussion threads, posts, and moderation for Craft 5.
 *
 * @author Vendor
 * @since 1.0.0
 */
class Forum extends Plugin
{
    public static Forum $plugin;
    public string $schemaVersion = '5.0.0';
    public bool $hasCpSettings = true;
    public bool $hasCpSection = true;

    use ServicesTrait;
    use PluginTrait;

    public function init(): void
    {
        parent::init();
        self::$plugin = $this;
        Craft::setAlias('@vendor/forum', __DIR__);

        $this->_registerEvents();
        $this->_registerCpRoutes();
    }
}
```

Note what's **not** on the main class: no `@property-read` tags duplicating the trait's `@property` map. One source of truth — the trait. Adding a service means editing the trait (new getter + new `@property` tag) and `static config()` (new component entry); the main class doesn't change.

## Services

### MemoizableArray Pattern

For entities managed through project config or any cached lookups:

```php
/**
 * @var MemoizableArray<MyEntity>|null
 * @see _items()
 */
private ?MemoizableArray $_items = null;

private function _items(): MemoizableArray
{
    if (!isset($this->_items)) {
        $records = MyEntityRecord::find()->all();
        $this->_items = new MemoizableArray(
            array_map(fn($record) => new MyEntity($record->getAttributes()), $records)
        );
    }

    return $this->_items;
}

public function getAllItems(): array
{
    return $this->_items()->all();
}

public function getItemById(int $id): ?MyEntity
{
    return $this->_items()->firstWhere('id', $id);
}
```

Always reset the cache when data changes: `$this->_items = null;`

### Event Pattern

Fire before/after events on all significant operations:

```php
public const EVENT_BEFORE_SAVE_ITEM = 'beforeSaveItem';

if ($this->hasEventHandlers(self::EVENT_BEFORE_SAVE_ITEM)) {
    $this->trigger(self::EVENT_BEFORE_SAVE_ITEM, new MyEntityEvent([
        'entity' => $entity,
        'isNew' => $isNew,
    ]));
}
```

### API Client Factory

Always require explicit context — never expose a bare `getClient()`:

```php
public function getApiClient(int $instanceId): Api
{
    $instance = $this->getItemById($instanceId);
    if (!$instance) {
        throw new InvalidConfigException("No instance found for ID: {$instanceId}");
    }

    return new Api($instance->apiKey, $instance->apiUrl);
}
```

### External API Rate-Limit Backoff

When your plugin calls rate-limited external APIs (HIBP, Stripe, Mailgun, geocoding services, etc.), use a **site-wide** cache key for backoff — not a per-user or per-entity key. A 429 response means the API is throttled for your entire install, not for a single request:

```php
$cacheKey = 'my-plugin:api-name:429-backoff';
$cache = Craft::$app->getCache();

// Check if we're in a backoff window
if ($cache->get($cacheKey)) {
    // Skip the API call — still rate-limited
    return null;
}

try {
    $response = $client->request('GET', $endpoint);
} catch (ClientException $e) {
    if ($e->getResponse()->getStatusCode() === 429) {
        $retryAfter = (int)($e->getResponse()->getHeaderLine('Retry-After') ?: 60);
        $cache->set($cacheKey, true, $retryAfter);
        return null;
    }
    throw $e;
}
```

Key the cache by **service name**, not by user/entity/request. Per-entity dedup keys mean every concurrent request burns a new API call inside the rate-limit window. The sentinel key with `Retry-After` TTL ensures the entire install backs off together.

### Date Arithmetic in Services

Use `Carbon` for comparison and arithmetic:

```php
use Carbon\Carbon;

$staleness = Carbon::parse($record->dateUpdated)->diffInMinutes(Carbon::now());
if ($staleness >= self::STALE_THRESHOLD_MINUTES) {
    // Handle stale operation
}
```

## Models

```php
class MyEntity extends Model
{
    public ?int $id = null;
    public ?string $uid = null;
    public string $name = '';
    public string $handle = '';
    public int $batchSize = 50;

    protected function defineRules(): array
    {
        $rules = parent::defineRules();
        $rules[] = [['name', 'handle'], 'required'];
        $rules[] = [['handle'], UniqueValidator::class, 'targetClass' => MyEntityRecord::class];
        $rules[] = [['batchSize'], 'integer', 'min' => 1, 'max' => 500];
        return $rules;
    }
}
```

### getConfig() for Project Config

Never include `id` — UIDs are the cross-environment identifier:

```php
public function getConfig(): array
{
    return [
        'name' => $this->name,
        'handle' => $this->handle,
        'batchSize' => (int)$this->batchSize,
    ];
}
```

### Settings Model (Plugins only)

```php
class SettingsModel extends Model
{
    public bool $enableSync = true;
    public int $defaultBatchSize = 50;

    protected function defineRules(): array
    {
        return [
            [['defaultBatchSize'], 'integer', 'min' => 1],
        ];
    }
}
```

### Settings Lifecycle (Plugins)

Plugin settings are merged and frozen at plugin construction — not lazily on each `getSettings()` call. The order:

1. `craft\services\Plugins::createPlugin()` merges the project-config row with `config/{handle}.php` overrides before the plugin object exists:

    ```php
    $settings = array_merge(
        $info['settings'] ?? [],                              // project config row
        Craft::$app->getConfig()->getConfigFromFile($handle), // config/{handle}.php
    );
    $config['settings'] = $settings;
    $plugin = Craft::createObject($config, [$handle, Craft::$app]);
    ```

2. Yii applies `$config['settings']` via the `setSettings()` setter during construction. `setSettings()` calls `getSettings()` (which lazily instantiates the empty model via `createSettingsModel()`), then writes the merged attributes onto it with `setAttributes($settings, false)`.

3. From that point on, `Plugin::getSettings()` returns the memoized `$_settings` model for the rest of the request. Every later call — from `init()`, from event closures registered in `init()`, from controllers, from Twig — returns the same instance with the same merged values.

**Consequence:** capturing `$settings` outside an event listener closure is equivalent to resolving it inside. Both observe the same merged model within a single request. There is no "stale-before-load" window in Craft's bootstrap.

This differs from Laravel/Symfony service containers where settings/config can be mutated mid-request through the container. Code reviewers should not flag the outside-the-closure pattern as a runtime bug by analogy; flag only with a concrete repro through Craft's actual call paths.

Settings *do* change between requests when the CP settings form saves: the flow is `Plugins::savePluginSettings()` → project config write → next request reads the merged values fresh from `Plugins::createPlugin()`. Within a single request the settings model is effectively immutable.

References: `craft\base\Plugin::getSettings()` (memoization), `craft\base\Plugin::setSettings()` (population), `craft\services\Plugins::createPlugin()` (merge).

## Records (ActiveRecord)

Records are thin — just the table mapping. No business logic, no validation:

```php
class MyEntity extends ActiveRecord
{
    public static function tableName(): string
    {
        return Table::MY_ENTITIES;
    }
}
```

### Record-to-Model Hydration Boundary

ActiveRecord does NOT coerce datetime columns into `DateTime` objects on read. Columns come back as raw SQL strings (e.g., `'2026-04-30 17:08:41'`). If your Model has typed `?DateTime` properties, direct assignment throws a `TypeError`:

```php
// WRONG — throws TypeError: Cannot assign string to property of type ?DateTime
$model->dateCreated = $record->dateCreated;

// RIGHT — wrap with DateTimeHelper
use craft\helpers\DateTimeHelper;

$model->dateCreated = DateTimeHelper::toDateTime($record->dateCreated) ?: null;
$model->dateUpdated = DateTimeHelper::toDateTime($record->dateUpdated) ?: null;
```

`DateTimeHelper::toDateTime()` handles strings, integers (unix timestamps), and `DateTime` instances. It returns `false` for invalid input — the `?: null` is needed when assigning to a `?DateTime` property.

This applies to every ActiveRecord-to-Model boundary, not just `dateCreated`/`dateUpdated`. Any custom timestamp column in your plugin tables needs the same wrapping. Build a `fromRecord()` static method on your Model to centralize the conversion:

```php
public static function fromRecord(MyEntityRecord $record): self
{
    $model = new self();
    $model->id = $record->id;
    $model->handle = $record->handle;
    $model->dateCreated = DateTimeHelper::toDateTime($record->dateCreated) ?: null;
    $model->dateUpdated = DateTimeHelper::toDateTime($record->dateUpdated) ?: null;
    $model->uid = $record->uid;
    return $model;
}
```

#### Those strings are naive UTC — never parse them with ambient-timezone functions

The raw column value isn't just "a string", it's a **naive UTC** string: no offset, no zone name. `Db::prepareDateForDb()` is what wrote it that way:

```php
// craft\helpers\Db::prepareDateForDb()
$date = clone $date;
$date->setTimezone(new DateTimeZone('UTC'));
return $date->format('Y-m-d H:i:s');
```

Meanwhile the PHP process default timezone is **not** UTC on most installs. Craft's init sets it from config: `ApplicationTrait::_setTimeZone()` resolves `generalConfig->timezone ?? projectConfig->get('system.timeZone')` and passes it to Yii's `setTimeZone()`, which is `date_default_timezone_set()`. So on a site configured for `America/Los_Angeles` or `Europe/Brussels`, the process default *is* that zone — Craft actively sets it.

Put those two facts together and any ambient-timezone parser misreads every value:

```php
// WRONG — parses a UTC string as if it were local time.
// Under America/Los_Angeles that's 7-8 hours off, in the wrong direction.
$changedSince = strtotime($record->dateUpdated);
$changedSince = new DateTime($record->dateUpdated);
```

The failure is quiet and direction-dependent: a "which records changed since X" comparison returns too many rows or too few depending on which side of the offset the data sits — and it is exactly correct on a UTC-configured machine, so it survives local testing and CI and breaks only on a non-UTC deployment.

Parse with an explicit UTC zone:

```php
use Carbon\Carbon;
use craft\helpers\DateTimeHelper;

// Preferred: toDateTime() treats a naive string as UTC by default.
$changedSince = DateTimeHelper::toDateTime($record->dateUpdated);

// In a service doing date arithmetic, Carbon with the zone named explicitly:
$changedSince = Carbon::createFromFormat('Y-m-d H:i:s', $record->dateUpdated, 'UTC');
```

`DateTimeHelper::toDateTime()` is the safe choice because of its signature — `toDateTime(mixed $value, bool $assumeSystemTimeZone = false, bool $setToSystemTimeZone = true)` — and this line inside it:

```php
$defaultTimeZone = ($assumeSystemTimeZone ? Craft::$app->getTimeZone() : 'UTC');
```

With the default `$assumeSystemTimeZone = false` a naive string is interpreted as UTC, which is precisely what the column holds. (`$setToSystemTimeZone = true` then shifts the result into the system zone for display; the *instant* is already right, so comparisons are unaffected.) Pass `true` for the second argument only when parsing something a human typed in their own timezone — never for a value that came out of the database.

**Rule of thumb:** every datetime crossing the DB boundary names its zone. `Db::prepareDateForDb()` on the way in, `DateTimeHelper::toDateTime()` or `Carbon::createFromFormat(..., 'UTC')` on the way out. `strtotime()` and bare `new DateTime()` have no place at that boundary.

This is the production-side twin of a testing rule: the `craft-pest` skill's `isolation.md` pins `date_default_timezone_set('UTC')` after app creation so test datetimes line up. That pin protects suites; explicit-UTC parsing protects production, where you don't control the process timezone and shouldn't try to.

### `Db::parseParam()` turns asterisks into wildcards

`Db::parseParam()` exists to translate Craft's element-query param syntax into SQL, and part of that syntax is asterisk-as-wildcard. For a string value with an `=` or `!=` operator it does:

```php
// craft\helpers\Db::parseParam()
$val = preg_replace('/^\*|(?<!\\\)\*$/', '%', $val, -1, $count);
$like = (bool)$count;
// ...
if ($like) {
    $operator = $operator === '=' ? 'like' : 'not like';
    $condition[] = [$operator, $column, static::escapeForLike($val), false];
```

A leading or trailing `*` becomes `%` and the comparison switches to `LIKE`. That is correct for query params and wrong for literal comparison.

Where it bites: any stored value that *legitimately* ends in an asterisk — URI patterns, route patterns, glob-style rules, wildcard redirects. A uniqueness check written as a query param quietly becomes a prefix match:

```php
// WRONG — 'blog/*' becomes LIKE 'blog/%', matching blog/hello, blog/2026/x, …
$exists = (new Query())
    ->from(Table::RULES)
    ->where(Db::parseParam('uriPattern', $pattern))
    ->exists();
```

So saving `blog/*` reports "already exists" because `blog/posts` is there. The false duplicate is the visible symptom; the invisible one is the reverse — a real duplicate passing because the wildcard matched something unexpected.

For literal comparison, bypass the helper:

```php
// Right — raw literal equality, no param-syntax interpretation
$exists = (new Query())
    ->from(Table::RULES)
    ->andWhere(['uriPattern' => $pattern])
    ->exists();
```

Escaping the asterisk (`\*`) also works — `parseParam()` unescapes `\*` back to a literal `*` after the wildcard pass — but it means every call site has to remember to escape. Prefer the raw `andWhere()` for stored-value comparisons and reserve `parseParam()` for actual user-supplied query criteria.

### Element-query param setters don't take Yii operator tuples

The sibling failure to the asterisk case above — same parser, opposite direction. There, a value you meant literally became a `LIKE`. Here, a condition you meant as `LIKE` becomes two literal values.

Element-query param setters route their argument through `Db::parseParam()`, which starts with `QueryParam::parse()`. That parser recognizes exactly three leading operators:

```php
// craft\db\QueryParam::extractOperator()
if (!in_array($firstVal, [self::AND, self::OR, self::NOT], true)) {
    return null;
}
```

`'like'` is not one of them. So this:

```php
// WRONG — silently matches nothing
Entry::find()->title(['like', $prefix . '%'])->all();
```

parses as *two literal values* with the default `OR` operator, and `Db::parseParam()` collapses an OR-list of `=` comparisons into an `IN`:

```sql
WHERE elements_sites.title IN ('like', 'fixture-%')
```

Zero rows, unless an entry is literally titled `like`. And note `%` is not a wildcard to `parseParam()` — it only translates `*` — so nothing rescues it.

**This fails silently in the worst possible way.** No exception, no warning, valid SQL, an empty result set that looks like "nothing matched." Anything built on such a query — a cleanup sweep, a maintenance job, a bulk re-save — becomes a permanent no-op that reports success. A real case had 11 call sites of a prefix-based cleanup sweep quietly matching nothing for weeks while the suite stayed green.

For `LIKE` and other operator conditions, drop to the raw Yii condition form against the underlying column:

```php
// Right — real LIKE against the column the param setter would have targeted
Entry::find()
    ->andWhere(['like', 'elements_sites.title', $prefix . '%', false])
    ->all();
```

Two details in that call:

- **`elements_sites.title`** is where the column lives in Craft 5 (`ElementQuery` maps it as `$this->_columnMap['title'] = 'elements_sites.title'`). Use the real column, not the param name.
- **The trailing `false`** maps to Yii's `escapingReplacements` (`LikeCondition::fromArrayDefinition()` assigns `$operands[2]`). Setting it `false` means "already escaped, don't touch" — which both preserves your own `%` and stops Yii from auto-wrapping the value in its own `%…%`. Omit it and Yii escapes your `%` into a literal and wraps the whole thing, giving you `LIKE '%fixture-\%%'`.

The general rule: **param setters take values, not conditions.** `->title('foo')`, `->title(['foo', 'bar'])`, `->title(['not', 'foo'])`, `->title('foo*')` — all fine, all value syntax. The moment you want a SQL operator, you've left the param API and want `andWhere()`.

**Verify the sweep matches.** Because the failure mode is an empty result rather than an error, a query like this deserves one assertion that it finds what it should — see the `craft-pest` skill's `craft-state.md` for the fixture-cleanup version of this.

### Serialized writers need bounded deadlock retry

A writer that must serialize — a hash-chained audit log, a sequence-numbered ledger, anything reading a "head" row and writing the next one — will hit MySQL deadlocks under concurrent processes. InnoDB detects the lock cycle, picks a victim, and rolls its transaction back with **SQLSTATE 40001 / error 1213 (`ER_LOCK_DEADLOCK`)**. This is expected, recoverable behavior, not a bug to eliminate.

Two failure modes compound:

- **No retry.** Under 12-way concurrency a chain writer without retry lost 9 of 12 writes to uncaught deadlocks.
- **A caller that swallows it.** `catch (Throwable) { continue; }` around the write turns each deadlock into **silent event loss** — no exception, no log line, nothing missing that anyone can see. For audit-class data that's the worst possible outcome.

A docblock claiming "writers serialize" is not an implementation. The retry has to be there:

```php
/**
 * Appends an entry, retrying on transient serialization failures.
 *
 * Each attempt re-reads the chain head inside a fresh transaction — the
 * previous attempt's read is invalid once its transaction rolled back.
 *
 * @param array $payload
 * @return int
 * @throws ChainWriteFailedException if every attempt deadlocks
 */
public function append(array $payload): int
{
    $attempts = 0;

    while (true) {
        $attempts++;
        $transaction = Craft::$app->getDb()->beginTransaction();

        try {
            // Re-read INSIDE this transaction — never reuse a head from a
            // rolled-back attempt.
            $head = $this->_lockChainHead();
            $id = $this->_insertLinked($head, $payload);

            $transaction->commit();

            return $id;
        } catch (Throwable $e) {
            $transaction->rollBack();

            if (!$this->_isSerializationFailure($e) || $attempts >= self::MAX_ATTEMPTS) {
                // Distinct exception type so callers can requeue rather than
                // treating this as "nothing to write".
                throw new ChainWriteFailedException(
                    "Chain append failed after {$attempts} attempts.", 0, $e,
                );
            }

            // Jittered backoff — fixed sleeps re-collide.
            usleep(random_int(1_000, 10_000) * $attempts);
        }
    }
}

/**
 * @param Throwable $e
 * @return bool
 */
private function _isSerializationFailure(Throwable $e): bool
{
    // 40001 is the SQLSTATE for serialization failure; MySQL's 1213 is the
    // driver-level deadlock code. Lock-wait timeout (1205) is also retryable.
    $sqlState = $e instanceof \yii\db\Exception ? ($e->errorInfo[0] ?? null) : null;
    $driverCode = $e instanceof \yii\db\Exception ? ($e->errorInfo[1] ?? null) : null;

    return $sqlState === '40001' || in_array($driverCode, [1213, 1205], true);
}
```

Three design points that matter more than the code:

1. **Re-read the head in a fresh transaction each attempt.** A retry that reuses the value read before the rollback writes a broken link.
2. **Throw a distinct exception when retries exhaust**, so callers can requeue the event instead of dropping it. `ChainWriteFailedException` vs a generic `Exception` is the difference between a queued retry and silent loss.
3. **Don't let callers catch `Throwable` and continue** around an audit write. If the write is important enough to hash-chain, it's important enough to fail loudly or requeue.

### Site Settings Model

For elements with per-site settings (URLs, templates):

```php
class Element_SiteSettings extends Model
{
    public ?int $siteId = null;
    public bool $hasUrls = false;
    public ?string $uriFormat = null;
    public ?string $template = null;

    protected function defineRules(): array
    {
        $rules = parent::defineRules();
        if ($this->hasUrls) {
            $rules[] = [['uriFormat'], 'required'];
        }
        return $rules;
    }
}
```

## Project Config

### Core Concept

Project config syncs configuration across environments via YAML. Entities that should sync (managed settings, field layouts) live in project config. Runtime data (element content, user preferences) does not.

**When manually editing `project.yaml`** (changing plugin editions, adding settings, resolving merge conflicts), you must update the `dateModified` unix timestamp at the top of the file. Without this, `craft up` won't detect the change. Either:
- Run `date +%s` and replace the `dateModified` value manually, or
- Run `ddev craft project-config/touch` which updates `dateModified` for you

This is the most common cause of "I changed the YAML but nothing happened."

### Settings belong in project config — including "operational" settings

Project config is Craft's **canonical settings store and the intended source of truth** for configuration. Plugin settings live there — and so do per-instance / per-entity *operational* settings that feel runtime-ish but are still configuration: alert thresholds, notification routing, workflow/status mappings, feature toggles, integration endpoints. These are author-defined values that should be identical across environments and version-controlled, so they go through project config (the `Save → Project Config → Handler → Database` flow above), **not** a DB-only column.

**The anti-pattern to reject:** "these are *operational* settings that need per-environment tuning, so keep them in the database and bypass project config." That inverts Craft's model. The correct workflow is the same as for sections and fields:

- **Set locally** (dev, `allowAdminChanges` on) → project config captures it to YAML → commit → deploy → `craft up` applies it.
- **Prod/UAT project config is read-only by design** (`allowAdminChanges => false`; see `deployment.md`). One direction: dev CP → YAML → Git → deploy. That read-only posture is the point, not an obstacle to route around.

If a value genuinely must differ per environment, that's what **environment variables** and `config/{handle}.php` overrides are for (the override is merged over the project-config row at plugin construction — see "Settings Lifecycle" above). Reach for that, not a DB-only escape hatch.

**The real risk to guard against is YAML↔DB divergence, not project config itself.** The failure mode: someone edits the setting directly in the database (or via a CP form on an environment where they shouldn't), the YAML doesn't reflect it, and the next `craft up` / `project-config/apply` re-applies YAML over the DB and **silently reverts** the change. The fix is discipline about keeping project config authoritative — change the value locally and deploy it — **not** moving the setting out of project config to dodge the sync.

**For code review:** flagging "thresholds/routing in project config cause cross-environment churn — make them DB-only" is a misconception to correct, not a valid finding. Project-config-managed settings don't churn when the workflow is followed (edit in dev, deploy); the churn only appears when someone edits config downstream of dev, which the read-only prod posture exists to prevent. Runtime *data* (element content, user preferences, logs, per-request state) still stays out of project config — the distinction is config vs. data, and operational settings are config.

### Register Paths

Register paths so Craft knows your plugin owns them:

```php
Craft::$app->getProjectConfig()
    ->onAdd(self::CONFIG_ITEMS_KEY . '.{uid}', [$this->getItems(), 'handleChangedItem'])
    ->onUpdate(self::CONFIG_ITEMS_KEY . '.{uid}', [$this->getItems(), 'handleChangedItem'])
    ->onRemove(self::CONFIG_ITEMS_KEY . '.{uid}', [$this->getItems(), 'handleDeletedItem']);
```

### Save → Project Config → Handler → Database

Validate model → fire before event → write to project config → handler writes to database:

```php
public function saveItem(MyEntity $item): bool
{
    $isNew = !$item->id;
    if ($isNew) {
        $item->uid = StringHelper::UUID();
    }

    if (!$item->validate()) {
        return false;
    }

    $this->trigger(self::EVENT_BEFORE_SAVE_ITEM, new MyEntityEvent([
        'entity' => $item,
        'isNew' => $isNew,
    ]));

    Craft::$app->getProjectConfig()->set(
        self::CONFIG_ITEMS_KEY . ".{$item->uid}",
        $item->getConfig(),
        "Save item \u201C{$item->name}\u201D"
    );

    return true;
}
```

### Handle Config Changes

The handler applies project config to the database. Skip validation — it was done before the config write:

```php
public function handleChangedItem(ConfigEvent $event): void
{
    $uid = $event->tokenMatches[0];
    $data = $event->newValue;

    $record = MyEntityRecord::findOne(['uid' => $uid])
        ?? new MyEntityRecord(['uid' => $uid]);

    $record->name = $data['name'];
    $record->handle = $data['handle'];
    $record->save(false);

    $this->_items = null; // Reset MemoizableArray
}
```

### Delete from Project Config

Clean up Craft elements BEFORE the project config removal — CASCADE on the FK won't touch the `elements` table:

```php
public function deleteItem(MyEntity $item): bool
{
    $this->_deleteItemElements($item);

    Craft::$app->getProjectConfig()->remove(
        self::CONFIG_ITEMS_KEY . ".{$item->uid}"
    );

    return true;
}
```

### Rebuild Handler

Without this, `project-config/rebuild` breaks your plugin:

```php
Event::on(ProjectConfig::class, ProjectConfig::EVENT_REBUILD,
    function(RebuildConfigEvent $event) {
        $event->config[self::CONFIG_ITEMS_KEY] = $this->_buildItemConfigs();
    }
);
```

### UID Rules

- UIDs are the cross-environment identifier. IDs are local to each database.
- Never hardcode UIDs. Always look them up or generate them.
- In migrations: check if project config already has the UID before generating a new one.
- `StringHelper::UUID()` generates v4 UUIDs.

### Creating or deleting sites at runtime

Sites are project-config-backed, and Craft assumes they change during a *request that ends*. Code that creates or deletes sites and then keeps running in the same process — importers, provisioning routines, multi-site setup commands, test fixtures — hits two caches that don't refresh themselves. Both fail silently. Verified against `craftcms/cms` 5.10.11.

#### `refreshSites()` does not invalidate the cache element queries actually read

`getIsMultiSite()` keeps **two** independent memos:

```php
// craft\base\ApplicationTrait
public function getIsMultiSite(bool $refresh = false, bool $withTrashed = false): bool
{
    if ($withTrashed) {
        if (!$refresh && isset($this->_isMultiSiteWithTrashed)) {
            return $this->_isMultiSiteWithTrashed;
        }
        // ... counts rows in the sites table
    }

    if (!$refresh && isset($this->_isMultiSite)) {
        return $this->_isMultiSite;
    }
    return $this->_isMultiSite = count($this->getSites()->getAllSites(true)) > 1;
}
```

`Sites::refreshSites()` refreshes only the first one:

```php
public function refreshSites(): void
{
    $this->_allSitesById = null;
    // ...
    Craft::$app->getIsMultiSite(true);      // ← $withTrashed defaults to FALSE
}
```

And `ElementQuery::beforePrepare()` gates its site filtering on the **other** one:

```php
if (Craft::$app->getIsMultiSite(false, true)) {
    $this->subQuery->andWhere(['elements_sites.siteId' => $this->siteId]);
}
```

So on a single-site install, `_isMultiSiteWithTrashed` memoizes `false` at first boot; code then creates a second site and calls `refreshSites()` like a good citizen; and **element queries still don't filter by site** for the rest of the process. Every query silently returns rows from all sites, with duplicate-looking results as the usual first symptom.

Force both variants after any runtime site change:

```php
Craft::$app->getSites()->refreshSites();          // site models + _isMultiSite
Craft::$app->getIsMultiSite(true, true);          // _isMultiSiteWithTrashed — the one queries read
```

The second call is the load-bearing one. It's easy to omit precisely because `refreshSites()` looks like it covers everything.

#### `deleteSite()`'s prune is invisible to already-memoized service caches

`Sites::deleteSite()` deletes sections that existed *only* on that site, removes the site's own project-config path, fires `EVENT_AFTER_DELETE_SITE`, and calls `refreshSites()`. An `ApplicationTrait` listener then prunes the site out of everything that referenced it:

```php
// Prune deleted sites from site settings
Event::on(Sites::class, Sites::EVENT_AFTER_DELETE_SITE, function(DeleteSiteEvent $event) {
    if (!Craft::$app->getProjectConfig()->getIsApplyingExternalChanges()) {
        $this->getRoutes()->handleDeletedSite($event);
        $this->getCategories()->pruneDeletedSite($event);     // removes categoryGroups.*.siteSettings.<uid>
        $this->getEntries()->pruneDeletedSite($event);        // removes sections.*.siteSettings.<uid>
    }
});
```

Those prunes write to **project config**. They do not null the `MemoizableArray` caches those services already built — `Entries::$_sections` and `Categories::$_groups` are private and only cleared by their own save/delete handlers. So within the same process, `getSectionByHandle()` and `getGroupByHandle()` keep returning models whose `siteSettings` still include the deleted site. Downstream code reads those stale models and behaves as though the prune never happened, which looks like phantom sites accumulating.

Note also the guard: when `getIsApplyingExternalChanges()` is true the entire prune is skipped by design (the incoming YAML is authoritative) — so a `project-config/apply` path prunes nothing here.

**Site deletion is a soft delete — FK CASCADE does not fire.** `craft\records\Site` uses `SoftDeleteTrait`, so `deleteSite()` sets `dateDeleted` on the `sites` row rather than removing it; the physical `DELETE` happens later in garbage collection (`Gc::run()` includes `Table::SITES` in its `hardDelete()` sweep — `src/services/Gc.php:171-173` in `craftcms/cms` 5.x), and only *then* do `ON DELETE CASCADE` constraints on plugin tables referencing `sites.id` fire. Consequences:

- A plugin whose per-site rows should vanish **immediately** on site deletion must listen to `EVENT_AFTER_DELETE_SITE` and clean up itself — relying on the FK means the rows linger until GC runs.
- A test that creates a site, saves per-site rows, calls `deleteSiteById()`, and asserts the rows are gone **fails** — the parent row still exists. To exercise the CASCADE itself, hard-delete directly (`Craft::$app->getDb()->createCommand()->delete(Table::SITES, ['id' => $siteId])->execute()`); to test the soft-delete contract, assert `dateDeleted` is set, the plugin rows are intact, and the event listener fired.

**Ordering matters when both a site and a category group are changing.** `Categories::saveGroup()` validates that the group's site settings cover every site that currently exists:

```php
$allSiteSettings = $group->getSiteSettings();
foreach (Craft::$app->getSites()->getAllSiteIds() as $siteId) {
    if (!isset($allSiteSettings[$siteId])) {
        throw new Exception('Tried to save a category group that is missing site settings');
    }
}
```

That's a thrown `Exception`, not a validation error you can inspect. So delete the site **first** — while the doomed site still exists, any `saveGroup()` call that omits it is rejected outright:

```php
// 1. Delete the site. Core prunes section/category-group siteSettings paths.
Craft::$app->getSites()->deleteSite($site);

// 2. Re-sync the caches core left stale.
Craft::$app->getSites()->refreshSites();
Craft::$app->getIsMultiSite(true, true);

// 3. Only now touch category groups — getAllSiteIds() no longer includes the
//    deleted site, so a group whose siteSettings omit it validates cleanly.
Craft::$app->getCategories()->saveGroup($group);
```

If you need the section/group models themselves to reflect the prune mid-process and no public refresh exists (`Entries` exposes `refreshEntryTypes()` but no section equivalent), re-read from project config rather than from the service, or defer the dependent work to a fresh request or queue job — which is what Craft's own request lifecycle would have given you.

## Yii2 Core Validators

Craft's `defineRules()` uses Yii2's validation system. These are the validators available in every `defineRules()` method, used by handle name (string) or class reference:

### Most Common

```php
protected function defineRules(): array
{
    $rules = parent::defineRules();

    // Required fields
    $rules[] = [['name', 'handle'], 'required'];

    // String length constraints
    $rules[] = [['name'], 'string', 'max' => 255];
    $rules[] = [['description'], 'string', 'max' => 1000];

    // Number with range
    $rules[] = [['batchSize'], 'integer', 'min' => 1, 'max' => 500];
    $rules[] = [['price'], 'number', 'min' => 0];

    // Boolean
    $rules[] = [['enabled'], 'boolean'];

    // Email and URL
    $rules[] = [['contactEmail'], 'email'];
    $rules[] = [['websiteUrl'], 'url'];

    // Value must be in a list
    $rules[] = [['status'], 'in', 'range' => ['draft', 'review', 'published']];

    // Regex match
    $rules[] = [['apiKey'], 'match', 'pattern' => '/^sk-[a-zA-Z0-9]{32}$/'];

    // Comparison
    $rules[] = [['endDate'], 'compare', 'compareAttribute' => 'startDate', 'operator' => '>=',
        'message' => 'End date must be after start date.'];

    return $rules;
}
```

### Conditional Validation

Use the `when` callback to apply rules conditionally:

```php
// Only validate apiKey when sync is enabled
$rules[] = [['apiKey'], 'required', 'when' => function($model) {
    return $model->enableSync;
}, 'whenClient' => "function(attribute, value) { return $('#enableSync').val(); }"];

// Only validate batchSize when it's not the default
$rules[] = [['batchSize'], 'integer', 'min' => 1, 'when' => function($model) {
    return $model->batchSize !== null;
}];
```

### Custom Error Messages

Override the default message on any validator:

```php
$rules[] = [['handle'], 'required', 'message' => Craft::t('my-plugin', '{attribute} cannot be blank.')];
$rules[] = [['batchSize'], 'integer', 'min' => 1, 'max' => 500,
    'tooSmall' => Craft::t('my-plugin', 'Batch size must be at least {min}.'),
    'tooBig' => Craft::t('my-plugin', 'Batch size cannot exceed {max}.'),
];
```

### Complete Validator Reference

| Validator | Type | Key Options | Purpose |
|-----------|------|-------------|---------|
| `'required'` | string | `message` | Field must not be empty |
| `'string'` | string | `min`, `max`, `length`, `encoding` | String length constraints |
| `'integer'` | string | `min`, `max`, `message` | Integer validation |
| `'number'` | string | `min`, `max`, `integerOnly` | Number (float or int) |
| `'boolean'` | string | `trueValue`, `falseValue`, `strict` | Boolean validation |
| `'email'` | string | `allowName`, `checkDNS` | Email format |
| `'url'` | string | `validSchemes`, `defaultScheme` | URL format |
| `'in'` | string | `range`, `strict`, `not` | Value in allowed list |
| `'match'` | string | `pattern`, `not` | Regex match |
| `'compare'` | string | `compareAttribute`, `compareValue`, `operator` | Cross-field comparison |
| `'date'` | string | `format`, `min`, `max` | Date format |
| `'each'` | string | `rule` | Apply a rule to each element in an array |
| `'default'` | string | `value` | Set default value (not a validation, runs before other rules) |
| `'filter'` | string | `filter` | Transform value (trim, strip_tags, custom callable) |
| `'safe'` | string | — | Mark attribute as safe for mass assignment (see `elements.md` — Attributes, Field Values, and Mass Assignment) |
| `'trim'` | string | — | Trim whitespace |
| `'unique'` | string | `targetClass`, `targetAttribute` | Unique in DB (use Craft's UniqueValidator for elements) |

### Craft-Specific Validators

| Validator | Class | Purpose |
|-----------|-------|---------|
| `HandleValidator` | `craft\validators\HandleValidator` | Validates handles (a-zA-Z0-9_, checks reserved words) |
| `UniqueValidator` | `craft\validators\UniqueValidator` | Unique check against records (extends Yii's) |
| `DateTimeValidator` | `craft\validators\DateTimeValidator` | Validates DateTime values |
| `ColorValidator` | `craft\validators\ColorValidator` | Validates hex color values |
| `UrlValidator` | `craft\validators\UrlValidator` | Validates URLs (extends Yii's, supports aliases) |
| `StringValidator` | `craft\validators\StringValidator` | Validates strings (extends Yii's) |
| `SlugValidator` | `craft\validators\SlugValidator` | Validates slug format |
| `LanguageValidator` | `craft\validators\LanguageValidator` | Validates language tags |

## Custom Validators

When Yii's built-in validators and Craft's validators (`HandleValidator`, `UniqueValidator`, `DateTimeValidator`) aren't enough, create custom validators for domain-specific rules.

### Inline Validator (Quick, One-Off)

For validation logic used in a single model, use an inline validator in `defineRules()`:

```php
protected function defineRules(): array
{
    $rules = parent::defineRules();
    $rules[] = [['handle'], function($attribute) {
        if (str_starts_with($this->$attribute, '_')) {
            $this->addError($attribute, Craft::t('my-plugin', 'Handle cannot start with an underscore.'));
        }
    }];
    return $rules;
}
```

### Standalone Validator Class

For reusable validation logic, extend `yii\validators\Validator`. Place in `src/validators/`:

```php
namespace myplugin\validators;

use Craft;
use yii\validators\Validator;

class PwnedPasswordValidator extends Validator
{
    /**
     * Validates a single value (standalone usage).
     *
     * @return array|null [error message, params] or null if valid
     */
    public function validateValue($value): ?array
    {
        if (MyPlugin::$plugin->getPasswords()->isPwned($value)) {
            return [
                Craft::t('my-plugin', 'This password has been compromised in a data breach.'),
                [],
            ];
        }

        return null;
    }

    /**
     * Validates a model attribute (when used in defineRules).
     */
    public function validateAttribute($model, $attribute): void
    {
        $result = $this->validateValue($model->$attribute);
        if ($result !== null) {
            $this->addError($model, $attribute, $result[0], $result[1]);
        }
    }
}
```

### Using Custom Validators in defineRules()

```php
protected function defineRules(): array
{
    $rules = parent::defineRules();
    $rules[] = [['newPassword'], PwnedPasswordValidator::class];
    $rules[] = [['handle'], UniqueValidator::class, 'targetClass' => MyEntityRecord::class];
    return $rules;
}
```

### Craft's Built-In Validators

Before creating custom validators, check if Craft already provides one. Common ones:

- `craft\validators\HandleValidator` — validates handle format and reserved words
- `craft\validators\UniqueValidator` — unique across a record class (wraps Yii's with Craft conventions)
- `craft\validators\DateTimeValidator` — validates DateTime objects
- `craft\validators\ColorValidator` — validates hex color codes
- `craft\validators\UrlValidator` — validates URLs with Craft's alias support
- `craft\validators\StringValidator` — extends Yii's with trim and encoding options

Keep validation logic in the validator — call service methods for expensive checks (API calls, database lookups) but don't put business logic in the validator itself.

## Plugin Editions

Plugins can offer multiple editions (e.g., lite/standard/pro) with different feature sets and pricing tiers.

### Declaring Editions

Override `static editions()` to return available editions from lowest to highest:

```php
public static function editions(): array
{
    return [
        'lite',
        'standard',
        'pro',
    ];
}
```

The default is `['standard']` (single edition). The order matters — it defines the hierarchy for comparison operators.

### Checking the Active Edition

Use `$plugin->is()` to gate features by edition:

```php
// Exact match
if (MyPlugin::$plugin->is('pro')) {
    // Pro-only feature
}

// Comparison operators
if (MyPlugin::$plugin->is('standard', '>=')) {
    // Standard or higher
}

if (MyPlugin::$plugin->is('lite', '>')) {
    // Above lite (standard or pro)
}
```

Supported operators: `<`, `<=`, `>`, `>=`, `==` (alias `=`), `!=` (alias `<>`).

### Feature Gating Pattern

Conditionally register features based on edition in `init()`:

```php
public function init(): void
{
    parent::init();

    // Core features available in all editions
    $this->_registerCoreFeatures();

    // Standard+ features
    if ($this->is('lite', '>')) {
        $this->_registerAdvancedFields();
    }

    // Pro-only features
    if ($this->is('pro')) {
        $this->_registerGraphqlTypes();
        $this->_registerWebhookController();
    }
}
```

Common patterns:
- **Lite (free)** — basic functionality, limited element types or field types
- **Standard** — full feature set for most users
- **Pro** — advanced features: GraphQL, API endpoints, bulk operations, advanced reporting

### Requiring a CMS Edition

Set `$minCmsEdition` to require a minimum Craft CMS edition:

```php
use craft\enums\CmsEdition;

class MyPlugin extends Plugin
{
    public CmsEdition $minCmsEdition = CmsEdition::Pro;
}
```

Available: `CmsEdition::Solo`, `CmsEdition::Team`, `CmsEdition::Pro`, `CmsEdition::Enterprise` (5.3.0+).

Use this when the plugin depends on CMS features only available in higher editions (e.g., user groups for permission-scoped content). For what each CMS edition unlocks (user groups, permissions, public registration), see the `craft-content-modeling` skill's `references/users-and-permissions.md`.

### Switching Editions for Local Testing

To test different plugin editions in a local dev environment:

1. **Change the edition** in `cms/config/project/project.yaml` — find the plugin's entry under `plugins` and set the `edition` key
2. **Update `dateModified`** at the top of `project.yaml` — run `date +%s` and replace the value. Without this, `craft up` won't detect the change.
3. **Apply the config**: `ddev craft up`
4. **Clear compiled templates**: `ddev craft clear-caches/compiled-templates` — Twig templates are compiled and cached, so edition-dependent conditionals (`{% if plugin.is('pro') %}`) won't re-evaluate until the cache is cleared

All four steps are required. Skipping step 2 means `craft up` silently ignores the change. Skipping step 4 means Twig renders stale compiled templates with the old edition check.

**Do NOT use `app.php` `pluginConfigs` to set editions.** That's for component configuration overrides, not edition management. The project config YAML is the single source of truth for plugin editions.

### Edition Helper Methods

Provide convenience getters for edition checks. Always delegate to `$this->is()` — never hardcode return values:

```php
public const EDITION_LITE = 'lite';
public const EDITION_PRO = 'pro';
public const EDITION_ENTERPRISE = 'enterprise';

public function getIsLite(): bool
{
    return $this->is(self::EDITION_LITE);
}

public function getIsPro(): bool
{
    return $this->is(self::EDITION_PRO);
}

public function getIsEnterprise(): bool
{
    return $this->is(self::EDITION_ENTERPRISE);
}
```

These are accessible as properties via Yii's magic getters: `MyPlugin::$plugin->isPro`, `MyPlugin::$plugin->isEnterprise`. Use edition constants as the source of truth — never `return true` or `return false` directly.

### Edition in Migrations

Migrations run regardless of the active edition. Settings saved in project config persist across edition changes — downgrading from Pro to Lite doesn't delete Pro settings. Guard feature access in `init()` and controllers, not in migrations or project config handlers.

### Edition in Templates

Check edition in CP templates to show/hide features:

```twig
{% if plugin('my-plugin').is('pro') %}
    {# Pro-only UI #}
{% endif %}
```

### Licensing

Editions map to Plugin Store pricing tiers. Each edition can have its own price (or be free). Users purchase an edition and can upgrade — downgrades require contacting the developer. The Plugin Store handles license validation; `$this->edition` reflects the active licensed edition.

## Front-End Output From Plugins

When a plugin renders into a *site's* front end, two patterns keep the integration robust. Both are consumed in Twig; the full front-end guidance (bundle structure, the Twig usage, progressive enhancement) lives in the craft-site skill's `example-templates.md`. This section covers the plugin-side pieces.

### Example templates: ship a copyable bundle, not fragments

Following the Craft Commerce example-templates model, a plugin with a front end ships a **complete, self-contained bundle** the integrator copies into their `templates/` — never bare body fragments. The bundle owns a canonical folder name (e.g. `example-templates/members/` → `templates/members/`), ships its own `_private/layouts/` HTML shell (skip link, nav include, flash notices rendered once, an `extraHead` block hook), and every page `{% extends %}` that shell filling a `{% block main %}`.

The plugin-side deliverable is an **install console command** (Commerce-style: `<handle>/example-templates`) that:

- copies the bundle into `templates/`;
- prompts for a destination folder name (default: the canonical name);
- rewrites the bundle's internal root-relative `{% extends %}`/`{% include %}` references when the folder is renamed (a mechanical prefix find-and-replace — which is why the bundle uses fixed root-relative paths, not a prefix-variable convention);
- refuses to overwrite an existing target folder unless `--overwrite` is passed.

The command class goes in `src/console/controllers/`. For option parsing, prompts, `stdout()` output, and exit codes, see `console-commands.md`.

### Render builders: fluent `BaseTag` with a config-array constructor

For a widget the plugin renders into a page, expose a fluent builder — `craft.<handle>.<thing>({...}).render()` — rather than a raw plugin-template include. Modeled on Password Policy's fluent tag:

- A `BaseTag` subclass with a **config-array constructor whose keys MUST map to chainable setters**. `new OtpInput(['digits' => 6])` and `->digits(6)` take the same path. **An unknown key throws** — a mistyped option (`digitz`) fails loudly at render instead of being silently dropped.
- **Validate option keys against a real allowlist, not `method_exists()`.** A `method_exists($this, $key)` guard accepts every public method as an "option" — `['render' => …]` passes the guard and then dies with `ArgumentCountError` deep in the call instead of "Unknown option: render". Keep an explicit list of settable option names (or derive it once from the settable properties) and reject everything else by name.
- **Attribute setters must merge `class`, never replace it.** A plain `array_merge($defaults, $callerAttrs)` replaces the `class` key wholesale, so a caller passing `attrs: {class: 'my-input'}` silently deletes every class the widget's own CSS and JS depend on. Merge the class *lists* (Craft's `Html::normalizeTagAttributes()` + merging the `class` arrays, or `Html::modifyTagAttributes()`), and offer an explicit `resetClass: true` option for callers who genuinely want to start clean. If the docs say "merges", the code must actually merge — a shipped plugin was found doing the replacing version while its README claimed merging.
- **Guard the attributes your own JS depends on.** If the rendered markup carries `data-` hooks a progressive-enhancement script reads, a caller passing `inputAttrs: {data: {…}}` wholesale can clobber them — the widget then renders fine and silently never enhances. Either merge `data` sub-keys the same way as `class`, or reserve the hook attributes and reject caller attempts to set them. (Those hooks are public API — see [The JS-to-markup contract is public API](#the-js-to-markup-contract-is-public-api).)
- A public **`render(): \Twig\Markup`** wrapping a private `_renderHtml(): string`. Returning `\Twig\Markup` marks the HTML pre-escaped so Twig doesn't re-escape it.
- Consumers must call `{{ tag.render() }}`, **never `{{ tag }}`** — a bare print goes through `__toString()`, which Twig auto-escapes, rendering the HTML as visible tags. `__toString()` is a debugging/logging fallback only. This is the double-escape trap documented in full in `events.md`.
- **Lazy client-asset registration** — register the widget's vanilla-JS + neutral-CSS asset bundle the first time it renders on a page, not eagerly at bootstrap, so pages that don't use it pay nothing. For asset-bundle registration and the Vite bridge, see `plugin-vite.md`.

The rendered control must be **progressively enhanced**: the server emits a fully functional plain control and JS upgrades it. The craft-site `example-templates.md` walks through the concrete discipline (the segmented-OTP carrier-input example) that front-end reviewers should apply.

### Plugin-registered CSS loads after the site's stylesheet

Craft compiles site templates with a node visitor that inserts the `head()` event tag **immediately before `</head>`** when the template doesn't call it explicitly (`craft\web\twig\nodevisitors\EventTagAdder`, `src/web/twig/nodevisitors/EventTagAdder.php:93-97` in `craftcms/cms` 5.x). Registered CSS files render at that marker — so a plugin's `<link>` lands **after** the site's own hardcoded stylesheet link. At equal specificity, the site's rule **loses on source order**, and "just override it in your CSS" is wrong advice: the integrator's override has to win on specificity, not on position.

Two design escapes, both worth shipping:

- **Wrap cosmetic rules in `@layer`.** Any *unlayered* site rule beats a layered plugin rule regardless of source order or specificity — the cleanest fix, and it needs no opt-in from the integrator. But **keep behaviour-critical rules out of the layer**: a `display: none` that hides the raw carrier input once JS has enhanced the widget must stay unlayered, because a browser without cascade-layer support drops the whole `@layer` block and would show both the raw input and the enhanced widget.
- **Offer a suppression switch** — a `renderCss: false` plugin setting plus a per-render override — so a developer can own the styling entirely. Formie is the reference design (verified in `verbb/formie` 3.1.21): per-render `renderCss`/`renderJs` options (`src/services/Rendering.php:105-106`), per-template lightswitches (`outputCssLayout`/`outputCssTheme`/`outputJsBase`/`outputJsTheme`, `src/models/FormTemplate.php:26-29`), and an `outputJsLocation` of `MANUAL` that skips auto-registration entirely (`Rendering.php:116-122`) for integrators who want to call `renderCss()`/`renderJs()` themselves. Three independent tiers — global setting, template config, per-render option — is the full shape; even just the first and last cover most needs.

### The JS-to-markup contract is public API

If a plugin ships front-end JS that always loads **and** supports user-supplied templates, the DOM hooks that JS reads — class names, `data-` attributes, element structure, input naming — **are public API and must be documented as such**. Otherwise a hand-written template renders correctly, looks right, and silently doesn't work: the JS finds none of its hooks and never enhances, with no error anywhere.

The robust shape:

- **PHP resolves the hook values and hands them to JS via `data-` attributes** on the rendered root (selector names, endpoint URLs, option flags) — so the plugin's own rendered markup and the JS always agree, even when settings change the values.
- **The JS keeps the hardcoded literals only as `||` fallbacks** (`el.dataset.inputSelector || '.otp-input'`), so minimal hand-written markup that uses the documented defaults still functions without reproducing every attribute.
- **The docs state the contract explicitly as "what your template must provide"**: required classes, required `data-` attributes, required input names, required nesting. Treat a change to any of them as a breaking change, because for template-owning integrators it is one.

When a plugin persists IP addresses — or comparable personal data (email, precise location, device identifiers) — it takes on a data-handling responsibility, and integrators inherit it. Ship a **privacy story** so the plugin is deployable in privacy-sensitive contexts without the integrator reverse-engineering what it stores.

This is **data-handling discipline, not legal advice.** Frame everything region-neutrally: describe *what* is stored and *how* it can be minimized, and point integrators at the fact that a lawful-basis / justification requirement may apply in their jurisdiction — do not assert any single jurisdiction's rules as universal.

### Ship a `docs/privacy.md`

Include four things:

1. **Data inventory** — what personal data the plugin stores, in which table/column, and why it needs it. Be specific: "the full client IP in `myplugin_events.ipAddress`, used to rate-limit submissions and derive city-level analytics."
2. **Retention statement** — how long records are kept and what prunes them (a console command, a queue job, a `purgeAfterDays` setting). "Stored indefinitely" is a valid statement only if it's a deliberate, documented choice.
3. **Lawful-basis / justification note** — stated generically. Explain that an integrator may need to record a lawful basis or justification for storing this data under whatever regime applies to them, and that specific regulations are *examples* they may need to consult — e.g. the EU GDPR's Recital 49 treats certain security-related processing as a legitimate interest — rather than a universal rule the plugin asserts on their behalf.
4. **Suggested privacy-policy wording** — a short, copy-pasteable paragraph the integrator can adapt into their own site's privacy policy, describing what the plugin collects and why.

### Offer an `anonymizeIp` lightswitch

Provide an optional setting (a lightswitch in the settings model) that minimizes stored addresses at write time:

- **IPv4:** zero the final octet — `203.0.113.47` → `203.0.113.0`.
- **IPv6:** keep the `/48` prefix, zero the rest — retains routing-level locality without the host identity.
- **Fail closed:** on unparseable input, store `null`, never the raw value. A malformed address must not slip through un-anonymized.
- **Apply at the storage boundary, AFTER any geo lookup.** Do the city-level geo derivation on the full address first, then truncate before persisting. Truncating earlier throws away location precision the plugin legitimately needs; truncating at the storage boundary keeps the derived data while discarding the identifying address.

```php
/**
 * Anonymizes an IP for storage: zeroes the final IPv4 octet or keeps the
 * IPv6 /48. Returns null on unparseable input (fail closed).
 *
 * Call this AFTER any geo lookup — geo derivation needs the full address.
 */
public function anonymizeIp(?string $ip): ?string
{
    if ($ip === null || filter_var($ip, FILTER_VALIDATE_IP) === false) {
        return null;
    }

    if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) !== false) {
        // Zero the final octet: 203.0.113.47 -> 203.0.113.0
        $packed = inet_pton($ip);
        $packed[3] = "\0";
        return inet_ntop($packed);
    }

    // IPv6: keep the /48, zero the remaining 80 bits.
    $packed = inet_pton($ip);
    for ($i = 6; $i < 16; $i++) {
        $packed[$i] = "\0";
    }
    return inet_ntop($packed);
}
```

Then apply it where the record is populated, gated on the setting:

```php
$record->ipAddress = $this->getSettings()->anonymizeIp
    ? $this->anonymizeIp($clientIp)
    : $clientIp;
```

If the data is also surfaced to the site's visitors (a public activity log, a "your recent sign-ins" panel), mirror this note into the craft-site front-end guidance so the template layer doesn't re-expose an address the storage layer took care to minimize.
