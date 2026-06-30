# CP UI Patterns — Visual Patterns, Conditions, Assets

Battle-tested CP patterns from Craft core and first-party plugins, plus condition builders and asset bundles. For CP templates, form macros, settings pages, and navigation, see `cp.md`. For dashboard widgets, utilities, slideouts, and ajax, see `cp-components.md`.

## Contents

- CP UI Patterns — tri-state inheritance, status indicators, field warnings, CSS variables, `[hidden]` gotcha, platform PHP mismatch
- Condition Builders — BaseCondition, custom condition rules, rule input HTML, rendering in templates, registration
- Asset Bundles — CP asset bundle, JS configuration injection, registration
- CP Markup Patterns — sidebar badges, notice/warning blocks, tip/warning on form fields
- Element Edit Screen — sidebar panels (`.meta` vs `.meta read-only`), `metaFieldsHtml()` override, top-toolbar split button (`EVENT_DEFINE_SIDEBAR_HTML` / `EVENT_DEFINE_ADDITIONAL_BUTTONS`)

## CP UI Patterns

Check this section before building custom CP UI — most non-trivial patterns already exist.

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

The `warning:` parameter on any form field macro is the canonical way to show "overridden by..." messages:

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

Server-rendered, visible after save and reload. Don't build custom `<p class="warning">` markup or JS-driven dynamic warnings — Craft's pattern is save-and-see. The `tip:` parameter works the same way for informational hints (see "Form field tip/warning parameters" under CP Markup Patterns).

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

- `craft\base\conditions\BaseCondition` — condition container holding rules
- `BaseMultiSelectConditionRule`, `BaseTextConditionRule`, `BaseDateRangeConditionRule` — common rule bases
- `ElementConditionRuleInterface` — implement for rules that filter element queries

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

#### A rule's own input HTML

A `BaseConditionRule` subclass renders its input by overriding `protected function inputHtml(): string` — **zero arguments**. This is distinct from a *field type's* `inputHtml(mixed $value, ?ElementInterface $element, bool $inline): string`. A condition rule stores its own value on the instance (e.g. `$this->value`), so the method takes no parameters; the common bases (`BaseMultiSelectConditionRule`, `BaseTextConditionRule`, etc.) already implement it for you, so you only override `inputHtml()` for a fully custom control.

### Registration

```php
Event::on(EntryCondition::class, EntryCondition::EVENT_REGISTER_CONDITION_RULE_TYPES,
    function(RegisterConditionRuleTypesEvent $event) {
        $event->conditionRuleTypes[] = ItemTypeConditionRule::class;
    }
);
```

### Rendering a condition builder in a CP template

Build the condition via the `conditions` service factory, then hand it to the template. `createCondition()` accepts a class name or a serialized config array (so you can rebuild a saved condition):

```php
$condition = Craft::$app->getConditions()->createCondition(MyCondition::class);
$condition->id = 'my-condition'; // namespaced into the builder markup

return $this->renderTemplate('my-plugin/_settings', [
    'condition' => $condition,
]);
```

In Twig, output the builder with `getBuilderHtml()` (on `BaseCondition`) — it returns the full `.condition-container` markup and registers the JS that initialises the UI elements:

```twig
{{ condition.getBuilderHtml()|raw }}
```

On submit, the posted config comes back under the condition's input name; rebuild it server-side with `createCondition($request->getBodyParam('condition'))` and persist the result of `condition.getConfig()`.

## Asset Bundles

> For Garnish library primitives (`Garnish.Modal`/`HUD`/`DragSort`, `UiLayerManager`, focus/ARIA helpers, the `Garnish.Base.extend` class system), see the `craft-garnish` skill. This file covers Craft's higher-level `Craft.*` CP APIs built on top.

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

### Form field tip/warning parameters

Form field macros also accept `tip` (green) and `warning` (orange) parameters, rendered inside the `.field` wrapper. Both are server-rendered — visible after save and reload:

```twig
{{ forms.textField({
    label: 'API Key'|t('my-plugin'),
    name: 'apiKey',
    value: settings.apiKey,
    warning: 'Changing this will invalidate existing tokens.'|t('my-plugin'),
    tip: 'Use an environment variable ($MY_API_KEY) for production.'|t('my-plugin'),
}) }}
```

## Element Edit Screen — Sidebar Panels & Toolbar Buttons

