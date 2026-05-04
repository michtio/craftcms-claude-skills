# Element Index — CP Presentation

## Contents

- Common Pitfalls
- Sources (defineSources, context values)
- Table Attributes (defineTableAttributes, attributeHtml, status pills, prepElementQueryForTableAttribute)
- Sort Options (defineSortOptions)
- Element Display Modes — chips, cards, table rows: when each renders, customization methods
- Card Attributes (Craft 5.5+)
- Thumbnails — hasThumbs, thumbUrl, thumbSvg, checkered/rounded
- Conditions (createCondition, custom condition rules)
- Actions (defineActions, includeSetStatusAction, custom actions, per-element edit-screen action menu)
- Exporters
- Sidebar and Metadata
- Preview Targets
- Index View Modes — table, cards, structure; defaultIndexViewMode()
- Extending Element Indexes via Events — adding columns, sources, bulk actions, condition rules to any element type

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
- Using `<span class="status red">` for status labels — produces a 10×10 px dot, not a pill. Text inside it wraps vertically one character per line. Use `Cp::statusLabelHtml()` instead.
- Registering bulk actions (`EVENT_REGISTER_ACTIONS`) but forgetting per-element actions (`EVENT_DEFINE_ACTION_MENU_ITEMS`) — plugin actions appear on the index multi-select menu but not on the per-element edit screen "..." menu.
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

### Status Pills in Table Attributes

Status pills in custom table attributes use `Cp::statusLabelHtml()`, not `<span class="status">`. The raw `<span class="status red">` produces a 10×10 px dot indicator — putting text inside it causes one-character-per-line vertical wrapping in narrow element-index columns.

The correct helper (Craft 5.2.0+) is `\craft\helpers\Cp::statusLabelHtml()` — the same helper Craft uses for the native Status column's "ACTIVE" pill:

```php
use craft\enums\Color;
use craft\helpers\Cp;

protected function attributeHtml(string $attribute): string
{
    return match ($attribute) {
        'syncStatus' => Cp::statusLabelHtml([
            'color' => Color::Red,           // Color enum: Red, Orange, Amber, Yellow, Green, Teal, Blue, …
            'label' => 'Reset required',
            'icon' => 'warning',             // optional — Lucide icon key
            'indicatorClass' => 'pending',   // optional — overrides the dot's CSS class
        ]),
        default => parent::attributeHtml($attribute),
    };
}
```

The `Color` enum at `\craft\enums\Color` ships 20 named colors. For elements that implement `Statusable`, use `Cp::componentStatusLabelHtml($component)` as a one-call wrapper that resolves the color + label from the component's status definition.

**Symptom of the wrong pattern:** label text appears stacked vertically one character per line ("R\ne\ns\ne\nt") in narrow element-index cells.

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

## Element Display Modes

Craft 5 renders elements in three display modes depending on context. Each mode uses different methods for customization.

### Chips (compact inline)

Chips appear in relation fields, breadcrumbs, inline references, and anywhere elements are shown compactly. Rendered by `Cp::elementChipHtml()` or the Twig function `elementChip()`.

```php
// Customize the chip label (default: uiLabel, which is usually the title)
protected function chipLabelHtml(): string
{
    return Html::encode($this->getUiLabel());
}

// Control whether the status pip shows on chips
public function showStatusIndicator(): bool  // Since 5.4.0
{
    return true;
}
```

Sizing: `Cp::CHIP_SIZE_LARGE`, `Cp::CHIP_SIZE_SMALL`. Plugins can modify chip output via `Cp::EVENT_DEFINE_ELEMENT_CHIP_HTML`.

### Cards (visual with thumbnail)

Cards appear in card view of element indexes, Matrix card mode, and relation field card display. Rendered by `Cp::elementCardHtml()` or the Twig function `elementCard()`.

```php
// Custom card body content (default: renders card body elements from field layout)
protected function cardBodyHtml(): ?string
{
    // Default iterates getFieldLayout()->getCardBodyElements($this)
    return parent::cardBodyHtml();
}

// Custom card title (since 5.7.0)
protected function getCardTitle(): ?string
{
    return $this->title;
}
```

Card layout (which attributes appear in the card body) is configured via `FieldLayout::getCardView()`/`setCardView()` (since 5.5.0).

### Table rows (column-based)

Table rows are the classic element index view. Each column is rendered by `attributeHtml()`:

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

The base implementation handles `contentBlock:*` and `generatedField:*` prefixed attributes automatically.

### Summary

