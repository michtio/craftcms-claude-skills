# Custom Field Types — Build Pattern

Complete reference for building custom field types in Craft CMS 5: class structure, static configuration, value lifecycle, settings, input HTML, validation, search keywords, GraphQL integration, and relation fields. For using built-in field types and field layout elements, see `fields.md`. For registering field types via events, see `events.md`.

## Documentation

- Field types: https://craftcms.com/docs/5.x/extend/field-types.html
- Generator: https://craftcms.com/docs/5.x/extend/generator.html

## Common Pitfalls

- Overriding `getContentColumnType()` instead of `dbType()` — the legacy instance method still works, but the Craft 5 static `dbType()` takes precedence. Use `dbType()`.
- Forgetting `parent::defineRules()` in field settings validation — drops validation for `handle`, `name`, and other base properties.
- Not calling `parent::afterElementSave()` — base class handles relation storage, delta writes, and propagation. Skipping it silently breaks multi-site and delta saves.
- Returning a query from `normalizeValue()` without implementing `EagerLoadingFieldInterface` — causes N+1 queries when multiple elements are loaded. Relation fields must be eager-loadable.
- Implementing `getContentGqlType()` without `getContentGqlMutationArgumentType()` — makes the field read-only in GraphQL mutations.
- Setting `searchable` on the field trait without implementing `getSearchKeywords()` — indexed keywords will be empty, making the field unsearchable despite the flag.

## Contents

