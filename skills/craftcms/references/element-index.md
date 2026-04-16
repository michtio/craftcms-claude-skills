# Element Index — CP Presentation

## Contents

- Common Pitfalls
- Sources (defineSources, context values)
- Table Attributes (defineTableAttributes, attributeHtml, prepElementQueryForTableAttribute)
- Sort Options (defineSortOptions)
- Card Attributes (Craft 5.5+)
- Thumbnails
- Conditions (createCondition, custom condition rules)
- Actions (defineActions, includeSetStatusAction, custom actions)
- Exporters
- Sidebar and Metadata
- Preview Targets
- Index View Modes

## Documentation

- CP section: https://craftcms.com/docs/5.x/extend/cp-section.html
- CP edit pages: https://craftcms.com/docs/5.x/extend/cp-edit-pages.html
- Element types: https://craftcms.com/docs/5.x/extend/element-types.html

## Common Pitfalls

- Using the old `tableAttributeHtml()` — renamed to `attributeHtml()` in Craft 5. The old method name will silently not be called.
- Not implementing `prepElementQueryForTableAttribute()` for custom attributes — Craft won't eager-load the data your column needs, causing N+1 queries or empty columns.
- Forgetting `includeSetStatusAction()` — without it, users can't bulk-change status from the index, even though your element has statuses.
- Sources returning stale data — sources are memoized per-request. Use service getters that read from MemoizableArray, not static arrays.
- Returning all table attributes as defaults — clutters the index. Pick the 4-5 columns users need most; they can customize from there.
- Loading all elements in `defineSources()` to extract grouping values — `defineSources()` runs on every element index page load. Use an aggregate query (`GROUP BY`) to get distinct values, never `::find()->all()` followed by array extraction.

## Sources

Sources define the sidebar navigation in element indexes:

```php
protected static function defineSources(string $context): array
{
    $sources = [
        [
            'key' => '*',
            'label' => Craft::t('my-plugin', 'All Items'),
            'criteria' => [],
            'defaultSort' => ['postDate', 'desc'],
        ],
    ];

    foreach (MyPlugin::$plugin->getCategories()->getAllCategories() as $category) {
        $sources[] = [
            'key' => 'category:' . $category->uid,
            'label' => $category->name,
            'criteria' => ['categoryId' => $category->id],
            'data' => ['handle' => $category->handle],
            'defaultSort' => ['postDate', 'desc'],
        ];
    }

    return $sources;
}
```

Source key `'*'` = all elements. Use prefix patterns like `'category:{uid}'` — consistent with Craft core (`section:{uid}`, `folder:{uid}`).

Context values: `'index'` (element index page), `'modal'` (selection modal), `'field'` (relation field), `'settings'` (admin).

## Table Attributes

Define available columns in the element index table view:

```php
protected static function defineTableAttributes(): array
{
    return [
        'externalId' => ['label' => Craft::t('my-plugin', 'External ID')],
        'category' => ['label' => Craft::t('my-plugin', 'Category')],
        'postDate' => ['label' => Craft::t('app', 'Post Date')],
        'expiryDate' => ['label' => Craft::t('app', 'Expiry Date')],
        'dateCreated' => ['label' => Craft::t('app', 'Date Created')],
        'link' => ['label' => Craft::t('app', 'Link'), 'icon' => 'world'],
    ];
}
```

### Default Table Attributes

Pick the 4-5 most useful columns shown by default:

```php
protected static function defineDefaultTableAttributes(string $source): array
{
    return ['category', 'postDate', 'expiryDate', 'dateCreated'];
}
```

### Custom Attribute HTML (Craft 5)

Override `attributeHtml()` (renamed from `tableAttributeHtml()` in Craft 5) for custom column rendering:

```php
protected function attributeHtml(string $attribute): string
{
    return match ($attribute) {
        'category' => $this->getCategory()?->name ?? '',
        'externalId' => Html::tag('code', Html::encode($this->externalId)),
        default => parent::attributeHtml($attribute),
    };
}
```

### Prepare Query for Table Attribute

When a table attribute needs eager-loaded data, override to prevent N+1:

```php
protected static function prepElementQueryForTableAttribute(
    ElementQueryInterface $elementQuery,
    string $attribute
): void {
    switch ($attribute) {
        case 'category':
            // Add eager loading or joins for this attribute
            break;
        default:
            parent::prepElementQueryForTableAttribute($elementQuery, $attribute);
    }
}
```

## Sort Options