Render custom UI into an element's **edit screen sidebar** (`EVENT_DEFINE_SIDEBAR_HTML`) or its **top toolbar** (`EVENT_DEFINE_ADDITIONAL_BUTTONS`). Both fire `craft\events\DefineHtmlEvent`; `$event->html` is the assembled markup (append to it), and `$event->sender` is the element. See `elements.md` (Element Events Reference) for where these sit among the ~40 element events.

The one mistake that makes a sidebar panel "look wrong" is picking the wrong `.meta` treatment. There are two, and they are visually opposite.

### Two `.meta` treatments — pick the right one

`Element::getSidebarHtml(bool $static)` (`src/base/Element.php`) assembles the sidebar in order:

1. The element's own `metaFieldsHtml()`, wrapped by Craft in `<div class="meta">` (plus a visually-hidden `<h2>Metadata</h2>`).
2. `statusFieldHtml()` — the **Status** panel.
3. `notesFieldHtml()` — the draft **Notes** field (only when the element has revisions).

…then fires `EVENT_DEFINE_SIDEBAR_HTML` with that assembled string in `$event->html`.

**A. Titled field panel** (Status / Notes / a custom card) — interactive form rows inside a filled card:

```html
<fieldset>
  <legend class="h6">Status</legend>
  <div class="meta">
    <!-- one or more native .field rows -->
    <div class="field">
      <div class="heading"><label for="enabled">Enabled</label></div>
      <div class="input ltr"><!-- control --></div>
    </div>
  </div>
</fieldset>
```

In the edit-screen sidebar, a plain `.meta` (i.e. `:not(.read-only)`) renders as a **subtly filled, rounded card** — `.details .meta:not(.read-only){background-color:var(--gray-050)}` plus `border-radius:var(--radius-lg)` (it is `--gray-050`, *not* white). `.field .input` is the value area and carries an orientation class (`ltr`/`rtl`).

**B. Key→value readout** (the bottom ID / Status / Created block) — produced by `Cp::metadataHtml($element->getMetadata())`, which the controller appends below the form:

```html
<dl class="meta read-only">
  <div class="data">
    <dt class="heading">Created at</dt>
    <dd class="value">…</dd>
  </div>
</dl>
```

`.meta.read-only` is a `<dl>` (rows are `<div class="data">` with `<dt class="heading">` / `<dd class="value">`), rendered **naked and muted** — `background-color:transparent` and `color:var(--fg-subtle)`. It is a *readout*, not a card. Using it for an interactive panel looks broken; using `.field`/`.input` rows for a static readout misses the muted readout styling.

**Rule:**

| You want | Use |
|----------|-----|
| Titled, interactive panel | `<fieldset>` + `<legend class="h6">` + plain `<div class="meta">` + `.field`/`.input` rows |
| Static key→value readout | `Cp::metadataHtml([...])` → `.meta read-only` + `.data`/`.value` |

Prefer the `Cp::*FieldHtml()` helpers (`textFieldHtml`, `dateTimeFieldHtml`, `selectFieldHtml`, `lightswitchFieldHtml`, …) over hand-rolling `.field` markup — they emit the correct `.field` > `.heading`/`label` + `.input` structure, handle status/errors/translation, and stay correct across Craft versions.

### (a) Append a titled panel to another element's sidebar (from a plugin)

Craft only wraps the element's *own* `metaFieldsHtml()` in `.meta` — markup you append to `$event->html` is **not** wrapped. So emit your own `fieldset` + `legend.h6` + `.meta` wrapper, or it renders unstyled:

```php
use Craft;
use craft\base\Element;
use craft\elements\Entry;
use craft\events\DefineHtmlEvent;
use craft\helpers\Cp;
use craft\helpers\Html;
use yii\base\Event;

Event::on(
    Entry::class,
    Element::EVENT_DEFINE_SIDEBAR_HTML,
    function(DefineHtmlEvent $event) {
        /** @var Entry $entry */
        $entry = $event->sender;

        $event->html .= Html::tag('fieldset',
            Html::tag('legend', Craft::t('my-plugin', 'Review'), ['class' => 'h6']) .
            Html::tag('div',
                Cp::lightswitchFieldHtml([
                    'label' => Craft::t('my-plugin', 'Approved'),
                    'name' => 'fields[approved]',
                    'on' => (bool)$entry->getFieldValue('approved'),
                ]),
                ['class' => 'meta'],
            ),
        );
    },
);
```

For a static readout instead, append `Cp::metadataHtml(['Word count' => $count, ...])` (no wrapper needed — it carries its own `.meta read-only`).

