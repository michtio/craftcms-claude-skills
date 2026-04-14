# Fields — Field Types, Native Fields, Field Layout Elements

## Documentation

- Field types: https://craftcms.com/docs/5.x/extend/field-types.html
- Field layout elements: https://craftcms.com/docs/5.x/extend/field-layout-element-types.html
- Custom fields system: https://craftcms.com/docs/5.x/system/fields.html
- Class reference: https://docs.craftcms.com/api/v5/craft-base-field.html

## Common Pitfalls

- Creating a field layout element class for a custom field type — Craft automatically wraps your field in `CustomField`. A layout element class would create a duplicate entry in the field layout designer.
- Forgetting `Fields::EVENT_REGISTER_FIELD_TYPES` — without registration, the field type won't appear in the Settings → Fields type selector, even though the class exists.
- Not calling `parent::afterElementSave()` — the base implementation handles relation updates and field lifecycle hooks. Skipping it silently breaks custom field data persistence.
- Using `afterElementSave()` without checking `$element->isFieldDirty()` — runs expensive processing (API calls, re-indexing) on every save even when the field value didn't change.
- Confusing native fields with custom field types — native fields are layout elements for element attributes (Title, Slug), custom fields are the configurable types users add in Settings → Fields. Different base classes, different registration events.

## When to Use What

Craft's field system has three distinct concepts. Understanding which one you need prevents building the wrong thing.

### Custom Field Types — Standalone field plugins

A custom field type is a **plugin whose primary purpose is providing a new kind of field** that works across ALL element types. Users install the plugin, then add the field in Settings → Fields, and assign it to any field layout — entries, assets, users, your custom elements, anything.

**Examples:** Colour Swatches, Hyper, ImageOptimize, CKEditor. These are standalone Composer packages.

**Extend:** `craft\base\Field` (or `craft\fields\BaseRelationField` for relation fields).
**Register:** `Fields::EVENT_REGISTER_FIELD_TYPES`.
**Scaffold:** `ddev craft make field-type --with-docblocks`.

You build a custom field type when you're creating a **reusable field that isn't tied to a specific element type**.

### Native Fields — Your element's own properties in the field layout designer

Native fields expose your **custom element's native properties** (like `postDate`, `externalId`, `category`) in the field layout designer, so administrators can position and configure them alongside custom fields.

These are NOT standalone plugins — they're part of your element type's implementation. Every custom element type with editable properties needs native fields. Craft's own Title, Slug, and Post Date fields are native fields.

**Extend:** `craft\fieldlayoutelements\BaseNativeField` (or use `TextField` for simple attributes).
**Register:** `FieldLayout::EVENT_DEFINE_NATIVE_FIELDS` (scoped to your element type).
**No generator** — create manually or use ad-hoc `TextField` definitions.

You build native fields when you're building a **custom element type and need its properties in the editor**.

### UI Elements — Non-data display components

UI elements are read-only layout components: sync status panels, info widgets, visual separators. They don't correspond to element properties — they provide feedback or structure.

**Extend:** `craft\fieldlayoutelements\BaseUiElement`.
**Register:** `FieldLayout::EVENT_DEFINE_UI_ELEMENTS`.

You build UI elements when you need **display-only components in the element editor**.

## Custom Field Types

### Scaffold and Registration

```bash
ddev craft make field-type --with-docblocks
```

```php
Event::on(Fields::class, Fields::EVENT_REGISTER_FIELD_TYPES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyField::class;
    }
);
```

### Key Methods

```php
class MyField extends Field
{
    public string $someOption = 'default';

    public static function displayName(): string
    {
        return Craft::t('my-plugin', 'My Field');
    }

    // Column type(s) for content table. Return false to manage storage yourself.
    public function getContentColumnType(): array|string
    {
        return Schema::TYPE_STRING;
    }

    public function getSettingsHtml(): ?string
    {
        return Craft::$app->getView()->renderTemplate('my-plugin/_field/settings', ['field' => $this]);
    }

    protected function inputHtml(mixed $value, ?ElementInterface $element, bool $inline): ?string
    {
        return Craft::$app->getView()->renderTemplate('my-plugin/_field/input', [
            'field' => $this,
            'value' => $value,
            'element' => $element,
        ]);
    }

    public function normalizeValue(mixed $value, ?ElementInterface $element): mixed
    {
        // DB/POST → working type
        return $value instanceof MyValueObject ? $value : new MyValueObject($value);
    }

    public function serializeValue(mixed $value, ?ElementInterface $element): mixed
    {
        // Working type → DB storage
        return $value instanceof MyValueObject ? $value->toArray() : $value;
    }

    public function afterElementSave(ElementInterface $element, bool $isNew): void
    {
        if ($element->isFieldDirty($this->handle)) {
            // Only process when value actually changed
        }
        parent::afterElementSave($element, $isNew);
    }
}
```