| Mode | Where it appears | Customization method | Size control |
|------|-----------------|---------------------|-------------|
| **Chip** | Relation fields, breadcrumbs, inline refs | `chipLabelHtml()` | `CHIP_SIZE_SMALL`, `CHIP_SIZE_LARGE` |
| **Card** | Card view, Matrix cards, relation card display | `cardBodyHtml()`, `defineCardAttributes()` | Field layout card view config |
| **Table** | Table view of element indexes | `attributeHtml()`, `defineTableAttributes()` | Column selection |

## Card Attributes (Craft 5.5+)

Define which attributes are available in card view:

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

Placeholders show in the field layout designer as preview content. Default card attributes include `dateCreated`, `dateUpdated`, `id`, `uid`, plus `link`/`slug`/`uri` for elements with URIs.

## Thumbnails

Thumbnails appear on chips (small) and cards (larger). The resolution chain:

1. `getThumbHtml(int $size)` — checks field layout's `thumbFieldKey` first (admin-configurable)
2. Falls back to `thumbUrl(int $size)` — override this for custom thumb logic
3. Falls back to `thumbSvg()` — SVG placeholder when no image exists

```php
// Declare that this element type supports thumbnails
public static function hasThumbs(): bool
{
    return true;
}

// Provide the thumbnail URL
protected function thumbUrl(int $size): ?string
{
    return $this->getFeatureImage()?->getThumbUrl($size);
}

// SVG fallback when no thumb URL exists — returns SVG markup, not a file path
protected function thumbSvg(): ?string
{
    return file_get_contents(Craft::getAlias('@my-plugin/icon.svg'));
}

// Checkered background for transparent images (like Assets)
protected function hasCheckeredThumb(): bool
{
    return false;
}

// Rounded thumbnail (like Users)
protected function hasRoundedThumb(): bool
{
    return false;
}
```

Thumbnails are lazy-loaded in the CP via `Craft.cp.elementThumbLoader` — no custom JS needed.

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

### Per-Element Edit-Screen Action Menu

Bulk actions (`EVENT_REGISTER_ACTIONS` / `defineActions()`) and the per-element edit-screen "..." disclosure menu are **two different surfaces**, wired to two different events. Registering a bulk action does not add it to the per-element menu.

The per-element menu is built from `Element::getActionMenuItems()` and fires `Element::EVENT_DEFINE_ACTION_MENU_ITEMS` (since Craft 5.0). Plugins append to `$event->items` using the `Cp::disclosureMenu()` item shape:

```php
use craft\base\Element;
use craft\elements\User;
use craft\events\DefineMenuItemsEvent;
use yii\base\Event;

Event::on(
    User::class,
    Element::EVENT_DEFINE_ACTION_MENU_ITEMS,
    function(DefineMenuItemsEvent $event): void {
        /** @var User $user */
        $user = $event->sender;

        $event->items[] = [
            'id' => 'pp-force-reset',
            'icon' => 'rotate',
            'label' => Craft::t('my-plugin', 'Force password reset'),
            'action' => 'my-plugin/user-password/force-reset',
            // OR 'url' => UrlHelper::cpUrl(...) for navigable items
        ];
    },
);
```

For destructive items (red-tinted, segregated below safe items), pass `'destructive' => true`.

**Which surface to register on:** match the registration to the security model of the action. "Change password..." should never be a bulk action — applying the same input to N users is a security anti-pattern. "Force password reset" and "Send password reset email" are useful on both surfaces. If in doubt, register per-element only and add bulk when the action is safe for N-at-a-time.

**Symptom of forgetting the per-element hook:** plugin actions appear absent from the per-user edit screen "..." menu, even though the index shows them when you bulk-select.

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

Element indexes support multiple view modes. Users switch between them via toolbar buttons.

### Built-in modes

| Mode | Icon | When to use | Rendering |
|------|------|-------------|-----------|
| **Table** | list | Default for all elements. Column-based with sort headers. | `attributeHtml()` per column |
| **Cards** | grid | Visual overview with thumbnails. Good for media, products. | `cardBodyHtml()` + `defineCardAttributes()` |
| **Structure** | structure | Hierarchical elements with drag-to-reorder. | Table with nesting indicators |

Table mode is always available. Cards require `defineCardAttributes()`. Structure requires the element type to support structures.

### Registering view modes

```php
public static function indexViewModes(): array
{
    $viewModes = parent::indexViewModes();

    // Add structure view for hierarchical elements
    $viewModes[] = [
        'mode' => 'structure',
        'title' => Craft::t('app', 'Display in a structure'),
        'icon' => 'structure',
    ];

    return $viewModes;
}
```

