# CP Components — Widgets, Utilities, Slideouts, Ajax

Standalone CP component types: dashboard widgets, utility pages, slideout editors, ajax endpoints, and alerts. For CP templates, form macros, settings pages, and navigation, see `cp.md`.

## Contents

- Utility Pages — Utility class, template, registration
- Dashboard Widgets — Widget class, settings/body templates, registration
- Slideout Editors — automatic behavior, customization, programmatic triggering
- Ajax Endpoints for CP — controller actions, Craft.sendActionRequest()
- VueAdminTable — paginated/searchable CP lists via a permission-gated JSON data action
- Editable Table Field — inline-editable row data via forms.editableTableField
- Spinner — loading indicator markup and variants
- Modals — CP modal markup, shade classes, and the missing Craft.confirm()
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

`icon()` returns a built-in system icon name (`'wand'`, `'magnifying-glass'`) or an SVG **file path**. Derive paths from the file's own location — `dirname(__DIR__) . '/icon.svg'` — never from a Yii alias you assume exists. Failures are silent: `Cp::iconSvg()` catches the lookup exception internally, logs a single `Craft::warning`, and returns an empty string; `UtilitiesController::_getUtilityIconSvg()` then falls back to the default icon on that empty string (its own `catch` never fires for this path — it's belt-and-suspenders), so a wrong alias (e.g. a legacy plugin namespace whose alias differs from the assumed one) ships an invisible bug.

Craft auto-gates every utility behind a `utility:<id>` permission — see `permissions.md` (Utility Permissions) for how plugin permission checks stack on top of that native gate.

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

> For Garnish library primitives (`Garnish.Modal`/`HUD`/`DragSort`, `UiLayerManager`, focus/ARIA helpers, the `Garnish.Base.extend` class system), see the `craft-garnish` skill. This file covers Craft's higher-level `Craft.*` CP APIs built on top.

### How Slideouts Work

In Craft 5, element chips and cards automatically trigger slideout editors when clicked — no custom JS needed. Slideouts load the element's edit form in a side panel without leaving the current page.

### Customizing Slideout Content

Override these methods on your element class:

- `getSidebarHtml()` — sidebar content (metadata fields, status indicators)
- `getMetadataHtml()` — metadata table at the bottom of the sidebar
- `cpEditUrl()` — full edit page URL (slideout links to it)

Use `Craft::$app->getRequest()->getAcceptsJson()` to detect slideout context if you need to render differently.

When composing slideout HTML in PHP, note that not every Twig form macro has a `Cp` helper equivalent. `forms.languageMenuField` is Twig-only (`_includes/forms.twig:489`; `Cp.php` has no language-menu helper) — the PHP-side fallback is `Cp::selectFieldHtml()` with a normalized language option list.

### Triggering Programmatically

```js
// Existing element
Craft.createElementEditor('myplugin\\elements\\MyElement', { elementId: 123, siteId: 1 });

// New element
Craft.createElementEditor('myplugin\\elements\\MyElement', { attributes: { typeId: 5 } });
```

Slideouts appear in: relation fields (clicking chips/cards), element indexes ("Edit" action), inline creation buttons, and any custom UI rendering `_elements/chip.twig`.

### Reloading a Slideout (5.10+)

`Craft.CpScreenSlideout` instances expose a `reload()` method that re-fetches the screen's HTML and replaces the slideout content in place. Craft itself uses this to auto-refresh slideouts when the same element is edited in another browser tab. You can also call it manually from custom JS after a background operation completes:

```js
const slideout = Craft.createElementEditor('myplugin\\elements\\MyElement', { elementId: 123 });

// Later, after some async work that mutated the element:
slideout.reload();
```

The reload preserves the slideout's open state and scroll position; only the form contents update.

### Queue Completion Event (5.10+)

`Craft.cp` fires a `queueCompleted` event when the last queue job in the running batch finishes. Useful for CP screens that want to refresh themselves once a long-running queue (resave, propagation, batch import) is done:

```js
Craft.cp.on('queueCompleted', () => {
    Craft.cp.runPendingActions();
    // or trigger a custom refresh, re-fetch a panel, etc.
});
```

This is a global event on the CP singleton — listen once per page, not per element. The Craft progress HUD and queue manager already use it internally; only register handlers when you need a custom side-effect after queue work completes.

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

## VueAdminTable (paginated CP lists)

Any CP list that grows with usage — logs, sign-in history, temporary grants, submissions — must be paginated and searchable, not a plain Twig `<table>` that renders every row. Two native options:

- **Element index** when the rows are elements (see `element-index.md`).
- **`Craft.VueAdminTable`** when the rows are plain records/data. It fetches pages from a JSON action, so the DB does the paging.

Wire it with a permission-gated JSON data action plus a small init in the CP template:

```php
// Controller — permission-gated JSON page source
public function actionTableData(): Response
{
    $this->requirePermission(MyController::PERMISSION_VIEW_LOG);
    $page = (int)$this->request->getParam('page', 1);
    $limit = (int)$this->request->getParam('per_page', 100);
    $search = $this->request->getParam('search');

    $query = LogRecord::find()->orderBy(['dateCreated' => SORT_DESC]);
    if ($search) {
        $query->andWhere(['like', 'message', $search]);
    }
    $total = (int)$query->count();
    $rows = $query->offset(($page - 1) * $limit)->limit($limit)->all();

    return $this->asJson([
        'data' => array_map(fn($r) => [
            'id' => $r->id,
            'title' => $r->message,
            'when' => $r->dateCreated,
        ], $rows),
        'pagination' => ['total' => $total],
    ]);
}
```

```twig
{% js %}
  new Craft.VueAdminTable({
    columns: [
      { name: 'title', title: '{{ 'Message'|t('my-plugin') }}' },
      { name: 'when', title: '{{ 'When'|t('my-plugin') }}' },
    ],
    container: '#log-table',
    tableDataEndpoint: '{{ actionUrl('my-plugin/logs/table-data') }}',
    search: true,
    pagination: true,
  });
{% endjs %}
<div id="log-table"></div>
```

A plain Twig `<table>` is acceptable only for a provably small, fixed list (e.g. a handful of statuses). See `cp-ui-patterns.md` (CP Screen Composition) for when to reach for this.

### The table is the sole pane content

`Craft.VueAdminTable` is designed to be the **only** child of its pane — the component pulls itself to the pane edges with negative margins (the sticky footer especially), so sibling markup above or below the table in the same pane gets clipped or overlapped. Core index screens show the correct shape (`settings/entry-types/index.twig`, `settings/sections/_index.twig`):