### Content Column Options

```php
Schema::TYPE_STRING    // VARCHAR
Schema::TYPE_TEXT      // TEXT
Schema::TYPE_INTEGER   // INT
Schema::TYPE_JSON      // JSON
// Multiple columns:
['date' => Schema::TYPE_DATETIME, 'timezone' => Schema::TYPE_STRING]
// No column (manage yourself):
false
```

### Relation Fields

Extend `craft\fields\BaseRelationField` for element relation fields:

```php
class MyRelationField extends BaseRelationField
{
    protected static function elementType(): string { return MyElement::class; }
    public static function displayName(): string { return Craft::t('my-plugin', 'My Elements'); }
}
```

## Native Fields

Register via `FieldLayout::EVENT_DEFINE_NATIVE_FIELDS`, scoped to your element type:

```php
Event::on(FieldLayout::class, FieldLayout::EVENT_DEFINE_NATIVE_FIELDS,
    function(DefineFieldLayoutFieldsEvent $event) {
        $layout = $event->sender;
        if ($layout->type === MyElement::class) {
            $event->fields[] = PostDateField::class;
        }
    }
);
```

### Ad-Hoc (No Dedicated Class)

```php
$event->fields[] = [
    'class' => \craft\fieldlayoutelements\TextField::class,
    'attribute' => 'externalId',
    'label' => Craft::t('my-plugin', 'External ID'),
    'mandatory' => true,
];
```

### Custom Native Field Class

```php
class PostDateField extends BaseNativeField
{
    public bool $mandatory = true;

    public function attribute(): string { return 'postDate'; }

    protected function defaultLabel(?ElementInterface $element = null): ?string
    {
        return Craft::t('app', 'Post Date');
    }

    protected function inputHtml(?ElementInterface $element = null, bool $static = false): ?string
    {
        return Cp::dateTimeFieldHtml([
            'id' => 'postDate',
            'name' => 'postDate',
            'value' => $element?->postDate,
            'disabled' => $static,
        ]);
    }
}
```

### Base Definitions

| Class | Purpose |
|-------|---------|
| `BaseNativeField` | Element attributes with input |
| `TextField` | Simple text/number — no custom class needed |
| `BaseUiElement` | Read-only display |
| `CustomField` | Wraps custom field types — never extend |

## UI Elements

```php
Event::on(FieldLayout::class, FieldLayout::EVENT_DEFINE_UI_ELEMENTS,
    function(DefineFieldLayoutFieldsEvent $event) {
        $event->elements[] = SyncStatusWidget::class;
    }
);
```

## FieldLayoutBehavior

For element types with multiple variants (like entry types):

```php
class MyCategory extends Model
{
    public ?int $fieldLayoutId = null;

    protected function defineBehaviors(): array
    {
        return [
            'fieldLayout' => [
                'class' => FieldLayoutBehavior::class,
                'elementType' => MyElement::class,
            ],
        ];
    }
}
```

## Validation

### Element Validation Rules

`getElementValidationRules()` defines validation applied to the **element** when the field value is saved. Rules are added to the element's `rules()` automatically. Standard Yii validators work: `string`, `number`, `email`, `url`, `required`, `in`, `match`, etc.

```php
public function getElementValidationRules(): array
{
    return [
        ['string', 'max' => $this->maxLength],
        ['required', 'when' => fn($model) => $this->required],
    ];
}
```

### Field Settings Validation

`defineRules()` validates the **field's own settings** (configured in Settings > Fields), not the element value. Always call `parent::defineRules()` -- skipping it silently drops validation for `handle`, `name`, and other core settings.

```php
protected function defineRules(): array
{
    $rules = parent::defineRules();
    $rules[] = [['maxLength'], 'number', 'integerOnly' => true, 'min' => 1];
    $rules[] = [['placeholder'], 'string', 'max' => 255];
    return $rules;
}
```

## Search Keywords

Without `getSearchKeywords()`, custom field content is invisible to Craft's search. Return an empty string to opt out of indexing (appropriate for non-textual data like coordinates or binary flags).

```php
public function getSearchKeywords(mixed $value, ElementInterface $element): string
{
    return $value instanceof MyValueObject ? $value->getSearchableText() : (string)$value;
}
```

After changing this method on an existing field, rebuild: `ddev craft db/search-indexes`.

## GraphQL Integration

Three methods control how a custom field type appears in Craft's GraphQL API. All optional -- if omitted, the field won't be queryable via GraphQL. See `graphql.md` for full GQL patterns.