Each mode entry has: `mode` (string key), `title` (tooltip text), `icon` (CP icon name).

### Default view mode

```php
protected static function defaultIndexViewMode(): string
{
    return 'cards'; // or 'table' (default) or 'structure'
}
```

This controls which view the user sees when first opening the element index. Users can switch and their preference is remembered per-element-type.

## Extending Element Indexes via Events

Plugins can extend any element type's index (including Craft's built-in Users, Entries, Assets) without modifying the element class. Most events below fire on `craft\base\Element` and are inherited by all element types. Condition rules are the exception — they live on `craft\base\conditions\BaseCondition`.

### Event Reference

| Event Constant | Event Class | Purpose |
|---------------|------------|---------|
| `EVENT_REGISTER_TABLE_ATTRIBUTES` | `RegisterElementTableAttributesEvent` | Add custom columns |
| `EVENT_REGISTER_DEFAULT_TABLE_ATTRIBUTES` | `RegisterElementDefaultTableAttributesEvent` | Set which columns show by default |
| `EVENT_DEFINE_ATTRIBUTE_HTML` | `DefineAttributeHtmlEvent` | Custom column rendering |
| `EVENT_PREP_QUERY_FOR_TABLE_ATTRIBUTE` | `ElementIndexTableAttributeEvent` | Modify query for custom column data |
| `EVENT_REGISTER_SOURCES` | `RegisterElementSourcesEvent` | Add sidebar sources |
| `EVENT_REGISTER_ACTIONS` | `RegisterElementActionsEvent` | Add bulk actions (index multi-select) |
| `EVENT_DEFINE_ACTION_MENU_ITEMS` | `DefineMenuItemsEvent` | Add per-element edit-screen "..." menu items |
| `EVENT_REGISTER_SORT_OPTIONS` | `RegisterElementSortOptionsEvent` | Add sort options |
| `EVENT_REGISTER_SEARCHABLE_ATTRIBUTES` | `RegisterElementSearchableAttributesEvent` | Add searchable attributes |
| `EVENT_REGISTER_CARD_ATTRIBUTES` | `RegisterElementCardAttributesEvent` | Add card view attributes (5.5+) |
| `EVENT_REGISTER_DEFAULT_CARD_ATTRIBUTES` | `RegisterElementDefaultCardAttributesEvent` | Set default card attributes (5.5+) |
| `EVENT_DEFINE_METADATA` | `DefineMetadataEvent` | Add metadata to element editor sidebar |

Condition rules live on `craft\base\conditions\BaseCondition`:

| Event Constant | Event Class | Purpose |
|---------------|------------|---------|
| `EVENT_REGISTER_CONDITION_RULES` | `RegisterConditionRulesEvent` | Add custom condition rules |

### Adding a custom column to the Users index

```php
use craft\base\Element;
use craft\elements\User;
use craft\events\DefineAttributeHtmlEvent;
use craft\events\RegisterElementTableAttributesEvent;
use yii\base\Event;

// Step 1: Register the column
Event::on(
    User::class,
    Element::EVENT_REGISTER_TABLE_ATTRIBUTES,
    function(RegisterElementTableAttributesEvent $event) {
        $event->tableAttributes['lastPasswordChange'] = [
            'label' => Craft::t('my-plugin', 'Last Password Change'),
        ];
    }
);

// Step 2: Render the column value
Event::on(
    User::class,
    Element::EVENT_DEFINE_ATTRIBUTE_HTML,
    function(DefineAttributeHtmlEvent $event) {
        if ($event->attribute === 'lastPasswordChange') {
            /** @var User $user */
            $user = $event->sender;
            $date = MyPlugin::getInstance()
                ->getPasswordService()
                ->getLastPasswordChange($user->id);

            $event->html = $date
                ? Craft::$app->getFormatter()->asDatetime($date)
                : '';

            $event->handled = true;
        }
    }
);
```

### Preparing query data for custom columns

When your custom column needs data not on the element by default, modify the query to avoid N+1:

```php
use craft\elements\User;
use craft\events\ElementIndexTableAttributeEvent;
use yii\base\Event;

Event::on(
    User::class,
    Element::EVENT_PREP_QUERY_FOR_TABLE_ATTRIBUTE,
    function(ElementIndexTableAttributeEvent $event) {
        if ($event->attribute === 'lastPasswordChange') {
            // Add a subquery or join so the data is available
            $event->query
                ->leftJoin(
                    '{{%my_password_history}} ph',
                    '[[ph.userId]] = [[elements.id]]'
                )
                ->addSelect(['ph.dateChanged AS lastPasswordChange']);
        }
    }
);
```

