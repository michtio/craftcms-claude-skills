# CP UI Patterns — Visual Patterns, Conditions, Assets

Battle-tested CP patterns from Craft core and first-party plugins, plus condition builders and asset bundles. For CP templates, form macros, settings pages, and navigation, see `cp.md`. For dashboard widgets, utilities, slideouts, and ajax, see `cp-components.md`.

## Contents

- CP UI Patterns — tri-state inheritance, status indicators, field warnings, CSS variables, `[hidden]` gotcha, platform PHP mismatch
- Condition Builders — BaseCondition, custom condition rules, registration
- Asset Bundles — CP asset bundle, JS configuration injection, registration
- CP Markup Patterns — sidebar badges, notice/warning blocks, tip/warning on form fields

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
