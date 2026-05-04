# CP Components — Widgets, Utilities, Slideouts, Ajax

Standalone CP component types: dashboard widgets, utility pages, slideout editors, ajax endpoints, and alerts. For CP templates, form macros, settings pages, and navigation, see `cp.md`.

## Contents

- Utility Pages — Utility class, template, registration
- Dashboard Widgets — Widget class, settings/body templates, registration
- Slideout Editors — automatic behavior, customization, programmatic triggering
- Ajax Endpoints for CP — controller actions, Craft.sendActionRequest()
- CP Alerts and Notices — system-wide alerts, flash messages

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

Does not extend a layout — Craft wraps it. Use `csrfInput()` since this is not a `fullPageForm`:

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

In Craft 5, element chips and cards automatically trigger slideout editors when clicked — no custom JS needed. Slideouts load the element's edit form in a side panel without leaving the current page.

### Customizing Slideout Content

Override these methods on your element class:

- `getSidebarHtml()` — sidebar content (metadata fields, status indicators)
- `getMetadataHtml()` — metadata table at the bottom of the sidebar
- `cpEditUrl()` — full edit page URL (slideout links to it)

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
