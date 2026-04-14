# Control Panel — Templates, Permissions, UI

Complete reference for CP extension points: templates, navigation, settings pages, utilities, widgets, slideouts, and AJAX patterns. For controller patterns (CRUD, webhooks, API, routing), see `references/controllers.md`.

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

## Contents

- [CP Templates](#cp-templates)
- [CP Navigation](#cp-navigation)
- [Settings Pages](#settings-pages)
- [Utility Pages](#utility-pages)
- [Dashboard Widgets](#dashboard-widgets)
- [Slideout Editors](#slideout-editors)
- [Ajax Endpoints for CP](#ajax-endpoints-for-cp)
- [CP Alerts and Notices](#cp-alerts-and-notices)
- [Form Macros Reference](#form-macros-reference)
- [Condition Builders](#condition-builders)
- [Asset Bundles](#asset-bundles)
- [Permissions](#permissions)

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

```twig
{{ forms.editableTableField({
    label: 'Site Mappings'|t('my-plugin'), id: 'sites', name: 'sites',
    cols: {
        siteId: { type: 'select', heading: 'Site'|t('my-plugin'), options: siteOptions },
        uriFormat: { type: 'singleline', heading: 'URI Format'|t('my-plugin'), placeholder: 'items/{slug}' },
    },
    rows: siteRows, allowAdd: true, allowDelete: true, allowReorder: true,
}) }}
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
    tableData: {{ items|json_encode|raw }},
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
    $item['badgeCount'] = 5;
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
Event::on(Utilities::class, Utilities::EVENT_REGISTER_UTILITY_TYPES,
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

Beyond the basics (`textField`, `lightswitchField`, `selectField`):

| Macro | Purpose |
|-------|---------|
| `forms.dateTimeField` | Date and time picker |
| `forms.colorField` | Color picker |
| `forms.autosuggestField` | Text with autocomplete (env vars, aliases) |
| `forms.textareaField` | Multi-line text |
| `forms.passwordField` | Password input |
| `forms.checkboxField` | Single checkbox |
| `forms.checkboxGroupField` | Multiple checkboxes |
| `forms.radioGroupField` | Radio button group |
| `forms.field` | Generic wrapper for custom HTML |

`autosuggestField` with `suggestEnvVars: true` -- typing `$` shows env vars. With `suggestAliases: true` -- typing `@` shows Yii aliases (`@web`, `@webroot`). See [Settings Pages](#settings-pages) for a full example.

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
    $data = Json::encode(['editableTypes' => $this->_getEditableTypes()]);
    $view->registerJs("window.Craft.MyPlugin = window.Craft.MyPlugin || {}; window.Craft.MyPlugin.config = {$data};", View::POS_HEAD);
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

Element-level checks (`canView()`, `canSave()`, `canDelete()`) are in `references/elements.md` under Authorization. Always implement alongside controller-level `requirePermission()` checks. Use `App::env('MY_PLUGIN_API_KEY')` for sensitive data.
