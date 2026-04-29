# Control Panel — Templates, Permissions, UI

Complete reference for CP extension points: templates, navigation, settings pages, utilities, widgets, slideouts, and AJAX patterns. For controller patterns (CRUD, webhooks, API, routing), see `controllers.md`.

## Documentation

- CP templates: https://craftcms.com/docs/5.x/extend/cp-templates.html
- CP sections: https://craftcms.com/docs/5.x/extend/cp-section.html
- CP edit pages: https://craftcms.com/docs/5.x/extend/cp-edit-pages.html
- Permissions: https://craftcms.com/docs/5.x/extend/user-permissions.html
- Utilities: https://craftcms.com/docs/5.x/extend/utilities.html
- Widget types: https://craftcms.com/docs/5.x/extend/widget-types.html

## Common Pitfalls

- Not wrapping settings UI in `allowAdminChanges` checks -- settings should be read-only in production.
- Hardcoding plugin name strings instead of using `Craft::t()` with the plugin handle translation category.
- Missing `actionInput()` and `redirectInput()` in full-page forms -- form submission won't route correctly.
- Not passing `errors: entity.getErrors('field')` to form macros -- validation errors won't display.
- Registering CP nav items without checking user permissions first -- users see nav items they can't access, leading to 403 errors.
- Using raw HTML in CP templates instead of Craft's form macros -- loses consistency, dark mode support, and accessibility features.
- Not handling the `readonly` state for fields when `allowAdminChanges` is false -- users can edit values they can't save.
- Forgetting `csrfInput()` in custom forms that don't use `fullPageForm` -- POST requests will be rejected.
- Using `size` attribute with `type: 'number'` on `textField` -- browsers ignore the HTML `size` attribute on `<input type="number">`. Craft's own Number field works around this by using `type: 'text'` with `inputmode: 'numeric'`. For number inputs, constrain width with `inputAttributes: { style: 'width: 6rem' }` or switch to a text input with `inputmode="numeric"` pattern.
- Expensive `badgeCount` computation in `getCpNavItem()` -- this method runs on **every CP page load** across the entire install, not just your plugin's pages. Badge counts must be extremely cheap: use a cached value (invalidated on relevant saves) or a simple indexed `COUNT(*)` query. Never run complex queries, N+1 patterns, or element queries with eager loading here.

## Contents