```php
protected static function defineSortOptions(): array
{
    return [
        'title' => Craft::t('app', 'Title'),
        'postDate' => Craft::t('app', 'Post Date'),
        'expiryDate' => Craft::t('app', 'Expiry Date'),
        [
            'label' => Craft::t('my-plugin', 'Category'),
            'orderBy' => 'my_elements.categoryId',
            'attribute' => 'category',
        ],
        'dateCreated' => Craft::t('app', 'Date Created'),
    ];
}
```

Simple form: `'column' => 'Label'`. Array form: `label`, `orderBy` (SQL expression or column), optional `attribute` (matches a table attribute key).

## Card Attributes (Craft 5.5+)

```php
protected static function defineCardAttributes(): array
{
    $attributes = parent::defineCardAttributes();

    $attributes['category'] = [
        'label' => Craft::t('my-plugin', 'Category'),
        'placeholder' => fn() => 'Example Category',
    ];

    $attributes['postDate'] = [
        'label' => Craft::t('app', 'Post Date'),
        'placeholder' => fn() => (new \DateTime())->sub(new \DateInterval('P7D')),
    ];

    return $attributes;
}

protected static function defineDefaultCardAttributes(): array
{
    return ['category', 'postDate'];
}
```

Placeholders show in the field layout designer as preview content.

## Thumbnails

```php
public static function hasThumbs(): bool
{
    return true;
}

protected function thumbUrl(int $size): ?string
{
    return $this->getFeatureImage()?->getThumbUrl($size);
}
```

## Conditions

```php
public static function createCondition(): ElementConditionInterface
{
    return Craft::createObject(MyElementCondition::class);
}
```

### Custom Condition Rules

No scaffold — create manually. Extend `craft\elements\conditions\ElementConditionRule`:

```php
class CategoryConditionRule extends BaseElementSelectConditionRule
{
    public function getLabel(): string
    {
        return Craft::t('my-plugin', 'Category');
    }

    public function getExclusiveQueryParams(): array
    {
        return ['categoryId'];
    }

    public function modifyQuery(ElementQueryInterface $query): void
    {
        $query->categoryId($this->getElementId());
    }
}
```

Register in your condition class:

```php
class MyElementCondition extends ElementCondition
{
    protected function selectableConditionRules(): array
    {
        return array_merge(parent::selectableConditionRules(), [
            CategoryConditionRule::class,
        ]);
    }
}
```

## Actions

Craft auto-adds Edit, Duplicate, Delete. Define additional bulk actions:

```php
protected static function defineActions(string $source): array
{
    return [
        SyncItems::class,
        SetStatus::class,
    ];
}

protected static function includeSetStatusAction(): bool
{
    return true;
}
```

### Custom Element Actions

```bash
ddev craft make element-action --with-docblocks
```

```php
class SyncItems extends ElementAction
{
    public static function displayName(): string
    {
        return Craft::t('my-plugin', 'Sync Items');
    }

    public function performAction(ElementQueryInterface $query): bool
    {
        foreach ($query->all() as $element) {
            Craft::$app->getQueue()->push(new SyncItem([
                'elementId' => $element->id,
            ]));
        }

        $this->setMessage(Craft::t('my-plugin', 'Sync jobs queued.'));
        return true;
    }
}
```

## Exporters

Craft provides `Raw` and `Expanded` by default:

```php
protected static function defineExporters(string $source): array
{
    $exporters = parent::defineExporters($source);
    $exporters[] = MyCustomExporter::class;
    return $exporters;
}
```

## Sidebar and Metadata

### Edit Screen Metadata

```php
protected function metadata(): array
{
    return [
        Craft::t('my-plugin', 'External ID') => $this->externalId ?: false,
        Craft::t('my-plugin', 'Category') => $this->getCategory()?->name ?: false,
        Craft::t('app', 'Date Created') => $this->dateCreated?->format('Y-m-d H:i'),
    ];
}
```

Values of `false` are omitted from the sidebar.

### Custom Sidebar HTML

```php
public function getSidebarHtml(bool $static): string
{
    $html = parent::getSidebarHtml($static);

    $html .= Craft::$app->getView()->renderTemplate(
        'my-plugin/_sidebar',
        ['element' => $this]
    );

    return $html;
}
```

## Preview Targets

```php
protected function previewTargets(): array
{
    $targets = parent::previewTargets();

    if ($this->uri) {
        $targets[] = [
            'label' => Craft::t('app', 'Primary page'),
            'url' => $this->getUrl(),
        ];
    }

    return $targets;
}
```

## Index View Modes

Override to add structure view for hierarchical elements:

```php
public static function indexViewModes(): array
{
    $viewModes = parent::indexViewModes();

    $viewModes[] = [
        'mode' => 'structure',
        'title' => Craft::t('app', 'Display in a structure'),
        'icon' => 'structure',
    ];

    return $viewModes;
}
```