- Intro / read-only copy goes in the layout's `contentNotice` region (`{% set contentNotice = ... %}`), not a paragraph above the table.
- The primary "New X" button goes in the layout's `{% block actionButton %}`, not beside the table.
- **One table per pane.** Grouped tables get one pane each behind anchor tabs — never stack two tables in one pane (the second table's chrome clips the heading between them).
- The one core-blessed exception is a secondary `.buttons` block *below* the table (`settings/assets/transforms/_index.twig:22-25`).

The "X of Y items" footer only renders for endpoint-driven tables: in the compiled component (`web/assets/admintable/dist/js/app.js`), `showFooter` is `(checkboxes && itemActions.length) || tableDataEndpoint` — inline `tableData` alone never shows it. If you want the count/pagination footer, or the list is unbounded, feed the table from a permission-gated JSON `tableDataEndpoint` as above.

## Editable Table Field

`forms.editableTableField` (macro `forms.twig:376`, wrapping the base `editableTable` at `forms.twig:136`) renders a grid of inline-editable rows — the same widget behind the Table field type. Reach for it when the author edits a small, structured set of rows in place (key/value pairs, ordered options, column definitions). It differs from VueAdminTable: editableTable is client-side and edits row *data*; VueAdminTable is server-driven and *displays* large paginated index tables (see the VueAdminTable section above — don't confuse the two).

Columns are declared via `cols` (each `{heading, type}`); `rows` seeds initial data keyed by column ID; `addRowLabel` sets the "add" button text but only surfaces when `allowAdd: true`:

```twig
{% import '_includes/forms.twig' as forms %}
{{ forms.editableTableField({
    label: 'Redirects'|t('my-plugin'),
    id: 'redirects',
    name: 'redirects',
    cols: {
        from: { heading: 'From'|t('my-plugin'), type: 'singleline' },
        to: { heading: 'To'|t('my-plugin'), type: 'url' },
    },
    rows: redirects,
    allowAdd: true,
    allowDelete: true,
    allowReorder: true,
    addRowLabel: 'Add a redirect'|t('my-plugin'),
}) }}
```

Common `col.type` values include `singleline`, `multiline`, `number`, `url`, `email`, `date`, `time`, `color`, `checkbox`, `select`, `heading`, and `template`. Pass `static: true` to render a non-editable, read-only grid.

For a purely presentational, read-only table you don't need the editable widget at all — a static `<table class="data">` (as used in the widget body template above) is lighter. Use editableTable only when the author actually edits the rows.

## Spinner

The CP loading indicator is a bare element — no JS required to show it; toggle it in/out of the DOM (or its visibility) as needed:

```twig
<div class="spinner"></div>
```

Size variants: `.spinner.small` and `.spinner.big`. Add `.spinner-absolute` to center it over a positioned container (it uses absolute positioning with a centered transform), which is handy for overlaying a spinner on a panel while an async request runs. Verified in `_main.scss` (~lines 2414-2447).

## Modals

> Modal and HUD *behavior* — the focus trap, ARIA wiring, open/close lifecycle, layer management — lives in the `craft-garnish` skill (`Garnish.Modal`, `Garnish.HUD`). This section only documents the CP markup and class contract; it does not duplicate the JS.

### Container and size variants

The modal container is `.modal`. A standard modal defaults to roughly 66% of the viewport (with a min size) unless you opt into a variant (verified `_main.scss` ~6901+):

- `.fitted` — shrinks to its content (`width: auto; height: auto`).
- `.fullscreen` — fills the viewport.
- `.alert` — adds an alert icon to the modal body (`.alert .body`), for confirmation-style dialogs.

### Shade (overlay) class

The dark backdrop behind a modal is `.modal-shade`, not a bare `.shade`. This is Garnish's `shadeClass` setting — the default is defined in `Modal.js` (~438) and the element is created from it (`Modal.js` ~41). HUDs use their own `.hud-shade` (`HUD.js` ~733). If you style or query the overlay, target `.modal-shade` / `.hud-shade`.

### Modal body/parts

The only content part on a base modal is `.body` (`.modal .body`, `_main.scss` ~6857/6865). There are **no** `.modal .header` or `.modal .footer` classes on a base Garnish modal. Structured CP screens use `Craft.CpModal` (which extends `Garnish.Modal`, `CpModal.js:9`), and it creates its own parts: `.cpmodal-body` (`CpModal.js:47`) and `.cpmodal-footer` (`CpModal.js:55`). Use those class names only with a `Craft.CpModal`, not a plain `Garnish.Modal`.

### There is no `Craft.confirm()`

There is no `Craft.confirm()` method — grepping `cp/src/js` for it returns nothing. For an alert-style confirmation, choose one of:

- **`Garnish.Modal` + `.modal.alert`** — a custom modal with the alert icon and your own confirm/cancel buttons (behavior via the `craft-garnish` skill).
- **`Craft.CpModal`** — a structured CP modal with `.cpmodal-footer` action buttons.
- **Native `confirm()` via `data-confirm`** — the lightest option. `Craft.submitForm()` (and the button handler at `Craft.js` ~3254) reads a button's `data-confirm` attribute into `options.confirm` and shows the browser's native `confirm()` before submitting (`Craft.js` ~2760). No custom JS needed:

```twig
<button type="submit" class="btn submit" data-confirm="{{ 'Delete this item?'|t('my-plugin') }}">
    {{ 'Delete'|t('my-plugin') }}
</button>
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
