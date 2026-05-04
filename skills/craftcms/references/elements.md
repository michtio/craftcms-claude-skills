# Elements — Core Behavior

## Contents

- Common Pitfalls
- Static Configuration Methods — displayName, hasTitles, hasUris, hasDrafts, etc.
- Element Save Lifecycle (15 steps) — beforeSave, afterSave, afterPropagate
- Attributes, Field Values, and Mass Assignment — native vs custom, safe rules, CP save chain, silent drop trap
- Element Query — beforePrepare()
- Status from Dates
- Authorization — canView, canSave, canDelete + 5 more
- Drafts and Revisions
- Field Layouts — getFieldLayout, defineFieldLayouts
- URI/Routing
- Searchable Attributes
- Propagation
- CP Edit Pages — getCpEditUrl, elements/edit route, asCpScreen, slide-outs, extending User edit screens
- Preview Targets — previewTargets, EVENT_REGISTER_PREVIEW_TARGETS
- Generated Fields (5.8.0) — computed values saved on elements
- Eager Loading — eagerLoadingMap
- Soft Delete and Garbage Collection — Gc::EVENT_RUN
- Element Events Reference — ~40 events

## Documentation

- Element types: https://craftcms.com/docs/5.x/extend/element-types.html
- Element queries: https://craftcms.com/docs/5.x/development/element-queries.html
- Soft deletes: https://craftcms.com/docs/5.x/extend/soft-deletes.html
- Behaviors: https://craftcms.com/docs/5.x/extend/behaviors.html

## Common Pitfalls

- Always use `addSelect()` in `beforePrepare()` — it's the Craft convention. Craft's `**` placeholder system merges default columns regardless, but `addSelect()` is safely additive when multiple extensions contribute columns.
- Forgetting `postDate` and `expiryDate` in `addSelect()` — status computation breaks.
- Writing to the custom table in `beforeSave()` — the element ID isn't available until after the `elements` table insert. Custom table writes belong in `afterSave()`.
- Not checking `$this->getIsDraft()` before saving side effects — drafts shouldn't trigger sync jobs, API calls, etc.
- Storing status as a DB column — status must be computed from dates in `getStatus()`.
- Missing `site('*')` in queue workers — elements on non-primary sites are invisible. See `queue-jobs.md`.
- `hasDrafts()` returning `true` is required for `hasRevisions()` to work.
- Overriding `canView()` / `canSave()` without calling `parent::` — base class fires authorization events that other plugins depend on.
- `getFieldLayout()` returning null — field layout designer won't render, custom fields won't save.
- Native attributes without a validation rule or `'safe'` marker — Yii2 mass assignment silently drops the value on CP form saves. No error, no warning. The form appears to save but `afterSave()` writes null/old value. Add `'safe'` to `defineRules()` for any native attribute that needs to come through from forms.
- Using `->where()` on an element query — replaces all internal conditions (status filters, soft-delete filters, site scoping). Always use `->andWhere()`. The `where()` method is inherited from Yii's `Query` and does not understand element query internals. This applies everywhere: services, controllers, Twig — not just `beforePrepare()`.
- Hardcoding site IDs (`->where(['siteId' => 1])`) — site 1 may not exist (sites can be deleted and recreated). Use `Craft::$app->getSites()->getPrimarySite()->id` or `getCurrentSite()->id`.
- Loading all elements in `defineSources()` — runs on every index page load. See `element-index.md` Common Pitfalls for details.
- Declaring element query properties without wiring them in `beforePrepare()` — unused properties are dead code that mislead developers. Every property on the query class must have corresponding `andWhere` logic in `beforePrepare()`.
- Assuming `NestedElementTrait` handles site propagation — it doesn't. The trait manages owner relationships (eager loading, owner getters/setters, sort order) but does NOT override `getSupportedSites()` or `isLocalized()`. Address elements fall through to the base `Element` default: primary site only. Matrix entries get multi-site support because the `Entry` class explicitly overrides `getSupportedSites()` and delegates to `$this->getField()->getSupportedSitesForElement($this)` when `$this->fieldId` is set. If your custom nested element type needs multi-site propagation, you must override `getSupportedSites()` yourself — the trait won't do it for you.
- Assuming all User properties are populated from element queries — `UserQuery::beforePrepare()` only selects a subset of columns from the `users` table. Security-sensitive columns like `lastPasswordChangeDate`, `password`, `invalidLoginCount`, `lastInvalidLoginDate`, `verificationCode`, `verificationCodeIssuedDate`, and `lastLoginAttemptIp` are intentionally excluded. These properties are `null` on User elements loaded via `Craft::$app->getUser()->getIdentity()` or any element query, even when the database has values. To access them, query the `users` table directly: `(new Query())->from(Table::USERS)->where(['id' => $user->id])->one()`. Craft's CP profile page does this internally — it loads the User record separately from the element.

