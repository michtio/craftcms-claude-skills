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
- Assigning ActiveRecord datetime columns directly to typed Model properties — ActiveRecord returns raw SQL strings, not `DateTime` objects. Use `DateTimeHelper::toDateTime($record->dateCreated) ?: null`. See [Record-to-Model Hydration Boundary](#record-to-model-hydration-boundary).

## Table of Contents

- [Scaffolding](#scaffolding)
- [Services](#services)
- [Models](#models)
- [Records (ActiveRecord)](#records-activerecord)
- [Project Config](#project-config)
- [Yii2 Core Validators](#yii2-core-validators)
- [Custom Validators](#custom-validators)
- [Plugin Editions](#plugin-editions) — declaring, checking, feature gating, edition switching, helper methods, migrations

## Scaffolding

```bash
ddev craft make service --with-docblocks
ddev craft make model --with-docblocks
ddev craft make record --with-docblocks
```

Then customize: add section headers, `@author`, `@since`, `@throws` chains.

## Services

### Registration via ServicesTrait

```php
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
        return $this->get('items');
    }
}
```

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
