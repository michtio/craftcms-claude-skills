# Control Panel — Templates, Permissions, UI

## Documentation

- CP templates: https://craftcms.com/docs/5.x/extend/cp-templates.html
- CP sections: https://craftcms.com/docs/5.x/extend/cp-section.html
- CP edit pages: https://craftcms.com/docs/5.x/extend/cp-edit-pages.html
- Permissions: https://craftcms.com/docs/5.x/extend/user-permissions.html

For controller patterns (CRUD, webhooks, API, routing), see `references/controllers.md`.

## Common Pitfalls

- Not wrapping settings UI in `allowAdminChanges` checks — settings should be read-only in production.
- Hardcoding plugin name strings instead of using `Craft::t()` with the plugin handle translation category.
- Missing `actionInput()` and `redirectInput()` in full-page forms — form submission won't route correctly.
- Not passing `errors: entity.getErrors('field')` to form macros — validation errors won't display.

## CP Templates

### Form Macros

Import Craft's built-in form helpers:

```twig
{% import '_includes/forms.twig' as forms %}

{{ forms.textField({
    label: 'Name'|t('my-plugin'),
    id: 'name',
    name: 'name',
    value: item.name,
    errors: item.getErrors('name'),
    required: true,
    first: true,
}) }}

{{ forms.lightswitchField({
    label: 'Enable Sync'|t('my-plugin'),
    id: 'enableSync',
    name: 'enableSync',
    on: settings.enableSync,
}) }}

{{ forms.selectField({
    label: 'Batch Size'|t('my-plugin'),
    id: 'batchSize',
    name: 'batchSize',
    value: item.batchSize,
    options: batchSizeOptions,
}) }}
```

### Editable Table

```twig
{{ forms.editableTableField({
    label: 'Site Mappings'|t('my-plugin'),
    id: 'sites',
    name: 'sites',
    cols: {
        siteId: {
            type: 'select',
            heading: 'Site'|t('my-plugin'),
            options: siteOptions,
        },
        uriFormat: {
            type: 'singleline',
            heading: 'URI Format'|t('my-plugin'),
            placeholder: 'items/{slug}',
        },
    },
    rows: siteRows,
    allowAdd: true,
    allowDelete: true,
    allowReorder: true,
}) }}
```

### Admin Changes Check

Always wrap settings UI in `allowAdminChanges`:

```twig
{% if allowAdminChanges %}
    <div class="buttons">
        <button type="submit" class="btn submit">{{ 'Save'|t('app') }}</button>
    </div>
{% endif %}
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

For listing entities with sorting, filtering, and pagination:

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

## Asset Bundles

Asset bundles load CSS and JavaScript into the CP. Every plugin with custom CP interactions needs one.

### CP Asset Bundle

Extend `craft\web\AssetBundle`. Set `$sourcePath` to your compiled assets directory and `$depends` to include `CpAsset` so Craft's CP styles and scripts are available:

```php
use craft\web\AssetBundle;
use craft\web\assets\cp\CpAsset;

class MyCpAsset extends AssetBundle
{
    public function init(): void
    {
        $this->sourcePath = '@myplugin/web/assets/dist';

        $this->depends = [
            CpAsset::class,
        ];

        $this->js = [
            'my-plugin.js',
        ];

        $this->css = [
            'my-plugin.css',
        ];

        parent::init();
    }
}
```

### Injecting JS Configuration

Override `registerAssetFiles()` to pass PHP data to JavaScript — define a global `Craft.MyPlugin` object that your scripts can read:

```php
public function registerAssetFiles($view): void
{
    parent::registerAssetFiles($view);

    $data = Json::encode(['editableTypes' => $this->_getEditableTypes()]);

    $js = <<<JS
if (typeof window.Craft.MyPlugin === typeof undefined) {
    window.Craft.MyPlugin = {};
}
window.Craft.MyPlugin.config = {$data};
JS;
    $view->registerJs($js, View::POS_HEAD);
}
```

### Registration

Register from controllers or templates:

```php
// In a controller action
Craft::$app->getView()->registerAssetBundle(MyCpAsset::class);

// In a Twig template
{% do view.registerAssetBundle('myplugin\\assetbundles\\MyCpAsset') %}
```

### Vite Integration

For modern build tooling (HMR, TypeScript, Vue), use `nystudio107/craft-plugin-vite` instead of manually managing asset bundles. It handles dev server proxying and production builds.

## Permissions

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
    $permissions = [];
    $permissions['my-plugin:settings'] = [
        'label' => Craft::t('my-plugin', 'Manage settings'),
    ];

    foreach (MyPlugin::$plugin->getItems()->getAllItems() as $item) {
        $permissions["my-plugin:manage:{$item->uid}"] = [
            'label' => Craft::t('my-plugin', 'Manage {name}', ['name' => $item->name]),
            'nested' => [
                "my-plugin:view:{$item->uid}" => [
                    'label' => Craft::t('my-plugin', 'View entries'),
                ],
            ],
        ];
    }

    return $permissions;
}
```

### Element Authorization

Element-level permission checks (`canView()`, `canSave()`, `canDelete()`, etc.) are documented in `references/elements.md` under Authorization. Always implement these alongside controller-level permission checks — controller checks gate access to the action, element checks gate access to the specific entity.

### Environment-Specific Security

Sensitive data via environment variables:

```php
'apiKey' => App::env('MY_PLUGIN_API_KEY') ?: $item->apiKey,
```