## Scaffold

```bash
ddev craft make element-type --with-docblocks
```

Generates: element class, element query, element condition, migration, CP controller routes, and templates.

## Static Configuration Methods

These `static` methods define what your element type *is*. Override as needed:

```php
public static function displayName(): string       // "Job", "Product"
public static function pluralDisplayName(): string  // "Jobs", "Products"
public static function hasTitles(): bool            // Elements have a title field
public static function hasThumbs(): bool            // Show thumbnails in index
public static function hasUris(): bool              // Elements get their own URLs
public static function hasStatuses(): bool          // Show status indicators
public static function hasDrafts(): bool            // Enable draft system
public static function isLocalized(): bool          // Multi-site support
public static function trackChanges(): bool         // Track field changes for drafts
public static function refHandle(): ?string         // Reference tag handle
```

### Custom Statuses

Override `statuses()` to define element-specific statuses:

```php
public static function statuses(): array
{
    return [
        self::STATUS_LIVE => Craft::t('my-plugin', 'Live'),
        self::STATUS_PENDING => ['label' => Craft::t('my-plugin', 'Pending'), 'color' => 'orange'],
        self::STATUS_EXPIRED => ['label' => Craft::t('my-plugin', 'Expired'), 'color' => 'red'],
        self::STATUS_DISABLED => Craft::t('app', 'Disabled'),
    ];
}
```

## Element Save Lifecycle (15 steps)

1. `beforeValidate()` → 2. `afterValidate()` → 3. `EVENT_BEFORE_SAVE` → 4. `beforeSave($isNew)` → 5. Insert/update `elements` table → 6. Insert/update `content` table → 7. `afterSave($isNew)` (**you** write to your custom element table here) → 8. Update search index → 9. `EVENT_AFTER_SAVE` → 10. Update structures → 11. Propagate to other sites → 12. Update drafts/revisions → 13. `afterPropagate($isNew)` → 14. `EVENT_AFTER_PROPAGATE` → 15. Clear caches.

### `beforeSave($isNew)`

Runs before the element is written to the database. Return `false` to cancel the save. The element ID is NOT available here for new elements — use for validation and state preparation:

```php
public function beforeSave(bool $isNew): bool
{
    if ($this->postDate === null) {
        $this->postDate = new DateTime();
    }

    return parent::beforeSave($isNew);
}
```

### `afterSave($isNew)`

This is where you write to your custom element table. The element ID is now available:

```php
public function afterSave(bool $isNew): void
{
    if ($isNew) {
        Db::insert(Table::MY_ELEMENTS, [
            'id' => $this->id,
            'externalId' => $this->externalId,
            'categoryId' => $this->categoryId,
            'postDate' => Db::prepareDateForDb($this->postDate),
            'expiryDate' => Db::prepareDateForDb($this->expiryDate),
        ]);
    } else {
        Db::update(Table::MY_ELEMENTS, [
            'externalId' => $this->externalId,
            'categoryId' => $this->categoryId,
            'postDate' => Db::prepareDateForDb($this->postDate),
            'expiryDate' => Db::prepareDateForDb($this->expiryDate),
        ], ['id' => $this->id]);
    }

    parent::afterSave($isNew);
}
```

### `afterPropagate($isNew)`

Fires after the element has been propagated to all sites. Use for cross-site side effects like queue jobs:

```php
public function afterPropagate(bool $isNew): void
{
    parent::afterPropagate($isNew);

    if (!$this->getIsDraft() && !$this->getIsRevision()) {
        // Safe to trigger side effects here
    }
}
```

## Attributes, Field Values, and Mass Assignment

Craft elements carry two distinct kinds of data. Understanding how each flows from form to database prevents silent data loss.

### Native attributes vs custom field values

**Native attributes** are PHP properties declared on the element class. They live in your custom element table (written in `afterSave()`), and are set/read as normal properties:

```php
// Direct assignment — used in services, queue jobs, migrations, controllers
$element->cockpitId = 'abc-123';
$element->postDate = new DateTime();
```

**Custom field values** are managed by Craft's field system. They live on a `CustomFieldBehavior` attached to every element, serialized into per-field-layout content tables (simple fields with a `dbType()`) or into separate tables (relational/Matrix fields via `afterElementSave()`). They use dedicated methods:

```php
// Single field
$element->setFieldValue('body', '<p>Hello</p>');
$value = $element->getFieldValue('body');

// Multiple fields
$element->setFieldValues([
    'body' => '<p>Hello</p>',
    'summary' => 'Short version',
]);
```

The `__get`/`__set` magic on Element bridges both worlds — `$element->body` checks native properties first, then falls back to `setFieldValue()`/`getFieldValue()`. When a native attribute and custom field share the same handle, use the `field:` prefix to disambiguate: `$element->{'field:body'}`.

### How CP form saves work

When an editor saves in the CP, `ElementsController::actionSave()` splits the POST body into two streams:

**Step 1 — `actionSave()` separates POST data:**
- Extracts meta-params (`elementType`, `siteId`, `enabled`, `draftName`, etc.)
- Extracts custom field data from the `fields` namespace (configurable via `fieldsLocation`)
- Everything remaining in the POST body = native attribute values

**Step 2 — `_applyParamsToElement()` applies them separately:**

```
Native attributes:  setAttributesFromRequest($attrs)  → Yii2 setAttributes() → safe check
Custom fields:      setFieldValuesFromRequest('fields') → setFieldValue() per field → no safe check
```

The native path goes through Yii2's mass assignment, which filters by safe attributes. The custom field path bypasses mass assignment entirely — it iterates editable fields from the field layout and calls `setFieldValueFromRequest()` for each, which normalizes via `$field->normalizeValueFromRequest()`.

### The safe attribute gate

Yii2's `setAttributes()` (called with `$safeOnly = true` by default) only assigns attributes returned by `safeAttributes()`. An attribute is "safe" for a scenario if **any** validation rule includes it for that scenario.

The controller sets the scenario to `SCENARIO_LIVE` before calling `setAttributesFromRequest()` for live elements, or `SCENARIO_ESSENTIALS` for drafts. Your native attributes must appear in at least one rule that applies to the relevant scenarios. The safest approach is to cover all three:

```php
protected function defineRules(): array
{
    $rules = parent::defineRules();

    // These attributes have real validation — implicitly safe for listed scenarios
    $rules[] = [['name', 'handle'], 'required',
        'on' => [self::SCENARIO_DEFAULT, self::SCENARIO_LIVE]];
    $rules[] = [['batchSize'], 'integer', 'min' => 1, 'max' => 500,
        'on' => [self::SCENARIO_DEFAULT, self::SCENARIO_LIVE]];

    // These attributes need no validation but must be assignable from forms.
    // Include SCENARIO_ESSENTIALS so draft saves also pick them up.
    $rules[] = [['cockpitId', 'cockpitInstanceId'], 'safe',
        'on' => [self::SCENARIO_DEFAULT, self::SCENARIO_LIVE, self::SCENARIO_ESSENTIALS]];

    return $rules;
}
```

**The `'safe'` validator does no validation.** Its only purpose is to mark attributes as eligible for mass assignment. Use it when a native attribute needs to come through from CP form submissions but has no validation requirements.

**If you omit the `'on'` parameter**, the rule applies to all scenarios (equivalent to listing every scenario). This is fine for attributes that should always be assignable:

```php
// Also works — safe in all scenarios
$rules[] = [['cockpitId', 'cockpitInstanceId'], 'safe'];
```

### The silent drop trap

If a native attribute has no validation rule (and no `'safe'` rule), it won't be in `safeAttributes()` for any scenario. When the CP form submits:

1. The POST body includes `cockpitId=abc-123`
2. `setAttributes()` checks `safeAttributes()` — `cockpitId` is not listed
3. Yii2 calls `onUnsafeAttribute()` — which **silently discards** the value (a debug-level log in dev, nothing in production)
4. `afterSave()` writes the old/null value to the database