### Adding a sidebar source

```php
use craft\elements\User;
use craft\events\RegisterElementSourcesEvent;
use yii\base\Event;

Event::on(
    User::class,
    Element::EVENT_REGISTER_SOURCES,
    function(RegisterElementSourcesEvent $event) {
        $event->sources[] = [
            'heading' => Craft::t('my-plugin', 'Password Status'),
        ];

        $event->sources[] = [
            'key' => 'my-plugin:expired-passwords',
            'label' => Craft::t('my-plugin', 'Expired Passwords'),
            'criteria' => [],  // Custom filtering handled in EVENT_BEFORE_PREPARE
            'data' => ['type' => 'expired-passwords'],
            'defaultSort' => ['dateCreated', 'desc'],
        ];

        $event->sources[] = [
            'key' => 'my-plugin:reset-required',
            'label' => Craft::t('my-plugin', 'Reset Required'),
            'criteria' => ['passwordResetRequired' => true],
            'defaultSort' => ['dateCreated', 'desc'],
        ];
    }
);
```

### Adding a custom bulk action

Element actions implement `craft\base\ElementActionInterface`. Register them per source:

```php
use craft\elements\User;
use craft\events\RegisterElementActionsEvent;
use yii\base\Event;

Event::on(
    User::class,
    Element::EVENT_REGISTER_ACTIONS,
    function(RegisterElementActionsEvent $event) {
        $event->actions[] = ForcePasswordReset::class;
    }
);
```

The action class:

```php
use craft\base\ElementAction;
use craft\elements\db\ElementQueryInterface;

class ForcePasswordReset extends ElementAction
{
    /**
     * @inheritdoc
     */
    public static function displayName(): string
    {
        return Craft::t('my-plugin', 'Force Password Reset');
    }

    /**
     * @inheritdoc
     */
    public function performAction(ElementQueryInterface $query): bool
    {
        /** @var User[] $users */
        $users = $query->all();

        foreach ($users as $user) {
            $user->passwordResetRequired = true;
            Craft::$app->getElements()->saveElement($user);
        }

        $this->setMessage(Craft::t(
            'my-plugin',
            '{count} user(s) flagged for password reset.',
            ['count' => count($users)]
        ));

        return true;
    }
}
```

### Adding condition rules

Condition rules allow users to filter the element index. Listen on the element's condition class:

```php
use craft\elements\conditions\users\UserCondition;
use craft\base\conditions\BaseCondition;
use craft\events\RegisterConditionRulesEvent;
use yii\base\Event;

Event::on(
    UserCondition::class,
    BaseCondition::EVENT_REGISTER_CONDITION_RULES,
    function(RegisterConditionRulesEvent $event) {
        $event->conditionRules[] = PasswordExpiredConditionRule::class;
    }
);
```

See `conditions.md` for building custom condition rule classes.

### Adding metadata to the element editor sidebar

```php
use craft\elements\User;
use craft\events\DefineMetadataEvent;
use yii\base\Event;

Event::on(
    User::class,
    Element::EVENT_DEFINE_METADATA,
    function(DefineMetadataEvent $event) {
        /** @var User $user */
        $user = $event->sender;

        $lastChange = MyPlugin::getInstance()
            ->getPasswordService()
            ->getLastPasswordChange($user->id);

        if ($lastChange) {
            $event->metadata[Craft::t('my-plugin', 'Password Changed')] =
                Craft::$app->getFormatter()->asDatetime($lastChange);
        }
    }
);
```

### Adding sort options

```php
use craft\elements\User;
use craft\events\RegisterElementSortOptionsEvent;
use yii\base\Event;

Event::on(
    User::class,
    Element::EVENT_REGISTER_SORT_OPTIONS,
    function(RegisterElementSortOptionsEvent $event) {
        $event->sortOptions['lastPasswordChange'] = [
            'label' => Craft::t('my-plugin', 'Last Password Change'),
            'orderBy' => 'my_password_history.dateChanged',
            'defaultDir' => 'desc',
        ];
    }
);
```

### User index built-in sources

The User element provides these sidebar sources by default:

- `*` — All Users
- `admins` — Admins
- `credentialed` — Credentialed (users who can log in)
- `group:{uid}` — One per user group

Plugin sources append after these via `EVENT_REGISTER_SOURCES`.