- [Scaffold](#scaffold)
- [Class Hierarchy](#class-hierarchy)
- [Static Configuration Methods](#static-configuration-methods)
- [Value Lifecycle](#value-lifecycle)
- [Settings](#settings)
- [Input HTML](#input-html)
- [Validation](#validation)
- [Search Keywords](#search-keywords)
- [GraphQL Integration](#graphql-integration)
- [Preview and Static HTML](#preview-and-static-html)
- [Element Lifecycle Hooks](#element-lifecycle-hooks)
- [Relation Fields](#relation-fields)
- [Registration](#registration)
- [Key FieldTrait Properties](#key-fieldtrait-properties)

## Scaffold

```bash
ddev craft make field-type
```

Generates a field type class with stubs for: `displayName()`, `defineRules()`, `getSettingsHtml()`, `dbType()`, `normalizeValue()`, `inputHtml()`, `getElementValidationRules()`, `getSearchKeywords()`, `getElementConditionRuleType()`.

## Class Hierarchy

```
craft\base\Field
  extends SavableComponent
    extends ConfigurableComponent
      extends Component (craft)
        extends Model (yii)
```

**Optional interfaces** for enhanced behavior:

| Interface | Enables |
|-----------|---------|
| `PreviewableFieldInterface` | `getPreviewHtml()` for element index tables/cards |
| `SortableFieldInterface` | `getSortOption()` for index sorting |
| `InlineEditableFieldInterface` | Inline editing in element indexes |
| `EagerLoadingFieldInterface` | Eager-loading support for query fields |
| `ThumbableFieldInterface` | Thumbnail in element cards |
| `MergeableFieldInterface` | Merge support for drafts |

## Static Configuration Methods

| Method | Return | Default | Purpose |
|--------|--------|---------|---------|
| `displayName()` | `string` | Class name | Name shown in the field type picker |
| `icon()` | `string` | `'i-cursor'` | SVG icon name |
| `phpType()` | `string` | `'mixed'` | PHP type hint for IDE autocompletion on `entry.myField` |
| `dbType()` | `string\|array\|null` | `Schema::TYPE_TEXT` | DB column type. `null` = self-managed storage |
| `isMultiInstance()` | `bool` | `dbType() !== null` | Whether multiple instances can exist in one field layout |
| `supportedTranslationMethods()` | `array` | All 5 when `dbType()` is non-null | Which translation methods the field supports |
| `queryCondition()` | `array\|ExpressionInterface\|false\|null` | Parent impl | Custom query filtering for `entry.myField(value)` |
| `isRequirable()` | `bool` | `true` | Whether the field can be marked required |
| `isSelectable()` | `bool` | `true` | Whether it appears in the field type selector |

### dbType() options

```php
// Simple column
public static function dbType(): string
{
    return Schema::TYPE_TEXT;
}

// Specific size
public static function dbType(): string
{
    return Schema::TYPE_STRING . '(255)';
}

// Multi-column
public static function dbType(): array
{
    return [
        'date' => Schema::TYPE_DATETIME,
        'timezone' => Schema::TYPE_STRING,
    ];
}

// Self-managed storage (relation fields, external APIs)
public static function dbType(): null
{
    return null;
}
```

Common types: `TYPE_TEXT`, `TYPE_STRING`, `TYPE_INTEGER`, `TYPE_BOOLEAN`, `TYPE_FLOAT`, `TYPE_JSON`, `TYPE_DATETIME`.

## Value Lifecycle

Values flow through these methods in order:

```
POST data / DB row
       │
       ▼
normalizeValueFromRequest()  ← POST data path
       │                       (delegates to normalizeValue() by default)
       ▼
normalizeValue()             ← DB data path
       │                       (transforms raw value to working PHP object)
       ▼
  Working PHP value          ← available as entry.myField in Twig
       │
       ▼
serializeValue()             ← converts back for DB storage
       │                       (handles Serializable, Arrayable, DateTime)
       ▼
serializeValueForDb()        ← final DB-bound value
```

### normalizeValue()

```php
public function normalizeValue(mixed $value, ?ElementInterface $element = null): mixed
{
    if ($value instanceof MyValueObject) {
        return $value;
    }

    if (is_string($value)) {
        return new MyValueObject(Json::decodeIfJson($value));
    }

    if (is_array($value)) {
        return new MyValueObject($value);
    }

    return new MyValueObject();
}
```

### normalizeValueFromRequest()

Override separately when POST data needs different handling than DB data:

```php
public function normalizeValueFromRequest(mixed $value, ?ElementInterface $element = null): mixed
{
    // POST data comes as flat array from form inputs
    if (is_array($value) && isset($value['date'], $value['timezone'])) {
        return new MyValueObject(
            DateTimeHelper::toDateTime($value['date']),
            $value['timezone']
        );
    }

    return parent::normalizeValueFromRequest($value, $element);
}
```

### serializeValue()

```php
public function serializeValue(mixed $value, ?ElementInterface $element = null): mixed
{
    if ($value instanceof MyValueObject) {
        return $value->toArray();
    }

    return parent::serializeValue($value, $element);
}
```

## Settings

### Declaring settings

Public properties on the field class are settings:

```php
public int $maxLength = 255;
public bool $multiline = false;
public string $placeholder = '';
```

### Validating settings

```php
protected function defineRules(): array
{
    $rules = parent::defineRules(); // Always call parent

    $rules[] = [['maxLength'], 'integer', 'min' => 1, 'max' => 65535];
    $rules[] = [['placeholder'], 'string', 'max' => 255];

    return $rules;
}
```

### Settings UI

```php
public function getSettingsHtml(): ?string
{
    return Craft::$app->getView()->renderTemplate(
        'my-plugin/fields/_settings',
        ['field' => $this]
    );
}
```

## Input HTML

```php
protected function inputHtml(mixed $value, ?ElementInterface $element, bool $inline): ?string
{
    // $value is already normalized
    // $element is null for default-value scenarios
    // $inline is true for inline editing in element indexes

    return Craft::$app->getView()->renderTemplate(
        'my-plugin/fields/_input',
        [
            'field' => $this,
            'value' => $value,
            'element' => $element,
        ]
    );
}
```

Set `useFieldset()` to return `true` to wrap input in a `<fieldset>` with label (instead of `<div>` with `<label>`).

## Validation

```php
public function getElementValidationRules(): array
{
    $rules = [];

    if ($this->maxLength) {
        $rules[] = ['string', 'max' => $this->maxLength];
    }

    // Custom inline validator
    $rules[] = [
        function(ElementInterface $element) {
            $value = $element->getFieldValue($this->handle);
            if ($value && !$this->_isValid($value)) {
                $element->addError(
                    $this->handle,
                    Craft::t('my-plugin', '{attribute} is invalid.', [
                        'attribute' => $this->name,
                    ])
                );
            }
        },
    ];

    return $rules;
}
```

### isValueEmpty()

Override to define what "empty" means for required validation:

```php
public function isValueEmpty(mixed $value, ElementInterface $element): bool
{
    if ($value instanceof MyValueObject) {
        return $value->isEmpty();
    }

    return parent::isValueEmpty($value, $element);
}
```

## Search Keywords

```php
public function getSearchKeywords(mixed $value, ElementInterface $element): string
{
    if ($value instanceof MyValueObject) {
        return $value->getSearchableText();
    }

    return '';
}
```

The field must be marked searchable in the field layout (`searchable` property on the field layout element) for keywords to be indexed.

## GraphQL Integration

All three are optional. Only `getContentGqlType()` is needed for the field to appear in GraphQL queries; the mutation and query-argument methods enable write and filter support respectively.

```php
use GraphQL\Type\Definition\Type;

// Query return type
public function getContentGqlType(): Type|array
{
    return MyFieldTypeType::getType();
}

// Mutation input type
public function getContentGqlMutationArgumentType(): Type|array
{
    return Type::string();
}

// Query argument type (for filtering)
public function getContentGqlQueryArgumentType(): Type|array
{
    return [
        'name' => $this->handle,
        'type' => Type::listOf(QueryArgument::getType()),
    ];
}

// Control visibility per GQL schema
public function includeInGqlSchema(GqlSchema $schema): bool
{
    return true;
}
```

## Preview and Static HTML

```php
// Compact preview for element index tables/cards
// Requires PreviewableFieldInterface
public function getPreviewHtml(mixed $value, ElementInterface $element): string
{
    if (!$value) {
        return '';
    }

    return Html::encode((string)$value);
}

// Read-only rendering for disabled contexts
public function getStaticHtml(mixed $value, ElementInterface $element): string
{
    return Html::tag('div', Html::encode((string)$value), [
        'class' => 'text',
    ]);
}
```

## Element Lifecycle Hooks

Methods called during element save/delete lifecycle. Always call `parent::` — base implementations handle relation storage, delta writes, and propagation.

| Method | Returns | When |
|--------|---------|------|
| `beforeElementSave($element, $isNew)` | `bool` | Before save. Return `false` to cancel. |
| `afterElementSave($element, $isNew)` | `void` | After save. Most common hook. |
| `afterElementPropagate($element, $isNew)` | `void` | After multi-site propagation. |
| `beforeElementDelete($element)` | `bool` | Before delete. Return `false` to prevent. |
| `afterElementDelete($element)` | `void` | After delete. Clean up resources. |
| `beforeElementDeleteForSite($element)` | `bool` | Per-site deletion. |
| `afterElementDeleteForSite($element)` | `void` | Per-site cleanup. |
| `beforeElementRestore($element)` | `bool` | Before soft-delete restore. |
| `afterElementRestore($element)` | `void` | After restore. Re-establish connections. |

### Draft-aware side effects

```php
public function afterElementSave(ElementInterface $element, bool $isNew): void
{
    parent::afterElementSave($element, $isNew);

    // Skip side effects for drafts and revisions
    if ($element->getIsDraft() || $element->getIsRevision()) {
        return;
    }

    // Trigger sync, webhook, etc.
    MyPlugin::getInstance()->getSyncService()->syncField($element, $this);
}
```

## Relation Fields

For fields that select related elements, extend `craft\fields\BaseRelationField` instead of `Field`:

```php
class MyRelationField extends BaseRelationField
{
    public static function displayName(): string
    {
        return Craft::t('my-plugin', 'My Elements');
    }

    public static function elementType(): string
    {
        return MyElement::class; // The only required abstract method
    }
}
```

### How BaseRelationField differs from Field

| Aspect | Field | BaseRelationField |
|--------|-------|-------------------|
| `dbType()` | Column in content table | Returns `null` (self-managed) |
| Storage | Content table column | `{{%relations}}` table |
| `normalizeValue()` | Returns scalar/object | Returns `ElementQuery` (lazy-loaded) |
| `serializeValue()` | Returns DB-storable value | Returns element ID array |
| `isMultiInstance()` | Usually `true` | `false` (single instance per layout) |
| Eager loading | Manual | Built-in via `EagerLoadingFieldInterface` |

### Config properties on BaseRelationField

| Property | Type | Default | Purpose |
|----------|------|---------|---------|
| `minRelations` | `?int` | `null` | Minimum required related elements |
| `maxRelations` | `?int` | `null` | Maximum allowed related elements |
| `allowSelfRelations` | `bool` | `false` | Allow relating to the source element |
| `maintainHierarchy` | `bool` | `false` | Preserve structure ordering |
| `targetSiteId` | `?string` | `null` | Restrict to specific site |
| `viewMode` | `string` | `'list'` | Display mode: `'list'`, `'large'`, `'cards'` |

## Registration

```php
use craft\events\RegisterComponentTypesEvent;
use craft\services\Fields;
use yii\base\Event;

Event::on(
    Fields::class,
    Fields::EVENT_REGISTER_FIELD_TYPES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyField::class;
    }
);
```

If generated via `craft make field-type` for a plugin, registration is added to the plugin's `init()` automatically.

## Key FieldTrait Properties

| Property | Type | Default | Purpose |
|----------|------|---------|---------|
| `searchable` | `bool` | `false` | Whether values are indexed for search |
| `translationMethod` | `string` | `TRANSLATION_METHOD_NONE` | How values are shared across sites |
| `translationKeyFormat` | `?string` | `null` | Custom translation key pattern |
| `layoutElement` | `?CustomField` | `null` | The field layout element wrapping this field |
| `static` | `bool` | `false` | Whether the field displays in read-only mode |

Translation methods:
| Constant | Behavior |
|----------|----------|
| `TRANSLATION_METHOD_NONE` | Same value across all sites |
| `TRANSLATION_METHOD_SITE` | Independent value per site |
| `TRANSLATION_METHOD_SITE_GROUP` | Shared within site group |
| `TRANSLATION_METHOD_LANGUAGE` | Shared by language |
| `TRANSLATION_METHOD_CUSTOM` | Uses `translationKeyFormat` |