No error. No warning. The form appears to save, the value is gone. In `devMode`, Yii2 writes a debug-level log via `onUnsafeAttribute()` — check your Craft logs for "Failed to set unsafe attribute" if you suspect this is happening. In production, there is no signal at all. This is the most common trap when building custom elements with native attributes.

### When to use what

| Scenario | Method | Why |
|----------|--------|-----|
| Service / queue job / migration setting native attrs | `$element->attr = $value` | You control the assignment, no safe check needed |
| Programmatically setting custom field values | `$element->setFieldValue('handle', $value)` | Routes through field normalization and behavior storage |
| Programmatically setting multiple custom fields | `$element->setFieldValues([...])` | Convenience wrapper, calls `setFieldValue()` per entry |
| CP form saving native attrs | Automatic via `setAttributes()` | Requires the attribute to be safe (has a rule or `'safe'` marker) |
| CP form saving custom fields | Automatic via `setFieldValuesFromRequest()` | Bypasses safe checks, iterates editable fields from layout |
| Controller manually applying POST data | `$element->setAttributesFromRequest($values)` | Delegates to `setAttributes()`, same safe checks apply |
| Setting from request with field normalization | `$element->setFieldValueFromRequest('handle', $value)` | Calls `normalizeValueFromRequest()` immediately (not lazy) |

### Custom field value lifecycle

Custom field values go through a normalization and serialization chain:

```
Form POST → normalizeValueFromRequest() → stored on behavior → [lazy] normalizeValue() on read
                                                                         ↓
                                              serializeValueForDb() → content JSON column
                                                                         ↓
                                              afterElementSave() → relational/Matrix tables
```

- **`normalizeValueFromRequest()`** — transforms raw POST data into the field's working type. Called immediately during `setFieldValueFromRequest()`.
- **`normalizeValue()`** — transforms stored/raw values into the field's working type. Called lazily on first `getFieldValue()`. Skipped if already normalized from request.
- **`serializeValueForDb()`** — converts the working value back to a DB-storable format. Called during the element save pipeline for fields with a `dbType()`.
- **`afterElementSave()`** — persists complex data (relations, nested elements). Called from `Element::afterSave()`.

### Native fields in the field layout

Native fields (`BaseNativeField` subclasses) map directly to element attributes. They render form inputs whose names land in the native attribute stream (not the `fields` namespace). Examples: Title, Slug, Post Date, Expiry Date.

When you build a custom element, register native fields so admins can position your attributes in the field layout designer:

```php
Event::on(
    FieldLayout::class,
    FieldLayout::EVENT_DEFINE_NATIVE_FIELDS,
    static function(DefineFieldLayoutFieldsEvent $event) {
        if ($event->sender->type === MyElement::class) {
            $event->fields[] = CockpitIdField::class;
        }
    }
);
```

The native field class maps to the element attribute:

```php
class CockpitIdField extends BaseNativeField
{
    public string $attribute = 'cockpitId';
    // ...
}
```

Because `cockpitId` is a native attribute rendered outside the `fields` namespace, it flows through `setAttributes()` on save — so it must be safe. See `fields.md` for full native field implementation patterns.

## Element Query — `beforePrepare()`

```php
protected function beforePrepare(): bool
{
    $this->joinElementTable(Table::MY_ELEMENTS);

    $this->query->addSelect([
        'my_elements.externalId',
        'my_elements.categoryId',
        'my_elements.postDate',
        'my_elements.expiryDate',
    ]);

    if ($this->externalId) {
        $this->subQuery->andWhere(Db::parseParam('my_elements.externalId', $this->externalId));
    }

    if ($this->postDate) {
        $this->subQuery->andWhere(Db::parseDateParam('my_elements.postDate', $this->postDate));
    }

    return parent::beforePrepare();
}
```

**Convention:** Always `addSelect()`, never `select()` on `$this->query`. Always include `postDate` and `expiryDate`.

## Status from Dates

Status must be computed, not stored:

```php
public function getStatus(): ?string
{
    if (!$this->enabled || !$this->enabledForSite) {
        return self::STATUS_DISABLED;
    }

    $now = DateTimeHelper::currentUTCDateTime();

    if ($this->postDate && $this->postDate > $now) {
        return self::STATUS_PENDING;
    }

    if ($this->expiryDate && $this->expiryDate <= $now) {
        return self::STATUS_EXPIRED;
    }

    return self::STATUS_LIVE;
}
```

## Authorization