```php
use GraphQL\Type\Definition\Type;

// Return type for queries
public function getContentGqlType(): array|Type
{
    return Type::string();
    // For complex types: return ['name' => $this->handle, 'type' => Type::string(), 'resolve' => fn($source) => ...]
}

// Input type for mutations
public function getContentGqlMutationArgumentType(): array|Type
{
    return ['name' => $this->handle, 'type' => Type::string()];
}

// Argument type for query filtering
public function getContentGqlQueryArgumentType(): array|Type
{
    return ['name' => $this->handle, 'type' => Type::listOf(Type::string())];
}
```

## Lifecycle Methods

Override these in your field class to hook into element CRUD operations. The `before*` methods can return `false` to cancel the operation.

| Method | When it fires | Notes |
|--------|---------------|-------|
| `beforeElementSave($element, $isNew)` | Before save | Return `false` to cancel |
| `afterElementSave($element, $isNew)` | After save | **Most common** -- sync data, process relations |
| `afterElementPropagate($element, $isNew)` | After multi-site propagation | Runs after all sites updated |
| `beforeElementDelete($element)` | Before soft/hard delete | Return `false` to prevent |
| `afterElementDelete($element)` | After delete | **Common** -- clean up resources |
| `beforeElementRestore($element)` | Before restore from soft delete | Return `false` to prevent |
| `afterElementRestore($element)` | After restore | Re-establish connections |

```php
public function afterElementSave(ElementInterface $element, bool $isNew): void
{
    if ($element->isFieldDirty($this->handle)) {
        $value = $element->getFieldValue($this->handle);
        // Process only when value changed
    }
    parent::afterElementSave($element, $isNew); // Always call parent
}
```

## Multi-Site Translation

The `translationMethod` property determines how field values are shared across sites.

| Constant | Behavior |
|----------|----------|
| `Field::TRANSLATION_METHOD_NONE` | Same value across all sites (default) |
| `Field::TRANSLATION_METHOD_SITE` | Unique value per site |
| `Field::TRANSLATION_METHOD_SITE_GROUP` | Shared within site group, unique across groups |
| `Field::TRANSLATION_METHOD_LANGUAGE` | Shared when sites have the same language |
| `Field::TRANSLATION_METHOD_CUSTOM` | Custom logic via `getTranslationKey()` |

### getTranslationKey

With `TRANSLATION_METHOD_CUSTOM`, elements with the same translation key share the same field value.

```php
public function getTranslationKey(ElementInterface $element): string
{
    return $element->getSite()->currency ?? 'default';
}
```

### getTranslationDescription

Human-readable description shown in the field layout designer tooltip.

```php
public function getTranslationDescription(): ?string
{
    return Craft::t('my-plugin', 'Values are shared across sites with the same currency.');
}
```

`supportedTranslationMethods()` declares which methods the field type supports -- see [Craft 5 Static Configuration Methods](#craft-5-static-configuration-methods).

## Static and Preview HTML

### getStaticHtml — Read-only rendering

Called when rendering the field in a non-editable context: draft sidebars, disabled fields, or without edit permission.

```php
public function getStaticHtml(mixed $value, ElementInterface $element): string
{
    return $value ? Html::encode((string)$value) : '';
}
```

### getPreviewHtml — Element index table/card preview

Called when rendering a compact preview in element index tables and cards. Keep output short.

```php
public function getPreviewHtml(mixed $value, ElementInterface $element): string
{
    return $value ? Html::encode(StringHelper::truncate((string)$value, 50)) : '';
}
```

Both methods must return HTML-safe strings. Use `Html::encode()` for plain text to prevent XSS.

## Craft 5 Static Configuration Methods

Static methods that define field type metadata. Craft calls these without an instance to build the field type selector, generate IDE hints, and configure database storage.

| Method | Return Type | Purpose |
|--------|-------------|---------|
| `icon()` | `?string` | SVG icon path or icon name for the field type picker |
| `phpType()` | `string` | PHP type hint for IDE autocompletion (e.g., `'string\|null'`) |
| `dbType()` | `string\|null` | Database column type -- replaces older `getContentColumnType()` |
| `isMultiInstance()` | `bool` | Whether multiple instances can exist in one layout (default `true`) |
| `supportedTranslationMethods()` | `array` | Array of `TRANSLATION_METHOD_*` constants the field supports |

```php
public static function icon(): ?string { return 'palette'; }
public static function phpType(): string { return 'string|null'; }
public static function isMultiInstance(): bool { return true; }

public static function dbType(): string|null
{
    return \yii\db\Schema::TYPE_TEXT;
    // Return null when the field manages its own storage (relation tables, external APIs)
}
```

`dbType()` is the preferred approach in Craft 5. The instance method `getContentColumnType()` still works but `dbType()` takes precedence when both are defined.