### (b) `metaFieldsHtml()` override on your own element

When you define the element, override `protected function metaFieldsHtml(bool $static): string` and return the field rows concatenated. `getSidebarHtml()` wraps the whole return value in a single `.meta` card, so return field HTML directly — do **not** add your own `.meta`/`fieldset` per field. Append `parent::metaFieldsHtml($static)` last so the base element's meta fields (and the `EVENT_DEFINE_META_FIELDS_HTML` event) still fire:

```php
protected function metaFieldsHtml(bool $static): string
{
    return implode("\n", [
        Cp::dateTimeFieldHtml([
            'status' => $this->getAttributeStatus('dueDate'),
            'label' => Craft::t('my-plugin', 'Due Date'),
            'id' => 'dueDate',
            'name' => 'dueDate',
            'value' => $this->dueDate,
            'errors' => $this->getErrors('dueDate'),
            'disabled' => $static,
        ]),
        parent::metaFieldsHtml($static),
    ]);
}
```

### (c) Top-toolbar split button via `EVENT_DEFINE_ADDITIONAL_BUTTONS`

`Element::getAdditionalButtons()` fires `EVENT_DEFINE_ADDITIONAL_BUTTONS`; the controller (`_additionalButtons()` in `src/controllers/ElementsController.php`) appends the result to the toolbar **after** the native Preview / Create a draft / Apply draft buttons.

The native Save split button (`_layouts/cp.twig` + `_layouts/components/form-action-menu.twig`) is the markup to match: a `.btngroup` holding a primary `.btn`, a disclosure-trigger `.btn.menubtn`, and the menu:

```twig
{# my-plugin/_components/toolbar-button.twig #}
<div class="btngroup">
  <a class="btn" href="{{ exportUrl }}">{{ 'Export'|t('my-plugin') }}</a>
  <button
    type="button"
    class="btn menubtn"
    aria-label="{{ 'More export options'|t('my-plugin') }}"
    aria-controls="export-menu-{{ elementId }}"
    data-disclosure-trigger
  ></button>
  <div id="export-menu-{{ elementId }}" class="menu menu--disclosure" data-align="right">
    <ul>
      <li>
        <button type="button" class="menu-item" data-action="my-plugin/export/csv">
          <span class="menu-item-label inline-flex flex-col items-start gap-2xs">{{ 'Export as CSV'|t('my-plugin') }}</span>
        </button>
      </li>
      <li>
        <button type="button" class="menu-item" data-action="my-plugin/export/json">
          <span class="menu-item-label inline-flex flex-col items-start gap-2xs">{{ 'Export as JSON'|t('my-plugin') }}</span>
        </button>
      </li>
    </ul>
  </div>
</div>
```

Register it (use a unique menu `id` per element so multiple instances don't collide):

```php
use craft\web\View;

Event::on(
    Entry::class,
    Element::EVENT_DEFINE_ADDITIONAL_BUTTONS,
    function(DefineHtmlEvent $event) {
        $entry = $event->sender;
        $event->html .= Craft::$app->getView()->renderTemplate(
            'my-plugin/_components/toolbar-button',
            [
                'elementId' => $entry->id,
                'exportUrl' => "my-plugin/export?elementId=$entry->id",
            ],
            View::TEMPLATE_MODE_CP,
        );
    },
);
```

Markup details that matter:

- **Menu items must be `<li>` inside `<ul>`.** A bare `.menu-item` outside a list misses the menu's layout.
- **The `.menu-item-label` span is required.** `_includes/disclosuremenu.twig` wraps every item label in `<span class="menu-item-label inline-flex flex-col items-start gap-2xs">` — the item's padding/layout CSS targets that span. Bare text directly in `.menu-item` renders cramped.
- **`data-align="right"`** aligns the menu's end edge to the trigger so it opens toward the start edge — matches the native Save menu.
- **No JS needed.** `Craft.initUiElements` runs `$('[data-disclosure-trigger]').disclosureMenu()`, so Garnish wires up any element carrying `data-disclosure-trigger` automatically (the `.menubtn` class is initialized separately only when it lacks that attribute).

Or skip the hand-rolled menu: `Cp::disclosureMenu($items, ['withButton' => true, 'hiddenLabel' => '…'])` emits the correct `<ul><li>` items and registers the JS. Wrap a primary `Html::a('…', ['class' => 'btn'])` and that call together in `Html::tag('div', …, ['class' => 'btngroup'])` for the split-button shape.