Override these to control who can do what. Base implementations return `false` and fire authorization events. Always call `parent::` to preserve the event chain:

```php
protected function canView(User $user): bool
{
    if (parent::canView($user)) {
        return true;
    }

    return $user->can("my-plugin:view:{$this->getCategoryUid()}");
}

protected function canSave(User $user): bool
{
    if (parent::canSave($user)) {
        return true;
    }

    return $user->can("my-plugin:manage:{$this->getCategoryUid()}");
}

protected function canDelete(User $user): bool
{
    if (parent::canDelete($user)) {
        return true;
    }

    return $user->can("my-plugin:manage:{$this->getCategoryUid()}");
}

public function canCreateDrafts(User $user): bool
{
    return $this->canSave($user);
}
```

Full authorization method list: `canView()`, `canSave()`, `canDelete()`, `canDeleteForSite()`, `canDuplicate()`, `canDuplicateAsDraft()`, `canCreateDrafts()`, `canCopy()`.

Each has a corresponding event: `EVENT_AUTHORIZE_VIEW`, `EVENT_AUTHORIZE_SAVE`, etc.

## Drafts and Revisions

Enable with `hasDrafts()` (static) and `hasRevisions()` (instance) — `hasDrafts()` returning `true` is required for `hasRevisions()` to work:

```php
public static function hasDrafts(): bool
{
    return true;
}

public function hasRevisions(): bool
{
    return true;
}
```

### Draft-Aware Logic

Always check draft/revision status before triggering side effects:

```php
public function afterSave(bool $isNew): void
{
    // Write to custom table regardless (drafts need their data too)
    $this->_saveRecord($isNew);

    // But don't trigger external side effects for drafts
    if (!$this->getIsDraft() && !$this->getIsRevision()) {
        $this->_syncToExternalService();
    }

    parent::afterSave($isNew);
}
```

### Key Draft/Revision Methods

```php
$this->getIsDraft()              // Is this a draft?
$this->getIsRevision()           // Is this a revision?
$this->getIsCanonical()          // Is this the canonical (live) version?
$this->getIsDerivative()         // Is this a draft or revision?
$this->getIsUnpublishedDraft()   // Draft that was never published?
$this->getCanonical()            // Get the canonical element
$this->mergeCanonicalChanges()   // Apply canonical changes to a draft
```

## Field Layouts

Override `getFieldLayout()` to return the correct field layout for your element:

```php
public function getFieldLayout(): ?FieldLayout
{
    if ($this->categoryId) {
        $category = MyPlugin::$plugin->getCategories()->getCategoryById($this->categoryId);
        if ($category) {
            return $category->getFieldLayout();
        }
    }

    return parent::getFieldLayout();
}
```

For element types with a single field layout:

```php
public function getFieldLayout(): ?FieldLayout
{
    return Craft::$app->getFields()->getLayoutByType(static::class);
}
```

### `defineFieldLayouts()` for Sources

Controls which field layouts are available for a given source in the CP:

```php
protected static function defineFieldLayouts(?string $source): array
{
    if ($source !== null && preg_match('/^category:(.+)/', $source, $matches)) {
        $category = MyPlugin::$plugin->getCategories()->getCategoryByUid($matches[1]);
        if ($category) {
            return [$category->getFieldLayout()];
        }
    }

    // Return all field layouts when source is null
    return Craft::$app->getFields()->getLayoutsByType(static::class);
}
```

## URI/Routing

For elements that have their own URLs:

```php
public static function hasUris(): bool
{
    return true;
}

public function getUriFormat(): ?string
{
    $siteSettings = $this->getCategory()->getSiteSettings();
    $siteSetting = $siteSettings[$this->siteId] ?? null;

    return $siteSetting?->uriFormat;
}

public function getRoute(): mixed
{
    $siteSettings = $this->getCategory()->getSiteSettings();
    $siteSetting = $siteSettings[$this->siteId] ?? null;

    if ($siteSetting?->template) {
        return ['templates/render', ['template' => $siteSetting->template]];
    }

    return parent::getRoute();
}
```

## Searchable Attributes

Define which element attributes are indexed for search:

```php
protected static function defineSearchableAttributes(): array
{
    return ['externalId', 'title'];
}
```

Custom search keywords for complex attributes:

```php
protected function searchKeywords(string $attribute): string
{
    if ($attribute === 'categoryName') {
        return $this->getCategory()?->name ?? '';
    }

    return parent::searchKeywords($attribute);
}
```