- [CP Templates](#cp-templates) — form macros, editable tables, tabbed settings, VueAdminTable
- [CP Navigation](#cp-navigation)
- [Settings Pages](#settings-pages) — settings model, env var support, split settings pages (savePluginSettings footgun)
- [Utility Pages](#utility-pages)
- [Dashboard Widgets](#dashboard-widgets)
- [Slideout Editors](#slideout-editors)
- [Ajax Endpoints for CP](#ajax-endpoints-for-cp)
- [CP Alerts and Notices](#cp-alerts-and-notices)
- [Form Macros Reference](#form-macros-reference)
- [CP UI Patterns](#cp-ui-patterns) — tri-state inheritance, status indicators, field warnings, CSS variables, `[hidden]` gotcha
- [Condition Builders](#condition-builders)
- [Asset Bundles](#asset-bundles)
- [Permissions](#permissions)
- [CP Markup Patterns](#cp-markup-patterns) — sidebar badges, notice/warning blocks, tip/warning on form fields
- [Read-Only Mode (allowAdminChanges)](#read-only-mode-allowadminchanges) — controller setup, template patterns, disabled fields

## CP Templates

### Form Macros

```twig
{% import '_includes/forms.twig' as forms %}

{{ forms.textField({
    label: 'Name'|t('my-plugin'), id: 'name', name: 'name',
    value: item.name, errors: item.getErrors('name'), required: true, first: true,
}) }}

{{ forms.lightswitchField({
    label: 'Enable Sync'|t('my-plugin'), id: 'enableSync', name: 'enableSync',
    on: settings.enableSync,
}) }}

{{ forms.selectField({
    label: 'Batch Size'|t('my-plugin'), id: 'batchSize', name: 'batchSize',
    value: item.batchSize, options: batchSizeOptions,
}) }}
```

### Editable Table

Two variants: `editableTableField` (with label, instructions, error wrapper) and `editableTable` (raw table only, for embedding in custom layouts).

#### Basic usage

```twig
{{ forms.editableTableField({
    label: 'Site Mappings'|t('my-plugin'),
    instructions: 'Map each site to a URI format.'|t('my-plugin'),
    id: 'sites',
    name: 'sites',
    cols: {
        siteId: { type: 'select', heading: 'Site'|t('my-plugin'), options: siteOptions },
        uriFormat: { type: 'singleline', heading: 'URI Format'|t('my-plugin'), placeholder: 'items/{slug}' },
        enabled: { type: 'lightswitch', heading: 'Enabled'|t('my-plugin') },
    },
    rows: siteRows,
    allowAdd: true,
    allowDelete: true,
    allowReorder: true,
    errors: settings.getErrors('sites'),
}) }}
```

#### Column types

| Type | Renders | Value in POST data |
|------|---------|-------------------|
| `singleline` | Text input | `string` |
| `multiline` | Textarea (auto-grows) | `string` |
| `number` | Number input | `string` (cast server-side) |
| `checkbox` | Centered checkbox | `'1'` or absent |
| `lightswitch` | Craft lightswitch toggle | `'1'` or `''` |
| `select` | Dropdown (requires `options`) | Selected value `string` |
| `date` | Date picker | `string` (Y-m-d format) |
| `time` | Time picker | `string` (H:i format) |
| `color` | Color picker | `string` (hex) |
| `heading` | Non-editable display text | Not submitted |
| `html` | Raw HTML (non-editable) | Not submitted |
| `template` | Render a Twig template per cell | Depends on template |

Column config keys: `type` (required), `heading`, `placeholder`, `class`, `width` (CSS width like `'30%'`), `thin` (boolean, minimal width), `options` (for `select`), `info` (tooltip text).

#### Raw table (no field wrapper)

```twig
{{ forms.editableTable({
    id: 'mappings',
    name: 'mappings',
    cols: cols,
    rows: rows,
    allowAdd: true,
    allowDelete: true,
    allowReorder: true,
    defaultValues: { enabled: true, batchSize: '50' },
    minRows: 1,
    maxRows: 10,
    staticRows: false,
}) }}
```

Additional settings: `minRows`, `maxRows` (enforce row count limits), `defaultValues` (hash of column handle → default value for new rows), `staticRows` (when `true`, rows can't be added/deleted — useful for fixed configurations like site mappings where you show one row per site).

#### Server-side handling

POST data arrives as a nested array keyed by row ID:

```php
// In controller action
$rows = $this->request->getBodyParam('sites');
// $rows = [
//     'row1' => ['siteId' => '1', 'uriFormat' => 'items/{slug}', 'enabled' => '1'],
//     'row2' => ['siteId' => '2', 'uriFormat' => 'articles/{slug}', 'enabled' => ''],
// ]

// Normalize — strip row IDs, cast types
$normalized = [];
foreach ($rows as $row) {
    $normalized[] = [
        'siteId' => (int)$row['siteId'],
        'uriFormat' => $row['uriFormat'] ?? '',
        'enabled' => (bool)($row['enabled'] ?? false),
    ];
}
```

Row IDs are auto-generated (e.g., `row1`, `new2`). Never rely on them — iterate the array values. New rows added by the user have IDs prefixed with `new`. When repopulating on validation failure, pass the raw `$rows` back as `rows` so the user's edits aren't lost.

#### Populating rows from a model

```php
// In controller, before rendering
$siteRows = [];
foreach ($settings->siteMappings as $mapping) {
    $siteRows[] = [
        'siteId' => $mapping['siteId'],
        'uriFormat' => $mapping['uriFormat'],
        'enabled' => $mapping['enabled'],
    ];
}

// Pass to template
return $this->renderTemplate('my-plugin/settings', [
    'siteRows' => $siteRows,
    'siteOptions' => $this->_getSiteOptions(),
]);
```

#### JS interaction (Garnish)

The table auto-initializes as a `Craft.EditableTable` instance. Access it for programmatic manipulation:

```javascript
// Get the instance (auto-attached to the container)
var table = $('#sites').data('editable-table');

// Add a row programmatically
table.addRow(false); // false = don't focus the new row

// Listen for row changes
$('#sites').on('addRow', function(ev) {
    // A row was added
});
$('#sites').on('deleteRow', function(ev) {
    // A row was deleted
});
```

### CP Layout

```twig
{% extends '_layouts/cp.twig' %}
{% set title = 'Settings'|t('my-plugin') %}
{% set selectedSubnavItem = 'settings' %}
{% set fullPageForm = true %}

{% block content %}
    {{ actionInput('my-plugin/settings/save') }}
    {{ redirectInput('my-plugin/settings') }}
    {# Form fields here #}
{% endblock %}
```

### Tabbed Settings Pages

Two approaches for multi-tab CP pages: Twig-level tabs (template-driven) and PHP-level tabs (controller-driven via `asCpScreen()`).

#### Twig-level tabs

Set the `tabs` variable in your template. Each tab links to a different URL or anchor. The CP layout renders the tab bar automatically when `tabs` has more than one entry.

```twig
{% extends '_layouts/cp.twig' %}
{% set title = 'Settings'|t('my-plugin') %}
{% set selectedSubnavItem = 'settings' %}
{% set fullPageForm = true %}

{% set tabs = {
    general: { label: 'General'|t('my-plugin'), url: url('my-plugin/settings/general') },
    sync: { label: 'Sync'|t('my-plugin'), url: url('my-plugin/settings/sync') },
    advanced: { label: 'Advanced'|t('my-plugin'), url: url('my-plugin/settings/advanced') },
} %}

{% set selectedTab = 'general' %}

{% block content %}
    {{ actionInput('my-plugin/settings/save-general') }}
    {{ redirectInput('my-plugin/settings/general') }}
    {# Tab-specific form fields #}
{% endblock %}
```

Each tab is a separate template (or a shared template with conditional blocks). The `selectedTab` variable highlights the active tab. Register CP URL rules for each tab path.

#### Anchor-based tabs (single page)

For tabs that switch content without a page reload, use anchor-based tab IDs. Craft's JS handles showing/hiding containers whose IDs match the tab anchors:

```twig
{% set tabs = {
    general: { label: 'General'|t('my-plugin'), url: '#general' },
    mapping: { label: 'Mapping'|t('my-plugin'), url: '#mapping' },
    advanced: { label: 'Advanced'|t('my-plugin'), url: '#advanced' },
} %}

{% block content %}
    {{ actionInput('my-plugin/settings/save') }}
    {{ redirectInput('my-plugin/settings') }}

    <div id="general">
        {# General settings fields #}
    </div>

    <div id="mapping" class="hidden">
        {# Mapping settings fields #}
    </div>

    <div id="advanced" class="hidden">
        {# Advanced settings fields #}
    </div>
{% endblock %}
```

Craft's CP JavaScript automatically shows the panel matching the selected tab and hides the others. Initial state: all panels except the first get `class="hidden"`.

#### PHP-level tabs via asCpScreen()

For controller-driven screens (custom element edit pages, non-template responses), use the `tabs()` fluent method on `CpScreenResponseBehavior`:

```php
/** @var Response|CpScreenResponseBehavior $response */
$response = $this->asCpScreen()
    ->title($item->title ?? Craft::t('my-plugin', 'New Item'))
    ->action('my-plugin/items/save')
    ->redirectUrl('my-plugin/items')
    ->tabs([
        'content' => [
            'label' => Craft::t('my-plugin', 'Content'),
            'url' => '#content',
        ],
        'settings' => [
            'label' => Craft::t('my-plugin', 'Settings'),
            'url' => '#settings',
        ],
    ])
    ->contentTemplate('my-plugin/items/_edit', [
        'item' => $item,
    ]);
```

Or add tabs individually with `addTab()`:

```php
$response->addTab(
    id: 'integrations',
    label: Craft::t('my-plugin', 'Integrations'),
    url: '#integrations',
);
```

`addTab()` accepts optional `class` (string or array) and `visible` (bool, default `true`) parameters. Set `visible: false` to hide a tab conditionally.

### VueAdminTable

```twig
{% js %}
new Craft.VueAdminTable({
    columns: [
        { name: '__slot:title', title: Craft.t('my-plugin', 'Name') },
        { name: 'handle', title: Craft.t('my-plugin', 'Handle') },
    ],
    container: '#items-vue-admin-table',
    deleteAction: 'my-plugin/items/delete-item',
    reorderAction: 'my-plugin/items/reorder-items',
    tableData: {{ items|json_encode(constant('JSON_HEX_TAG'))|raw }},
});
{% endjs %}
```

## CP Navigation

### Plugin CP Section

Enable CP section in the plugin class, then override `getCpNavItem()` for subnav:

```php
public bool $hasCpSection = true;

public function getCpNavItem(): ?array
{
    $item = parent::getCpNavItem();
    // Badge count must be cheap — runs on every CP page load, not just this plugin's pages
    $item['badgeCount'] = Craft::$app->getCache()->getOrSet('my-plugin:pending-count', fn() =>
        MyElement::find()->status('pending')->count(), 300);
    $item['subnav'] = [
        'dashboard' => ['label' => Craft::t('my-plugin', 'Dashboard'), 'url' => 'my-plugin'],
        'items' => ['label' => Craft::t('my-plugin', 'Items'), 'url' => 'my-plugin/items'],
    ];

    // Gate subnav items behind permissions
    if (Craft::$app->getUser()->getIdentity()?->can('my-plugin:settings')) {
        $item['subnav']['settings'] = [
            'label' => Craft::t('my-plugin', 'Settings'),
            'url' => 'my-plugin/settings',
        ];
    }
    return $item;
}
```

### Module CP Navigation

Modules cannot use `hasCpSection`. Register nav items via event:

```php
Event::on(Cp::class, Cp::EVENT_REGISTER_CP_NAV_ITEMS,
    function(RegisterCpNavItemsEvent $event) {
        if (!Craft::$app->getUser()->getIdentity()?->can('accessModule')) {
            return;
        }
        $event->navItems[] = [
            'url' => 'my-module',
            'label' => Craft::t('my-module', 'My Module'),
            'icon' => 'gear',
            'badgeCount' => 0,
        ];
    }
);
```

### Icon Options

The `icon` key accepts a Craft icon identifier (`'gear'`, `'wand'`, `'magnifying-glass'`) or inline SVG. Check `vendor/craftcms/cms/src/icons/` for available built-in icons.

## Settings Pages

Three pieces: model, plugin class methods, and template.

### Settings Model

```php
class Settings extends Model
{
    public string $apiUrl = '';
    public string $apiKey = '';
    public bool $enableSync = false;
    public int $batchSize = 100;

    protected function defineRules(): array
    {
        $rules = parent::defineRules();
        $rules[] = [['apiUrl', 'apiKey'], 'required'];
        $rules[] = [['batchSize'], 'integer', 'min' => 1, 'max' => 1000];
        return $rules;
    }
}
```

### Plugin Class Methods

```php
protected function createSettingsModel(): ?Model
{
    return new Settings();
}

protected function settingsHtml(): ?string
{
    return Craft::$app->getView()->renderTemplate('my-plugin/_settings.twig', [
        'settings' => $this->getSettings(),
    ]);
}
```

### Settings Template with Env Var Support

```twig
{% import '_includes/forms.twig' as forms %}
{% set allowAdminChanges = craft.app.config.general.allowAdminChanges %}

{{ forms.autosuggestField({
    label: 'API URL'|t('my-plugin'), id: 'apiUrl', name: 'apiUrl',
    value: settings.apiUrl, suggestEnvVars: true, suggestAliases: true,
    required: true, disabled: not allowAdminChanges,
}) }}

{{ forms.autosuggestField({
    label: 'API Key'|t('my-plugin'), id: 'apiKey', name: 'apiKey',
    value: settings.apiKey, suggestEnvVars: true,
    required: true, disabled: not allowAdminChanges,
}) }}

{{ forms.lightswitchField({
    label: 'Enable Sync'|t('my-plugin'), id: 'enableSync', name: 'enableSync',
    on: settings.enableSync, disabled: not allowAdminChanges,
}) }}
```

`disabled: not allowAdminChanges` on every field prevents editing in production. `suggestEnvVars: true` shows env var dropdown when user types `$`. At runtime, resolve with `App::parseEnv($settings->apiUrl)`.

### Split Settings Pages (savePluginSettings footgun)

`Craft::$app->getPlugins()->savePluginSettings($plugin, $settings)` only persists the keys present in `$settings`. Internally it calls `$pluginSettings->toArray(array_keys($settings))`, meaning any settings NOT submitted in the current request are silently dropped from project config.

If your plugin has tabbed or multi-page settings, each tab's form only submits its own fields. **You must merge with existing settings before saving:**

```php
public function actionSaveGeneralSettings(): ?Response
{
    $this->requirePostRequest();
    $this->requireAdmin();

    $plugin = MyPlugin::getInstance();
    $settings = $plugin->getSettings();

    // Only update the fields from this tab
    $settings->apiUrl = $this->request->getBodyParam('apiUrl');
    $settings->apiKey = $this->request->getBodyParam('apiKey');

    // Save the FULL settings model — all properties are present
    if (!Craft::$app->getPlugins()->savePluginSettings($plugin, $settings->toArray())) {
        $this->setFailFlash(Craft::t('my-plugin', 'Couldn't save settings.'));
        return null;
    }

    $this->setSuccessFlash(Craft::t('my-plugin', 'Settings saved.'));
    return $this->redirectToPostedUrl();
}
```

The key: load the full settings model first, update only the relevant properties, then pass `$settings->toArray()` (all keys). Never pass `$this->request->getBodyParams()` directly to `savePluginSettings()` on a split-settings page — you'll lose every setting not on the current tab.

## Utility Pages

Utilities appear under the "Utilities" CP section as single-page admin tools.

### Utility Class

```php
class MyUtility extends Utility
{
    public static function displayName(): string
    {
        return Craft::t('my-plugin', 'My Utility');
    }

    public static function id(): string { return 'my-utility'; }
    public static function icon(): ?string { return 'wand'; }
    public static function badgeCount(): int { return 0; }

    public static function contentHtml(): string
    {
        return Craft::$app->getView()->renderTemplate('my-plugin/_utilities/my-utility.twig');
    }
}
```

### Utility Template

Does not extend a layout -- Craft wraps it. Use `csrfInput()` since this is not a `fullPageForm`:

```twig
{% import '_includes/forms.twig' as forms %}
<form method="post" accept-charset="UTF-8">
    {{ csrfInput() }}
    {{ actionInput('my-plugin/utility/run-task') }}
    {{ forms.selectField({
        label: 'Action'|t('my-plugin'),
        id: 'action',
        name: 'action',
        options: [
            { label: 'Rebuild Index', value: 'rebuild' },
            { label: 'Clear Cache', value: 'clear' },
        ],
    }) }}
    <button type="submit" class="btn submit">{{ 'Run'|t('my-plugin') }}</button>
</form>
```

### Registration

```php
Event::on(Utilities::class, Utilities::EVENT_REGISTER_UTILITIES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyUtility::class;
    }
);
```

## Dashboard Widgets

Widgets appear on the CP dashboard. Users add and configure them per-instance.

### Widget Class

```php
class RecentItems extends Widget
{
    public int $limit = 5;

    public static function displayName(): string
    {
        return Craft::t('my-plugin', 'Recent Items');
    }

    public static function icon(): ?string { return 'clock'; }
    public static function maxColspan(): ?int { return 2; }

    protected function defineRules(): array
    {
        $rules = parent::defineRules();
        $rules[] = [['limit'], 'integer', 'min' => 1, 'max' => 50];
        return $rules;
    }

    public function getSettingsHtml(): ?string
    {
        return Craft::$app->getView()->renderTemplate(
            'my-plugin/_widgets/recent-items/settings.twig',
            ['widget' => $this],
        );
    }

    public function getBodyHtml(): ?string
    {
        $items = MyPlugin::getInstance()->getItems()->getRecentItems($this->limit);
        return Craft::$app->getView()->renderTemplate(
            'my-plugin/_widgets/recent-items/body.twig',
            ['items' => $items],
        );
    }
}
```

### Widget templates

Settings template (`_components/widgets/recentitems/settings.twig`):

```twig
{% import '_includes/forms.twig' as forms %}

{{ forms.textField({
    label: 'Limit',
    id: 'limit',
    name: 'limit',
    value: widget.limit,
    size: 3,
    type: 'number',
}) }}
```

Body template (`_components/widgets/recentitems/body.twig`):

```twig
{% if items|length %}
<table class="data fullwidth">
    <thead>
        <tr>
            <th>{{ 'Title'|t('app') }}</th>
            <th>{{ 'Date'|t('app') }}</th>
            <th>{{ 'Status'|t('app') }}</th>
        </tr>
    </thead>
    <tbody>
        {% for item in items %}
        <tr>
            <td><a href="{{ item.cpEditUrl }}">{{ item.title }}</a></td>
            <td>{{ item.dateCreated|date('short') }}</td>
            <td>{{ item.status }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<p>{{ 'No recent activity.'|t('my-plugin') }}</p>
{% endif %}
```

### Registration

```php
Event::on(Dashboard::class, Dashboard::EVENT_REGISTER_WIDGET_TYPES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = RecentItems::class;
    }
);
```

## Slideout Editors

### How Slideouts Work

In Craft 5, element chips and cards automatically trigger slideout editors when clicked -- no custom JS needed. Slideouts load the element's edit form in a side panel without leaving the current page.

### Customizing Slideout Content

Override these methods on your element class:

- `getSidebarHtml()` -- sidebar content (metadata fields, status indicators)
- `getMetadataHtml()` -- metadata table at the bottom of the sidebar
- `cpEditUrl()` -- full edit page URL (slideout links to it)

Use `Craft::$app->getRequest()->getAcceptsJson()` to detect slideout context if you need to render differently.

### Triggering Programmatically

```js
// Existing element
Craft.createElementEditor('myplugin\\elements\\MyElement', { elementId: 123, siteId: 1 });

// New element
Craft.createElementEditor('myplugin\\elements\\MyElement', { attributes: { typeId: 5 } });
```

Slideouts appear in: relation fields (clicking chips/cards), element indexes ("Edit" action), inline creation buttons, and any custom UI rendering `_elements/chip.twig`.

## Ajax Endpoints for CP

### Controller Actions

```php
public function actionSaveItem(): Response
{
    $this->requireAcceptsJson();
    $this->requirePostRequest();
    $name = Craft::$app->getRequest()->getRequiredBodyParam('name');
    $item = new Item(['name' => $name]);

    if (!MyPlugin::getInstance()->getItems()->saveItem($item)) {
        return $this->asFailure(Craft::t('my-plugin', 'Could not save item.'), ['errors' => $item->getErrors()]);
    }
    return $this->asSuccess(Craft::t('my-plugin', 'Item saved.'), ['item' => $item->toArray()]);
}
```

`asSuccess()` / `asFailure()` for structured responses, `asJson()` for raw data. Guard with `requireAcceptsJson()` and `requirePostRequest()` / `requirePermission()`.

### JavaScript Side

`Craft.sendActionRequest()` handles CSRF and JSON headers automatically:

```js
Craft.sendActionRequest('POST', 'my-plugin/items/save-item', {
    data: { name: 'New Item' },
}).then((response) => {
    Craft.cp.displayNotice(response.data.message);
}).catch((error) => {
    Craft.cp.displayError(error.response.data.message);
});
```

## CP Alerts and Notices

### System-Wide Alerts

Persistent alerts at the top of every CP page:

```php
Event::on(Cp::class, Cp::EVENT_REGISTER_ALERTS,
    function(RegisterCpAlertsEvent $event) {
        if (empty(MyPlugin::getInstance()->getSettings()->apiKey)) {
            $event->alerts[] = Craft::t('my-plugin',
                'API key is not configured. [Configure it here]({url}).',
                ['url' => 'my-plugin/settings'],
            );
        }
    }
);
```

Alert text supports limited Markdown link syntax: `[link text](url)`.

### Flash Messages

```php
// Controller helper methods (preferred)
$this->setSuccessFlash(Craft::t('my-plugin', 'Item saved.'));
$this->setFailFlash(Craft::t('my-plugin', 'Could not save item.'));

// Direct session access (when not in a controller)
Craft::$app->getSession()->setNotice(Craft::t('my-plugin', 'Item saved.'));
Craft::$app->getSession()->setError(Craft::t('my-plugin', 'Could not save item.'));
```

## Form Macros Reference

All macros live in `_includes/forms.twig`. Import with `{% import '_includes/forms.twig' as forms %}`.

Every `*Field` macro wraps its input in a `<div class="field">` with label, instructions, tip, warning, and error display. The non-`Field` variants (e.g., `forms.text` vs `forms.textField`) render just the input — use these when building custom layouts or embedding inputs in other containers.

### Common parameters (all field macros)

| Param | Type | Purpose |
|-------|------|---------|
| `label` | `string` | Field label (translate with `\|t('my-plugin')`) |
| `instructions` | `string` | Help text below the label |
| `tip` | `string` | Green info tip below the input |
| `warning` | `string` | Orange warning below the input |
| `id` | `string` | Input element ID |
| `name` | `string` | Input name (for POST data) |
| `value` | `mixed` | Current value |
| `errors` | `array` | Validation errors from `item.getErrors('field')` |
| `required` | `bool` | Shows required indicator |
| `first` | `bool` | Auto-focus this field on page load |
| `disabled` | `bool` | Disable the input |
| `fieldClass` | `string` | Extra CSS class on the outer `<div class="field">` |

### Input macros

| Macro | Purpose | Key extra params |
|-------|---------|-----------------|
| `forms.textField` | Single-line text | `placeholder`, `size`, `maxlength`, `type` (e.g. `'email'`, `'url'`, `'number'`) |
| `forms.textareaField` | Multi-line text | `rows`, `placeholder`, `maxlength` |
| `forms.passwordField` | Password input | `placeholder` |
| `forms.selectField` | Dropdown | `options` (array of `{label, value}` or flat `{value: label}`) |
| `forms.multiSelectField` | Multi-select list | `options`, `values` (array of selected values) |
| `forms.lightswitchField` | Toggle switch | `on` (bool), `toggle` (CSS selector to show/hide) |
| `forms.checkboxField` | Single checkbox | `checked` (bool), `toggle` (CSS selector) |
| `forms.checkboxGroupField` | Multiple checkboxes | `options`, `values` (array of checked values) |
| `forms.radioGroupField` | Radio button group | `options`, `value` |
| `forms.buttonGroupField` | Button-style option selector (exclusive) | `options`, `value` — see [buttonGroupField](#buttongroupfield) |
| `forms.colorField` | Color picker | `value` (hex string) |
| `forms.dateTimeField` | Date and time picker | `value` (DateTime object or string) |
| `forms.timeField` | Time-only picker | `value` (time string) |
| `forms.autosuggestField` | Text with autocomplete | `suggestEnvVars`, `suggestAliases`, `suggestions` |
| `forms.editableTableField` | Editable table with add/delete/reorder | `cols`, `rows`, `allowAdd`, `allowDelete`, `allowReorder` — see [Editable Table](#editable-table) |
| `forms.elementSelectField` | Element relation selector (entries, assets, users) | `elementType`, `sources`, `criteria`, `limit`, `elements` (pre-selected), `modalStorageKey` |
| `forms.fieldLayoutDesignerField` | Field layout designer UI | `fieldLayout` (FieldLayout object) |
| `forms.hidden` | Hidden input (no field wrapper) | `name`, `value` |
| `forms.field` | Generic wrapper — you provide the inner HTML | `input` (raw HTML string) |

### autosuggestField

```twig
{{ forms.autosuggestField({
    label: 'API Endpoint'|t('my-plugin'),
    id: 'apiUrl',
    name: 'apiUrl',
    value: settings.apiUrl,
    suggestEnvVars: true,
    suggestAliases: true,
    placeholder: '$MY_API_URL',
}) }}
```

Typing `$` shows environment variables, `@` shows Yii aliases (`@web`, `@webroot`, custom aliases). Standard for any setting that should support env var overrides.

### elementSelectField

```twig
{{ forms.elementSelectField({
    label: 'Related Entries'|t('my-plugin'),
    id: 'relatedEntries',
    name: 'relatedEntries',
    elementType: 'craft\\elements\\Entry',
    sources: ['section:blog', 'section:news'],
    criteria: { status: null },
    limit: 5,
    elements: existingRelatedEntries,
    modalStorageKey: 'my-plugin.relatedEntries',
}) }}
```

Server-side, the POST value is an array of element IDs: `$ids = $request->getBodyParam('relatedEntries');`. Use `modalStorageKey` to remember the user's last-selected source in the modal.

### lightswitchField toggle

The `toggle` param shows/hides another element based on the switch state:

```twig
{{ forms.lightswitchField({
    label: 'Enable Feature'|t('my-plugin'),
    id: 'enableFeature',
    name: 'enableFeature',
    on: settings.enableFeature,
    toggle: '#feature-settings',
}) }}

<div id="feature-settings"{% if not settings.enableFeature %} class="hidden"{% endif %}>
    {# Additional fields shown only when the switch is on #}
    {{ forms.textField({ ... }) }}
</div>
```

### buttonGroupField

Exclusive button selector — visually similar to a segmented control. One option active at a time. Renders a `Craft.Listbox` with `aria-pressed` on each button. Use for settings with 2-5 discrete options where radio buttons feel too heavy.

```twig
{{ forms.buttonGroupField({
    label: 'Display Mode'|t('my-plugin'),
    id: 'displayMode',
    name: 'displayMode',
    value: settings.displayMode,
    options: {
        list: 'List'|t('my-plugin'),
        grid: 'Grid'|t('my-plugin'),
        map: 'Map'|t('my-plugin'),
    },
}) }}
```

Options can be a flat hash (`{ value: label }`) or an array of objects with `label`, `value`, and optional `class`:

```twig
{{ forms.buttonGroupField({
    label: 'Priority'|t('my-plugin'),
    id: 'priority',
    name: 'priority',
    value: settings.priority,
    options: [
        { label: 'Low', value: 'low' },
        { label: 'Normal', value: 'normal' },
        { label: 'High', value: 'high', class: 'error' },
    ],
}) }}
```

Server-side, the POST value is the selected option's `value` string. The raw variant (`forms.buttonGroup`) renders without the field wrapper — use it inside custom layouts or inline with other inputs.

`buttonGroupField` is for simple exclusive selects (display mode, priority level). It is **not** the right tool for tri-state inheritance controls (off/inherit/on) — its hidden input doesn't distinguish empty (inherit) from explicit values, and the uniform button styling doesn't convey state semantics. For inheritance UI, use the webhook table pattern below.

## CP UI Patterns

Battle-tested patterns from Craft core and first-party plugins. Check this section before building custom CP UI — most non-trivial patterns already exist.

### Tri-State Inheritance Controls

The `craftcms/webhooks` plugin (3.x branch, `_manage/edit.html`) is the reference implementation for "off / inherit / on" controls in table rows. Key details:

- Buttons use `<div class="btn">` not `<button class="btn">` (different default styles in Craft CP)
- `<div class="btngroup" tabindex="0">` wraps the three buttons
- Icons via `data-icon="remove"` (X mark) and `data-icon="checkmark"` (check) — uses Craft's built-in icon font
- Middle "inherit" button uses `<div class="status inactive">` for a hollow grey circle
- Hidden input stores the actual value; clicking a button updates it via JS
- Custom CSS is minimal (~15 lines) — colors, border resets, icon margin

```html
<div class="btngroup" tabindex="0">
    <div class="btn off-btn{% if value == false %} active{% endif %}"
         data-icon="remove" title="Off"></div>
    <div class="btn inherit-btn{% if value is null %} active{% endif %}"
         title="Inherit"><div class="status inactive"></div></div>
    <div class="btn on-btn{% if value == true %} active{% endif %}"
         data-icon="checkmark" title="On"></div>
</div>
<input type="hidden" name="settings[{{ handle }}]" value="{{ value }}">
```

Don't reinvent with `buttonGroupField` + custom captions. The webhook table pattern wins on compactness and clarity.

### Status Indicator Classes

Bare `<div class="status"></div>` renders **invisibly** in Craft 5 — no border-width/style on the base rule. Always add a modifier:

| Class | Appearance | Use for |
|-------|-----------|---------|
| `.status.green` / `.status.live` / `.status.active` | Green filled circle | Enabled, live, active |
| `.status.red` / `.status.off` | Red filled circle | Disabled, off, error |
| `.status.gray` / `.status.grey` | Grey filled circle | Neutral, pending |
| `.status.inactive` / `.status.disabled` | Hollow outlined circle (`box-shadow inset`) | Inherit, unset, neutral indicator |
| `.status.orange` / `.status.pending` | Orange filled circle | Pending, warning |

For "inherit/neutral" indicators, use `.status.inactive` (hollow). When placing an inactive status inside a dark `.active` button background, override the outline color for WCAG contrast: `--outline-color: var(--white)` (the default `var(--gray-500)` fails 3:1 contrast against dark backgrounds).

### Field Warning Parameter for Override Indicators

The `warning:` parameter on any form field macro is the canonical way to show "overridden by..." messages. Blitz uses this pattern extensively (`putyourlightson/blitz`):

```twig
{# Define a reusable macro #}
{% macro overrideWarning(globalValue) -%}
    {{ 'This overrides the global value of `{value}`.'|t('my-plugin', { value: globalValue })|markdown(inlineOnly=true) }}
{%- endmacro %}

{# Use on any field — renders inside the .field wrapper, no spacing hacks needed #}
{% from 'my-plugin/_macros' import overrideWarning %}

{{ forms.textField({
    label: 'Min Length'|t('my-plugin'),
    id: 'minLength',
    name: 'minLength',
    value: policy.minLength,
    warning: policy.minLength is not null ? overrideWarning(globalSettings.minLength),
}) }}
```

Server-rendered, visible after save and reload. Don't build custom `<p class="warning">` markup or JS-driven dynamic warnings — Craft's pattern is save-and-see. The `tip:` parameter works the same way for informational hints (green instead of orange).

For selects where the global value isn't visible via a placeholder, build an `inheritsGlobal()` macro that shows informational text revealing the current global setting when "Inherit global" is selected.

### The `[hidden]` Attribute Gotcha

Craft's `.warning.has-icon { display: flex }` (and similar utility classes) overrides the browser default `*[hidden] { display: none }`. Setting `element.hidden = true` in JavaScript does nothing visible — the element stays displayed because the CSS specificity wins.

Avoid this by using server-rendered `warning:` / `tip:` parameters (see above) instead of dynamic show/hide. If dynamic toggling is unavoidable, force the override with a namespaced rule:

```css
.my-plugin-element[hidden] { display: none !important; }
```

### Craft CSS Custom Properties

Don't hardcode hex colors. Craft provides semantic CSS variables that adapt to light/dark mode and are pre-tested for WCAG accessibility:

| Variable | Purpose | Notes |
|----------|---------|-------|
| `var(--ui-control-color)` | Default control/text color | |
| `var(--ui-control-active-color)` | Active/selected state | |
| `var(--bg-enabled)` | Live/on/active green | Passes WCAG AA against white |
| `var(--bg-disabled)` | Off/disabled red | Passes WCAG AA against white |
| `var(--white)` | High-contrast text on filled backgrounds | |
| `var(--gray-050)` through `var(--gray-900)` | Grey scale | |
| `var(--red-050)` through `var(--red-600)` | Red scale | |
| `var(--blue-050)` through `var(--blue-600)` | Blue scale | |
| `var(--yellow-050)` through `var(--yellow-600)` | Yellow/warning scale | |

White text on hardcoded `#27ae60` is 2.6:1 — fails AA (needs 4.5:1). Use `var(--bg-enabled)` instead.

### Platform PHP Version Mismatch

If `vendor/` was installed with host PHP (e.g., 8.4) but DDEV runs a different version (e.g., 8.3), `composer check-cs` and `composer phpstan` fail with `platform_check.php` errors. Always install dependencies inside DDEV:

```bash
ddev composer install
```

This ensures `vendor/` matches the container's PHP version. Never run `composer install` on the host for a DDEV-managed project.

## Condition Builders

Craft's UI for user-configurable filtering. Appears in element indexes (custom sources), field layout conditions, and entry type assignment rules.

### Key Classes

- `craft\base\conditions\BaseCondition` -- condition container holding rules
- `BaseMultiSelectConditionRule`, `BaseTextConditionRule`, `BaseDateRangeConditionRule` -- common rule bases
- `ElementConditionRuleInterface` -- implement for rules that filter element queries

### Custom Condition Rule

```php
class ItemTypeConditionRule extends BaseMultiSelectConditionRule implements ElementConditionRuleInterface
{
    public function getLabel(): string
    {
        return Craft::t('my-plugin', 'Item Type');
    }

    public function getExclusiveQueryParams(): array { return ['typeId']; }

    protected function options(): array
    {
        return array_map(fn($t) => ['value' => $t->id, 'label' => $t->name],
            MyPlugin::getInstance()->getItemTypes()->getAllItemTypes());
    }

    public function modifyQuery(ElementQueryInterface $query): void
    {
        $query->typeId($this->paramValue());
    }

    public function matchElement(ElementInterface $element): bool
    {
        return $this->matchValue($element->typeId);
    }
}
```

### Registration

```php
Event::on(EntryCondition::class, EntryCondition::EVENT_REGISTER_CONDITION_RULE_TYPES,
    function(RegisterConditionRuleTypesEvent $event) {
        $event->conditionRuleTypes[] = ItemTypeConditionRule::class;
    }
);
```

## Asset Bundles

### CP Asset Bundle

```php
class MyCpAsset extends AssetBundle
{
    public function init(): void
    {
        $this->sourcePath = '@myplugin/web/assets/dist';
        $this->depends = [CpAsset::class];
        $this->js = ['my-plugin.js'];
        $this->css = ['my-plugin.css'];
        parent::init();
    }
}
```

### Injecting JS Configuration

```php
public function registerAssetFiles($view): void
{
    parent::registerAssetFiles($view);
    $view->registerJsVar('MyPluginConfig', ['editableTypes' => $this->_getEditableTypes()]);
}
```

### Registration

```php
Craft::$app->getView()->registerAssetBundle(MyCpAsset::class); // controller
{% do view.registerAssetBundle('myplugin\\assetbundles\\MyCpAsset') %} {# template #}
```

For modern build tooling (HMR, TypeScript, Vue), use `nystudio107/craft-plugin-vite`.

## Permissions

For the complete permissions reference (all built-in handles, user groups, Twig/PHP checking, authorization events, strategies), see `permissions.md`. This section covers the CP-specific patterns.

### Registration

```php
Event::on(UserPermissions::class, UserPermissions::EVENT_REGISTER_PERMISSIONS,
    function(RegisterUserPermissionsEvent $event) {
        $event->permissions[] = [
            'heading' => Craft::t('my-plugin', 'My Plugin'),
            'permissions' => $this->_buildPermissions(),
        ];
    }
);
```

### Dynamic Per-Entity Permissions

Scope permissions by entity UID for multi-tenant isolation:

```php
private function _buildPermissions(): array
{
    $permissions = ['my-plugin:settings' => ['label' => Craft::t('my-plugin', 'Manage settings')]];
    foreach (MyPlugin::$plugin->getItems()->getAllItems() as $item) {
        $permissions["my-plugin:manage:{$item->uid}"] = [
            'label' => Craft::t('my-plugin', 'Manage {name}', ['name' => $item->name]),
            'nested' => ["my-plugin:view:{$item->uid}" => ['label' => Craft::t('my-plugin', 'View entries')]],
        ];
    }
    return $permissions;
}
```

Element-level checks (`canView()`, `canSave()`, `canDelete()`) are in `elements.md` under Authorization. Always implement alongside controller-level `requirePermission()` checks. Use `App::env('MY_PLUGIN_API_KEY')` for sensitive data.

## CP Markup Patterns

### Sidebar badges

Use `<span class="badge">` for badge labels in navigation sidebars and settings sidebars. Not `<span class="status">` — that's for element status indicators.

```twig
<span class="badge">{{ count }}</span>
```

### Notice and warning blocks

Semantic notice/warning markup for CP templates. No inline styles — use Craft's built-in classes:

```twig
{# Warning #}
<p class="warning has-icon">
    <span class="icon" aria-hidden="true"></span>
    <span class="visually-hidden">{{ 'Warning:'|t('app') }}</span>
    <span>{{ 'This action cannot be undone.'|t('my-plugin') }}</span>
</p>

{# Tip / informational notice #}
<p class="notice has-icon">
    <span class="icon" aria-hidden="true"></span>
    <span>{{ 'Configure the API key in Settings.'|t('my-plugin') }}</span>
</p>
```

Form field macros also accept `tip` and `warning` parameters:

```twig
{{ forms.textField({
    label: 'API Key'|t('my-plugin'),
    name: 'apiKey',
    value: settings.apiKey,
    warning: 'Changing this will invalidate existing tokens.'|t('my-plugin'),
    tip: 'Use an environment variable ($MY_API_KEY) for production.'|t('my-plugin'),
}) }}
```

## Read-Only Mode (allowAdminChanges)

When `allowAdminChanges` is `false` (production), plugin settings pages should be viewable but not editable. This requires coordination between the controller and the template. For the controller-side pattern, see `controllers.md` (the `requireAdmin(false)` pattern).

### Controller setup

```php
private bool $readOnly;

public function beforeAction($action): bool
{
    if (!parent::beforeAction($action)) {
        return false;
    }

    // View actions: admin without allowAdminChanges check
    if (in_array($action->id, ['index', 'edit'])) {
        $this->requireAdmin(false);
    } else {
        // Save/delete actions: require allowAdminChanges
        $this->requireAdmin();
    }

    $this->readOnly = !Craft::$app->getConfig()->getGeneral()->allowAdminChanges;

    return true;
}

public function actionEdit(?int $itemId = null): Response
{
    // Block creation in read-only mode
    if ($itemId === null && $this->readOnly) {
        throw new ForbiddenHttpException('New items cannot be created when allowAdminChanges is disabled.');
    }

    $variables['readOnly'] = $this->readOnly;

    return $this->renderTemplate('my-plugin/_edit', $variables);
}
```

### Template patterns

Pass `readOnly` to the template and use it to disable inputs and hide save buttons:

```twig
{% set readOnly = readOnly ?? false %}

{% set fullPageForm = not readOnly %}

{% block content %}
    {# Text field — disabled in read-only mode #}
    {{ forms.textField({
        label: 'Name'|t('my-plugin'),
        name: 'name',
        value: item.name,
        errors: item.getErrors('name'),
        disabled: readOnly,
        readonly: readOnly,
    }) }}

    {# Lightswitch — disabled #}
    {{ forms.lightswitchField({
        label: 'Enabled'|t('my-plugin'),
        name: 'enabled',
        on: item.enabled,
        disabled: readOnly,
    }) }}

    {# Editable table — static in read-only mode #}
    {% if readOnly %}
        {# Render a plain HTML table instead of the editable version #}
        <table class="data fullwidth">
            <thead>
                <tr>
                    <th>{{ 'Site'|t('my-plugin') }}</th>
                    <th>{{ 'URI Format'|t('my-plugin') }}</th>
                </tr>
            </thead>
            <tbody>
                {% for row in item.siteSettings %}
                    <tr>
                        <td>{{ row.site.name }}</td>
                        <td><code>{{ row.uriFormat }}</code></td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        {{ forms.editableTableField({
            label: 'Site Settings'|t('my-plugin'),
            name: 'siteSettings',
            cols: siteSettingsCols,
            rows: siteSettingsRows,
        }) }}
    {% endif %}

    {# Element select — disabled #}
    {{ forms.elementSelectField({
        label: 'Related Entries'|t('my-plugin'),
        name: 'relatedEntries',
        elements: relatedEntries,
        elementType: 'craft\\elements\\Entry',
        disabled: readOnly,
    }) }}
{% endblock %}
```

### Key template techniques

| Technique | Purpose |
|-----------|---------|
| `{% set fullPageForm = not readOnly %}` | Hides the save button and form wrapper in read-only mode |
| `disabled: readOnly` on form fields | Grays out inputs and prevents interaction |
| `readonly: readOnly` on text inputs | Prevents editing but allows text selection |
| Static HTML table fallback | Replaces editable tables with a plain display |
| `{% if not readOnly %}` around action buttons | Hides delete, reorder, and add buttons |

### Read-only notice

Show a notice at the top of the page so admins understand why they can't edit:

```twig
{% if readOnly %}
    {% set notice %}
        {{ 'Settings are read-only because allowAdminChanges is disabled in this environment.'|t('my-plugin') }}
    {% endset %}
    <div class="readable">
        <blockquote class="note">{{ notice }}</blockquote>
    </div>
{% endif %}
```
