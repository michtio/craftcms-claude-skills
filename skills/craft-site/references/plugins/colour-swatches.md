# Colour Swatches

Visual colour picker field type by CraftPulse. Lets editors choose from predefined colour palettes with support for multi-colour swatches, Tailwind utility classes, and custom options per colour. CraftPulse's own plugin — used in 5/6 projects.

`craftpulse/craft-colour-swatches` — Free

## Documentation

- GitHub: https://github.com/craftpulse/craft-colour-swatches
- Plugin Store: https://plugins.craftcms.com/colour-swatches

## Common Pitfalls

- Accessing `.color` directly as a string when it's an array — each swatch can have multiple colours (for gradient or multi-colour swatches). Always iterate or access by index.
- Not defining a `default` swatch — if no swatch is pre-selected and the field is optional, template code must handle null values.
- Defining palettes in field settings instead of the config file — config-file palettes are reusable across fields and environments. Prefer `config/colour-swatches.php`.
- Missing the `color` key (required) in the colour definition — the `color` hex value is what renders the swatch preview. All other keys (like Tailwind classes) are custom options.
- Forgetting that `{{ swatch }}` returns the label, not the colour — string casting calls `__toString()` which returns `label`. Use `.colors()` or `.color` for colour values.

## Config File

Define reusable palettes in `config/colour-swatches.php`:

```php
// config/colour-swatches.php
return [
    'palettes' => [
        'Brand Colours' => [
            [
                'label' => 'Primary',
                'default' => true,
                'class' => null,
                'color' => [
                    [
                        'color' => '#0284c7',           // Required — renders the swatch preview
                        'background' => 'bg-brand-primary',
                        'backgroundHover' => 'hover:bg-brand-primary-dark',
                        'text' => 'text-white',
                    ],
                ],
            ],
            [
                'label' => 'Secondary',
                'default' => false,
                'class' => null,
                'color' => [
                    [
                        'color' => '#059669',
                        'background' => 'bg-brand-secondary',
                        'backgroundHover' => 'hover:bg-brand-secondary-dark',
                        'text' => 'text-white',
                    ],
                ],
            ],
            [
                'label' => 'Gradient (Sky/Rose)',
                'default' => false,
                'class' => 'bg-gradient-to-r from-sky-500 to-rose-600',
                'color' => [
                    [
                        'color' => '#0ea5e9',
                        'background' => 'bg-sky-500',
                        'text' => 'text-white',
                    ],
                    [
                        'color' => '#e11d48',
                        'background' => 'bg-rose-600',
                        'text' => 'text-white',
                    ],
                ],
            ],
        ],
    ],
];
```

### Palette Structure

Each swatch entry has:

| Key | Type | Description |
|-----|------|-------------|
| `label` | `string` | Display name (also returned by `__toString()`) |
| `default` | `bool` | Whether this swatch is pre-selected |
| `class` | `string\|null` | Extra CSS class(es) for the swatch (e.g., gradient) |
| `color` | `array` | Array of colour definitions (supports multi-colour) |

Each colour definition has:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `color` | `string` | ✅ | Hex colour for the swatch preview |
| *custom keys* | `string` | No | Any additional keys (Tailwind classes, CSS vars, etc.) |

Custom keys are whatever your project needs — `background`, `backgroundHover`, `text`, `textHover`, `border`, CSS custom properties, etc.

## Twig API

### Model Properties

```twig
{% set swatch = entry.colourField %}

{{ swatch }}                    {# Returns label (string cast) #}
{{ swatch.label }}              {# "Primary" #}
{{ swatch.colors() }}           {# Array of colour definitions #}
{{ swatch.labels() }}           {# Label string #}
{{ swatch.default() }}          {# Boolean — is this the default? #}
{{ swatch.class() }}            {# Extra class string or null #}
```

### Accessing Colour Values

Single-colour swatch:

```twig
{% set swatch = entry.colourField %}
{% if swatch and swatch.colors() %}
    {% set colorData = swatch.colors()|first %}
    <div class="{{ colorData.background ?? '' }} {{ colorData.text ?? '' }}">
        {{ entry.title }}
    </div>
{% endif %}
```

Multi-colour swatch (gradient):

```twig
{% set swatch = entry.colourField %}
{% if swatch and swatch.class() %}
    <div class="{{ swatch.class() }}">
        Gradient background
    </div>
{% endif %}
```

### Using with Tailwind Named-Key Collections

Colour Swatches pairs naturally with the named-key collection pattern:

```twig
{# _atoms/badge.twig #}
{% set defaults = collect({
    wrapper: swatch.colors()|first.background ?? 'bg-gray-100',
    text: swatch.colors()|first.text ?? 'text-gray-900',
}) %}

<span class="{{ defaults.get('wrapper') }} {{ defaults.get('text') }} rounded-full px-3 py-1 text-sm font-medium">
    {{ label }}
</span>
```

### Null Handling

```twig
{% set swatch = entry.colourField ?? null %}
{% set bgClass = swatch ? (swatch.colors()|first.background ?? 'bg-gray-100') : 'bg-gray-100' %}
```

### Collection API

```twig
{% set collection = entry.colourField.collection() %}
{# Returns an Illuminate Collection of colour data #}
```

## Element Queries

Filter entries by colour swatch value:

```twig
{# Colour Swatches stores JSON — use raw query for filtering #}
{% set entries = craft.entries
    .section('news')
    .colourField(':notempty:')
    .all() %}
```

## Use Cases

- **Section/category theming** — assign brand colours to sections, apply in templates
- **Card accents** — editors pick highlight colours for cards, banners, CTAs
- **Multi-brand sites** — different palettes per brand, stored in config
- **Gradient presets** — multi-colour swatches with Tailwind gradient classes