## Propagation

Control which sites an element exists on. The base `Element::getSupportedSites()` checks `isLocalized()` — if false (the default), returns primary site only. If true, returns all sites. Most element types override this with their own logic.

`NestedElementTrait` does NOT provide `getSupportedSites()` or `isLocalized()`. Nested element types that need multi-site propagation must override these themselves. Matrix entries work because `Entry::getSupportedSites()` delegates to `$this->getField()->getSupportedSitesForElement($this)` when `fieldId` is set. Address elements don't override either method, so they exist on the primary site only — even when their owner exists on multiple sites.

```php
public function getSupportedSites(): array
{
    $sites = [];
    foreach ($this->getCategory()->getSiteSettings() as $siteId => $settings) {
        $sites[] = [
            'siteId' => $siteId,
            'propagationMethod' => PropagationMethod::None,
            'enabledByDefault' => $settings->enabledByDefault,
        ];
    }

    return $sites;
}
```

## CP Edit Pages

Custom elements need a CP edit page for creating and editing instances. Craft provides a built-in `elements/edit` action that handles drafts, revisions, auto-saving, and slide-out editing automatically.

### Route Registration + getCpEditUrl()

Register a CP URL rule pointing to `elements/edit`, and implement `getCpEditUrl()` on your element:

```php
// In your plugin's init() or via EVENT_REGISTER_CP_URL_RULES
Event::on(UrlManager::class, UrlManager::EVENT_REGISTER_CP_URL_RULES,
    function(RegisterUrlRulesEvent $event) {
        $event->rules['my-plugin'] = ['template' => 'my-plugin/_index.twig'];
        $event->rules['my-plugin/<elementId:\\d+>'] = 'elements/edit';
    }
);
```

```php
// On the element class
public function getCpEditUrl(): ?string
{
    return UrlHelper::cpUrl("my-plugin/{$this->id}");
}
```

When `getCpEditUrl()` returns a URL, Craft generates edit links in the element index, and the `elements/edit` action handles the entire edit page — field layout rendering, draft/revision management, and auto-saving. No custom controller needed for standard editing.

### Custom Edit Pages with asCpScreen()

For non-standard editing (custom tabs, extra UI outside the field layout), build your own controller action using `CpScreenResponseBehavior`:

```php
public function actionEdit(?int $elementId = null): Response
{
    $element = $elementId
        ? Craft::$app->getElements()->getElementById($elementId, MyElement::class)
        : new MyElement();

    if ($elementId && !$element) {
        throw new NotFoundHttpException('Element not found');
    }

    /** @var Response|CpScreenResponseBehavior $response */
    $response = $this->asCpScreen()
        ->title($element->title ?? Craft::t('my-plugin', 'New Item'))
        ->editUrl($element->getCpEditUrl())
        ->docTitle($element->title ?? Craft::t('my-plugin', 'New Item'))
        ->action('my-plugin/items/save')
        ->redirectUrl('my-plugin')
        ->contentTemplate('my-plugin/items/_edit', [
            'element' => $element,
        ]);

    return $response;
}
```

`asCpScreen()` automatically handles both full-page and slide-out (modal) contexts — no need to detect which mode is active.

### Extending User Edit Screens

Craft 5.0 ships `UsersController::EVENT_DEFINE_EDIT_SCREENS`, fired from `EditUserTrait::asEditUserScreen()` between the native screens (Profile, Permissions, Preferences, Addresses) and the auth screens (Password & Verification, Passkeys). Plugin-defined screens render as left-nav items alongside the natives — no template hacks or sidebar workarounds needed.

```php
use craft\controllers\UsersController;
use craft\events\DefineEditUserScreensEvent;
use craft\helpers\UrlHelper;
use yii\base\Event;

Event::on(
    UsersController::class,
    UsersController::EVENT_DEFINE_EDIT_SCREENS,
    function(DefineEditUserScreensEvent $event): void {
        // Permission gate first — same pattern as the controller's beforeAction()
        if (!MyController::callerHasViewPermission()) {
            return;
        }

        $userId = $event->editedUser->id;
        $event->screens['my-screen'] = [
            'label' => Craft::t('my-plugin', 'My Screen'),
            'url' => UrlHelper::cpUrl("my-plugin/users/{$userId}/my-screen"),
        ];
    },
);
```

