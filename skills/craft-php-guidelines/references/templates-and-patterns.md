# CP Templates, Validation, Translations, and File Headers

## CP Twig Templates

Indent with 4 spaces. Spaces inside delimiters: `{{ value }}`, `{% tag %}`, `{# comment #}`.

### File Naming

- `_underscore` prefix = partial (not directly accessible via URL). Use for includes, layouts, and components.
- No underscore = route entry point or publicly accessible template.
- Lowercase with hyphens for directories: `plugin-store/`, `entry-types/`.
- camelCase for form macro names: `textField`, `lightswitchField`.

### Template Directory Structure

```
templates/
├── _components/         # Reusable UI components (sidebars, cards)
├── _includes/           # Shared partials (forms, pagination)
├── _layouts/            # Base layouts for CP pages
├── settings/            # Settings pages (route-accessible)
│   ├── _edit.twig       # Edit partial
│   └── index.twig       # Index entry point
```

### Control Structures

```twig
{% if condition %}
    Something
{% endif %}

{% for item in items %}
    {{ item.title }}
{% endfor %}
```

### Form Macros

Import Craft's form helpers and use the object syntax:

```twig
{% import '_includes/forms.twig' as forms %}

{{ forms.textField({
    label: "Name"|t('app'),
    id: 'name',
    name: 'name',
    value: entity.name,
    errors: entity.getErrors('name'),
    required: true,
}) }}
```

### Defaults and Null Coalescing

Use `??` for safe defaults in templates:

```twig
{% set readOnly = readOnly ?? false %}
{% set title = title ?? 'Untitled'|t('app') %}
```

### Whitespace Control

Use `{%-` and `-%}` to trim surrounding whitespace in low-level components:

```twig
{%- set class = class ?? 'default' -%}
```

## Validation

Use `defineRules()` with array notation:

```php
protected function defineRules(): array
{
    $rules = parent::defineRules();
    $rules[] = [['name', 'handle'], 'required'];
    $rules[] = [['handle'], UniqueValidator::class, 'targetClass' => MyEntityRecord::class];
    $rules[] = [['batchSize'], 'integer', 'min' => 1, 'max' => 500];
    $rules[] = [['apiUrl'], 'url'];
    return $rules;
}
```

Always call `parent::defineRules()` first to inherit base validation. Use Craft's built-in validators (`HandleValidator`, `UniqueValidator`, `DateTimeValidator`) before writing custom ones.

## Translations

Always use the plugin handle as the translation category:

```php
Craft::t('pluginhandle', 'Some translatable text')
```

```twig
{{ 'Some translatable text'|t('pluginhandle') }}
```

In CP templates, translate labels inline with the `|t()` filter:

```twig
{{ forms.textField({
    label: "Field Label"|t('pluginhandle'),
    instructions: "Help text for this field."|t('pluginhandle'),
}) }}
```

Never hardcode user-facing strings. All CP labels, messages, and descriptions must go through `Craft::t()` or the `|t()` Twig filter.

## File Header

Every PHP file starts with:

```php
<?php
/**
 * <Plugin Name> plugin for Craft CMS
 *
 * <Plugin description>.
 *
 * @link      <Author URL>
 * @copyright Copyright (c) <Year> <Author Name>
 */

namespace vendor\pluginhandle\path\to;
```
