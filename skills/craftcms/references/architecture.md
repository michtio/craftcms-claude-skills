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

## Table of Contents

- [Scaffolding](#scaffolding)
- [Services](#services)
- [Models](#models)
- [Records (ActiveRecord)](#records-activerecord)
- [Project Config](#project-config)
- [Custom Validators](#custom-validators)

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