**Payload:** `DefineEditUserScreensEvent` carries `currentUser`, `editedUser`, and `screens` (`array<string, array>` keyed by screen ID — each entry requires `label`, `url` is optional and defaults to `myaccount/<id>` or `users/<id>/<id>`).

**When to use sidebar instead:** `Element::EVENT_DEFINE_SIDEBAR_HTML` filtered to `User::class` is still the right tool for adding read-only metadata or status pointers to the right meta-sidebar — but for navigable screens, use `EVENT_DEFINE_EDIT_SCREENS`.

### Propagation Method Settings UI

To let admins configure propagation per source (e.g., per category or section), include a propagation method select in the source's settings template:

```twig
{% import '_includes/forms.twig' as forms %}

{{ forms.selectField({
    label: 'Propagation Method'|t('app'),
    id: 'propagationMethod',
    name: 'propagationMethod',
    value: category.propagationMethod.value,
    options: [
        { label: 'Only save to the site it was created in'|t('app'), value: 'none' },
        { label: 'Save to all sites the owner element is saved in'|t('app'), value: 'all' },
        { label: 'Save to other sites in the same site group'|t('app'), value: 'siteGroup' },
        { label: 'Save to other sites with the same language'|t('app'), value: 'language' },
    ],
}) }}
```

The saved value feeds into `getSupportedSites()` on the element, which returns the `propagationMethod` per site.

### Field Layout Designer in Settings

To let admins design the field layout for your element type, include Craft's field layout designer in your settings template:

```twig
{% import '_includes/forms.twig' as forms %}

{{ forms.fieldLayoutDesignerField({
    fieldLayout: category.getFieldLayout(),
}) }}
```

In the controller, save the field layout from the POST body:

```php
$fieldLayout = Craft::$app->getFields()->assembleLayoutFromPost();
$fieldLayout->type = MyElement::class;
$category->setFieldLayout($fieldLayout);
```

### Site-Specific Settings (URI Format, Template, Enabled)

For elements with URIs, create per-site settings with URI format and template path:

```twig
{% set allSites = craft.app.sites.getAllSites() %}

{% for site in allSites %}
    <div class="field">
        <div class="heading"><label>{{ site.name }}</label></div>
        {{ forms.lightswitchField({
            label: 'Enabled'|t('app'),
            name: "sites[#{site.id}][enabled]",
            on: siteSettings[site.id].enabled ?? false,
        }) }}
        {{ forms.textField({
            label: 'URI Format'|t('app'),
            name: "sites[#{site.id}][uriFormat]",
            value: siteSettings[site.id].uriFormat ?? '',
            placeholder: 'items/{slug}',
        }) }}
        {{ forms.textField({
            label: 'Template'|t('app'),
            name: "sites[#{site.id}][template]",
            value: siteSettings[site.id].template ?? '',
            placeholder: 'items/_entry',
        }) }}
    </div>
{% endfor %}
```

## Preview Targets

Define where an element can be previewed. Craft shows these as options in the edit page's preview menu.

### Implementing previewTargets()

Override `previewTargets()` on the element class:

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

### Registering Preview Targets via Event

Add preview targets to elements you don't own:

```php
use craft\base\Element;
use craft\events\RegisterPreviewTargetsEvent;

Event::on(
    MyElement::class,
    Element::EVENT_REGISTER_PREVIEW_TARGETS,
    static function(RegisterPreviewTargetsEvent $event) {
        /** @var MyElement $element */
        $element = $event->sender;

        if ($element->externalId) {
            $event->previewTargets[] = [
                'label' => Craft::t('my-plugin', 'External Preview'),
                'url' => "https://example.com/preview/{$element->externalId}",
            ];
        }
    }
);
```

## Eager Loading

For custom relations, implement `eagerLoadingMap()` — returns source→target ID mappings:

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

## Generated Fields (5.8.0)

Generated fields are computed values stored on elements. Unlike native fields (entered by editors) or custom fields (configured by admins), generated fields are defined on the field layout and their values are computed from an object template on every save.

### How they work

Generated fields are configured on `FieldLayout`, not on the element class. Each generated field has:
- `uid` — unique identifier
- `name` — display name
- `handle` — access handle (like custom field handles)
- `template` — an object template (Twig) evaluated against the element at save time

