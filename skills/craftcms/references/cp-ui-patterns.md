# CP UI Patterns — Visual Patterns, Conditions, Assets

Battle-tested CP patterns from Craft core and first-party plugins, plus condition builders and asset bundles. For CP templates, form macros, settings pages, and navigation, see `cp.md`. For dashboard widgets, utilities, slideouts, and ajax, see `cp-components.md`.

## Contents

- CP UI Patterns — tri-state inheritance, status indicators (`on`/`off` + distinct red statuses), field warnings, semantic CSS tokens (color/status/spacing/radius/control/focus/fonts), `[hidden]` gotcha, platform PHP mismatch
- Condition Builders — BaseCondition, custom condition rules, rule input HTML, rendering in templates, registration
- Asset Bundles — CP asset bundle, JS configuration injection, registration
- CP Markup Patterns — sidebar badges, notice/warning blocks, tip/warning on form fields
- Element Edit Screen — sidebar panels (`.meta` vs `.meta read-only`), `metaFieldsHtml()` override, top-toolbar split button (`EVENT_DEFINE_SIDEBAR_HTML` / `EVENT_DEFINE_ADDITIONAL_BUTTONS`)
- CP Screen Composition — native UX defaults: never improvise CP UI (copy the core/vendor idiom), tabs + the namespace/id tab trap, lightswitches vs checkboxes, two-layer field guidance (`instructions` + `<span class="info">`), cross-setting callout markup, env-var numerics, VueAdminTable for unbounded lists, index-screen column scheme + disclosure-menu row actions, native stats, honest empty values, `.status-badge` is a draft indicator (not an empty-value badge)

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

Bare `<div class="status"></div>` renders **invisibly** in Craft 5 — the base `.status` rule *does* size the dot (`width`/`height` of `calc(12rem/16)`, `border-radius:100%`, `box-sizing:border-box`), but it sets no fill; the `background-color` only comes from a modifier class. Always add one:

| Class | Appearance | Use for |
|-------|-----------|---------|
| `.status.on` / `.status.live` / `.status.active` / `.status.enabled` | Green filled circle | Enabled, live, active |
| `.status.off` / `.status.suspended` / `.status.expired` / `.status.red` | Red filled circle | Disabled / suspended / expired |
| `.status.gray` / `.status.grey` | Grey filled circle | Neutral, pending |
| `.status.inactive` / `.status.disabled` | Hollow outlined circle (`box-shadow inset`) | Inherit, unset, neutral indicator |
| `.status.orange` / `.status.pending` | Orange filled circle | Pending, warning |

The synonym groups are defined in `Color::tryFromStatus()` (`src/enums/Color.php`): `on`/`live`/`active`/`enabled` all map to teal (the green fill), and `off`/`suspended`/`expired` all map to red. `on` and `off` are the first-class boolean pair — prefer them for lightswitch-style state. But `off`, `suspended`, and `expired` are **distinct statuses that merely share the red fill** — they are not synonyms for one another, so pass the status that actually applies (`suspended` for a suspended user, `expired` for an expired entry) rather than flattening everything to `off`.

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

Don't hardcode raw values. Craft exposes a layer of **semantic tokens** on top of its color/size ramps (all in `_tokens.scss`). The point is indirection: a semantic token like `--bg-enabled` re-points itself under theming and light/dark mode, so referencing the token name keeps your UI in step with Craft automatically — hardcoding the value it happens to resolve to today freezes you out of that. Prefer the semantic token (`--bg-*`, `--fg-*`, `--ui-*`, `--border-*`, `--radius-*`, `--focus-*`) over the raw ramp value, and prefer the ramp value over a literal hex.

**Naming convention.** Tokens follow `--<prefix>-<modifier>`: `--ui-` (control chrome), `--fg-`/`--bg-` (foreground/background), `--border-`, `--focus-`, `--radius-`. Recognizing the prefix tells you what layer a token belongs to.

**Color ramps** (raw scales — reach for a semantic token first):

| Variable | Purpose |
|----------|---------|
| `var(--white)` | High-contrast text on filled backgrounds |
| `var(--gray-050)` through `var(--gray-900)` | Grey scale |
| `var(--red-050)` through `var(--red-600)` | Red scale |
| `var(--blue-050)` through `var(--blue-600)` | Blue scale |
| `var(--yellow-050)` through `var(--yellow-600)` | Yellow scale |

**Semantic status / feedback tokens** — use these for state coloring rather than picking a ramp shade by eye; each maps to the ramp centrally:

| Variable | Maps to | Purpose |
|----------|---------|---------|
| `var(--bg-primary)` | `--red-600` | Primary action / brand background |
| `var(--bg-secondary)` | `--gray-500` | Secondary background |
| `var(--bg-enabled)` | teal | Live / on / active fill |
| `var(--bg-disabled)` | `--red-600` | Off / disabled fill |
| `var(--bg-pending)` | orange | Pending fill |
| `var(--bg-success)` / `var(--fg-success)` | teal | Success callout bg / text |
| `var(--bg-warning)` / `var(--fg-warning)` | amber | Warning callout bg / text |
| `var(--bg-error)` / `var(--fg-error)` | red | Error callout bg / text |
| `var(--bg-notice)` / `var(--fg-notice)` | sky | Notice callout bg / text |

**Text tokens:**

| Variable | Value | Purpose |
|----------|-------|---------|
| `var(--fg-subtle)` | `--gray-550` | Muted/secondary text (readouts, help) |
| `var(--lh)` / `var(--size-line-height)` | `1.42em` | Body line-height |

**UI control chrome** — the tokens that size and round Craft's inputs/buttons. Match these so custom controls line up with native ones:

| Variable | Value | Purpose |
|----------|-------|---------|
| `var(--ui-control-color)` | — | Default control/text color |
| `var(--ui-control-active-color)` | — | Active/selected state |
| `var(--ui-control-radius)` | `= --radius-lg` | Control corner radius |
| `var(--ui-control-height)` | `34px` (`calc(34rem/16)`) | Standard control height |
| `var(--ui-control-height-small)` | `30px` (`calc(30rem/16)`) | Compact control height |

**Radius scale:**

| Variable | Value |
|----------|-------|
| `var(--radius-sm)` | `3px` |
| `var(--radius-md)` | `4px` |
| `var(--radius-lg)` | `5px` (also `--ui-control-radius`) |

**Spacing scale.** These are relative — each is `calc(<n>rem/16)` (e.g. `--xl` is `calc(24rem/16)`), so they scale with the root font size. **Use the token, not a px equivalent**, for gaps/padding: `--2xs`, `--xs`, `--s`, `--m`, `--l`, `--xl`. `var(--padding)` aliases `--xl` (contextually re-pointed to a smaller step in tight layouts).

**Hairline / border tokens:** `var(--border-hairline)` and `var(--border-hairline-medium)` for the thin dividers Craft draws between meta rows, card sections, etc. Reference by name — they're theme-aware and adjust for dark mode; don't quote the color.

**Focus tokens:** `var(--focus-ring)` is the composed box-shadow Craft puts on focused controls (it aliases `--focus-ring-medium`); `var(--focus-outline-medium)` is the underlying outline color. Applying `box-shadow: var(--focus-ring)` on a custom control gives it the exact native focus treatment (and keeps it correct if Craft retunes the ring).

**Fonts — no web fonts to load.** Craft's UI type is a system-UI stack: the `sans-serif-font` mixin (`_mixins.scss`) resolves to `system-ui, BlinkMacSystemFont, -apple-system, 'Segoe UI', 'Roboto', … sans-serif`. So there is no text webfont to bundle or preload — only the separate `Craft` icon font (used by `data-icon`) is a real font file. For code, handles, and other monospace UI, use the `fixed-width-font` mixin (`'SFMono-Regular', Consolas, Menlo, monospace`) rather than hardcoding a family.

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

**Whose form is it?** The example above uses `'name' => 'fields[approved]'`, which is correct only because `approved` is a real custom field on that entry — the surrounding entry form posts it and Craft saves it as part of the element. That's one of two cases, and getting them mixed up is the single most common bug in injected panels.

| The panel's values are saved by… | Give inputs a `name`? |
|----------------------------------|----------------------|
| The **host** form (real custom fields on that element) | Yes — `fields[handle]`, and let Craft save it |
| **Your own** endpoint (plugin data, separate ajax call) | **No** — `id` only |

**Fields injected into another form's DOM must be id-only when your plugin owns the data.** The element edit screen is one big `<form>`; anything with a `name` inside it is serialized and posted to Craft's element save action. A `name` your plugin invented then travels into `ElementsController::actionSave()`, which either ignores it (your value is silently dropped on every entry save) or — worse, if the name collides with something Craft or another plugin reads — writes it somewhere you didn't intend. Either way the host form "swallows" the field.

So drop `name` entirely and address the inputs by `id`. `Cp::*FieldHtml()` accepts `id` without `name`:

```php
$event->html .= Html::tag('fieldset',
    Html::tag('legend', Craft::t('my-plugin', 'Share Options'), ['class' => 'h6']) .
    Html::tag('div',
        // id only — no `name`. The host entry form must not serialize these.
        Cp::textFieldHtml([
            'label' => Craft::t('my-plugin', 'Recipient email'),
            'id' => 'my-plugin-share-email',
            'value' => $existing->email ?? '',
        ]) .
        Cp::lightswitchFieldHtml([
            'label' => Craft::t('my-plugin', 'Require password'),
            'id' => 'my-plugin-share-requirePassword',
            'on' => (bool)($existing->requirePassword ?? false),
        ]) .
        Html::button(Craft::t('my-plugin', 'Create link'), [
            'type' => 'button',            // never 'submit' inside the host form
            'class' => 'btn',
            'id' => 'my-plugin-share-submit',
        ]),
        ['class' => 'meta'],
    ),
);
```

Three details that make it behave:

- **Build the markup with Craft's `Cp::*FieldHtml()` helpers** (or `forms.*` macros in a template), not hand-rolled `<div class="field">`. They emit the correct structure, handle status/errors/translation, and stay right across Craft versions — and they let you pass `id` without `name`.
- **`type="button"`, never `type="submit"`.** A submit button inside the host form saves the entry.
- **Guard the Enter key**, or typing in your text field and pressing Enter submits the *entry* form. That's the JS half — see the `craft-garnish` skill's `integration.md` (Panels injected into another form).

Namespace the ids with your plugin handle (`my-plugin-share-email`). Ids are global on the page, the edit screen already has many, and Craft reserves a set of its own — see `cp.md` (Reserved DOM IDs).

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

## CP Screen Composition — Native UX Defaults

A plugin's CP screens should look and behave like Craft's own — native Craft UX is the default, not a later polish pass. These are the conventions (and the traps) that make a screen read as part of Craft rather than "almost Craft." For the settings-page controller/template plumbing and the in-section pattern, see `cp.md` (Settings Pages).

**Never improvise CP UI.** Thin guidance is not a license to invent: when a pattern isn't documented here, read Craft core's templates (`vendor/craftcms/cms/src/templates/`) or an established vendor plugin (nystudio107, putyourlightson, verbb, doublesecretagency, craftpulse) and copy the idiom — and note which template you matched. Hand-rolled markup where a core idiom exists is a defect, not a style choice.

### Tabs by default — and the namespace/id tab trap

A settings or management screen with more than ~2 sections uses CP tabs (`{% set tabs %}` + pane divs), not one long scroll. Craft's tab JS toggles panes by reading each tab's `href="#pane-id"` and matching it as a selector against the pane's literal `id` (showing that pane, adding `class="hidden"` to the rest). Two consequences:

- **Give each pane a literal `id` matching its tab's `href`.** First pane visible; later panes start `class="hidden"`.
- **Do not wrap tabbed settings fields in `{% namespace 'settings' %}`.** The namespace tag rewrites `id` attributes as well as `name`s (both go through `View::namespaceInputs()`), so a pane `id="general"` becomes `id="settings-general"`, the tab's `href="#general"` matches nothing, and **every tab silently shows the first pane**. Instead, carry the post envelope explicitly on each field — `name: 'settings[tokenTtl]'` — and leave pane ids literal. (The bare-fragment `{% namespace 'settings' %}` reuse in `cp.md` is safe only for a *non-tabbed* shared fragment where no pane ids exist.)

### Lightswitches, not checkboxes, for booleans

Use `forms.lightswitchField` for a boolean or a toggle-set setting. A checkbox group (`forms.checkboxSelectField`) is only for a genuine multi-select of peers. Lightswitches are Craft's native affordance for on/off; checkboxes read as "pick several."

### Two-layer field guidance: `instructions` + `<span class="info">`, not `tip:`

Field help is two layers, with distinct mechanisms — don't reach for `tip:` for this:

- The one-line **`instructions`** param carries the short "what this is."
- The deeper "why and when" goes **inside** the instructions as `<span class="info">…</span>`, which Craft renders as the hover ⓘ info bubble next to the label (the same `.info` span Craft's own field macros emit). Example: `instructions: 'Token lifetime.'|t ~ '<span class="info">' ~ 'How long an issued token stays valid before re-auth is required.'|t ~ '</span>'`.
- `tip:` (blue lightbulb) and `warning:` (amber) are **standalone callout params** for genuine per-field callouts — they are *not* the info-bubble mechanism. Using `tip:` where an info bubble belongs produces the wrong affordance.

### Cross-setting warnings: core's conditional-callout markup

When one setting's value makes another moot ("X is on but Y is off, so the feature stays closed"), render the warning with Craft core's exact conditional-callout markup — copy it from `vendor/craftcms/cms/src/templates/settings/email/_index.twig`:

```twig
{% if someConditionThatMattersToTheUser %}
    <div class="readable">
        <blockquote class="note warning">
            <p>{{ 'Sessions are enabled but no driver is configured, so login stays disabled. {link}.'|t('my-plugin', {
                link: tag('a', { text: 'Configure a driver'|t('my-plugin'), href: url('my-plugin/settings') })
            })|raw }}</p>
        </blockquote>
    </div>
    <hr>
{% endif %}
```

The trailing `<hr>` **inside** the conditional is the spacing mechanism between the callout and the first field — that's why it belongs to the `{% if %}`. Never hand-roll bare colored text, and never juggle a `first:` flag on the following field to fake the gap (that spacing bug recurs every time the callout is hand-rolled). Always carry the actionable link.

### Operational numerics support env vars

Anything an operator might need to change in production without a deploy — TTLs, limits, rate windows — gets env-var support end to end: `forms.autosuggestField` with `suggestEnvVars: true` in the template, a model property typed `int|string` (it may hold `'$MY_TTL'` before resolution), a typed getter that resolves via `App::parseEnv()`, and validation that runs on the **resolved** value. See `cp.md` (Settings Template with Env Var Support) for the field markup.

### No unbounded static tables

Any CP list that grows with usage — logs, sign-ins, grants, submissions — ships as a paginated, searchable **VueAdminTable** backed by a permission-gated JSON data action, or as an **element index** when the rows are elements. A plain Twig `<table>` is only for a provably small, fixed list. See `cp-components.md` (VueAdminTable) for the wiring.

### Index-screen column scheme and row actions

Match core's settings indexes (`settings/plugins/index.twig`, `settings/sections/_index.twig`):

- **Name first, bold, linked** to the edit screen — the row's name is the way in, not a separate Edit button.
- **Technical / copyable values** (handles, external resource names, IDs) render as monospace copy chips — VueAdminTable's `__slot:handle` column does this natively (the compiled component renders a copy-text button with `code light` classes). Surface the name developers actually integrate against — the alias-aware, query-correct external name — not an internal label.
- **Boolean state** renders as status dots with a label (`<span class="status on"></span>` / `off` / `disabled` + `<span class="light">` — `settings/plugins/index.twig:233-245`), not bare words.
- **Meta columns** (dates, counts) stay plain.
- **Per-row actions** live in a disclosure menu (`Cp::disclosureMenu()` — `settings/plugins/index.twig:258`); row deletion uses VueAdminTable's native `deleteAction`. A farm of `btn small` buttons per row is not a Craft idiom.

### Native stats and honest empty values

- Posture / summary data (counts, health, "N of M configured") renders with Craft's native stat presentation, not paragraphs of prose.
- Unknown or empty cells in an admin table render as **muted words**, never a bare `-` — set an empty value's cell to something like `<span class="light">Location unknown</span>`. (Do **not** reach for `.status-badge` here: in Craft source that class is a draft-modification indicator, not an empty-value label — see below.)
- An admin table shows **facts**, not user alerts. A signal meant for the end user (e.g. a "new sign-in location" security notice) ships through the user-facing channel (email/notification) — it does not get an admin-table column.

### `.status-badge` is a draft-modification indicator, not an empty-value badge

Don't confuse `.status-badge` with the muted empty-value text above. In Craft source (`.status-badge` in `_main.scss`; emitted by `Cp::elementHtml()` and `Cp::fieldHtml()` in `src/helpers/Cp.php`) it is an **absolutely-positioned 2px stripe** pinned to the inline-start edge of an element card or field (`position:absolute; inset-inline-start:0; width:2px; height:100%`), always paired with a visually-hidden label. Its two modifiers signal draft state: `.status-badge.modified` (blue, `var(--blue-600)`) marks an element that has unsaved/edited draft changes, and `.status-badge.outdated` (orange, `var(--bg-pending)`) marks a derivative that has fallen behind its canonical. It is not a word-label control and never carries visible text — for an "unknown/empty" cell use muted text (`<span class="light">…</span>`), not this class.