```php
// Access generated field values like custom fields
$element->getGeneratedFieldValues();

// Individual value
$value = $element->{$handle};
```

### Storage and querying

Generated field values are stored in the database. They can be:
- Queried as element query params: `MyElement::find()->myGeneratedHandle('> 100')`
- Used in sort options: `.orderBy('myGeneratedHandle DESC')`
- Displayed in table and card views on element indexes

Since 5.9.0, `true`/`false`/`null`/integer/float values are normalized to appropriate types.

### Use cases

- **Computed summaries** — count related entries, sum values from nested content
- **Denormalized data** — hoist a nested field value to the top level for querying/sorting
- **Binary criteria** — flag elements matching a condition (e.g., spending > threshold)
- **Sequential numbering** — use `seq()` for auto-incrementing reference numbers
- **Search-optimized text** — strip markup from rich text for cleaner search indexing

### Limitations

- Values are evaluated sequentially at save time — referencing one generated field from another sees pre-save values
- Values from related elements can become stale between saves
- Condition builders treat values as strings (text operators: "starts with", "contains")
- Not directly editable in the CP — they're computed, not authored

## Soft Delete and Garbage Collection

Elements use soft delete by default (`dateDeleted` column). Craft's garbage collector purges after the configured retention period. Don't bypass with hard deletes unless you have a specific reason.

For plugin-level cleanup of expired or stale elements, listen to `Gc::EVENT_RUN` instead of running cleanup on every request:

```php
use craft\services\Gc;

Event::on(Gc::class, Gc::EVENT_RUN, function(\yii\base\Event $event) {
    // Batch delete expired elements — runs during Craft's GC cycle, not on every request
    MyPlugin::$plugin->getMyService()->deleteExpiredElements();
});
```

Never run synchronous cleanup in `init()` or request-level event handlers — it adds latency to every CP page load. For bulk element deletion, use a queue job or a single batch query where possible.

## Element Events Reference

Element.php fires ~40 events. Key categories:

**Lifecycle events** (fire in order during save):
`EVENT_BEFORE_SAVE` → `EVENT_AFTER_SAVE` → `EVENT_AFTER_PROPAGATE`

**Delete/restore**: `EVENT_BEFORE_DELETE`, `EVENT_AFTER_DELETE`, `EVENT_BEFORE_RESTORE`, `EVENT_AFTER_RESTORE`

**Authorization** (fired from `canView()`, `canSave()`, etc. — see `permissions.md` for full patterns):
`EVENT_AUTHORIZE_VIEW`, `EVENT_AUTHORIZE_SAVE`, `EVENT_AUTHORIZE_CREATE_DRAFTS`, `EVENT_AUTHORIZE_DUPLICATE`, `EVENT_AUTHORIZE_DELETE`, `EVENT_AUTHORIZE_DELETE_FOR_SITE`

**Registration** (extend via events):
`EVENT_REGISTER_SOURCES`, `EVENT_REGISTER_FIELD_LAYOUTS`, `EVENT_REGISTER_ACTIONS`, `EVENT_REGISTER_EXPORTERS`, `EVENT_REGISTER_SEARCHABLE_ATTRIBUTES`, `EVENT_REGISTER_SORT_OPTIONS`, `EVENT_REGISTER_TABLE_ATTRIBUTES`, `EVENT_REGISTER_DEFAULT_TABLE_ATTRIBUTES`, `EVENT_REGISTER_CARD_ATTRIBUTES`, `EVENT_REGISTER_DEFAULT_CARD_ATTRIBUTES`, `EVENT_REGISTER_PREVIEW_TARGETS`

**Customization**:
`EVENT_DEFINE_SIDEBAR_HTML`, `EVENT_DEFINE_METADATA`, `EVENT_DEFINE_ADDITIONAL_BUTTONS`, `EVENT_DEFINE_ATTRIBUTE_HTML`, `EVENT_DEFINE_EAGER_LOADING_MAP`, `EVENT_SET_ROUTE`, `EVENT_DEFINE_KEYWORDS`, `EVENT_DEFINE_CACHE_TAGS`, `EVENT_DEFINE_URL`

**Structures**: `EVENT_BEFORE_MOVE_IN_STRUCTURE`, `EVENT_AFTER_MOVE_IN_STRUCTURE`

For the full list and event class signatures, `WebFetch` https://craftcms.com/docs/5.x/extend/events.html
