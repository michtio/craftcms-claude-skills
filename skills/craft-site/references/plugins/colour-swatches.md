# Colour Swatches

Visual colour picker field type by CraftPulse. Lets editors choose from predefined colour palettes with support for multi-colour swatches, Tailwind utility classes, and custom options per colour. CraftPulse's own plugin — used in 5/6 projects.

`craftpulse/craft-colour-swatches` — Free

## Documentation

- GitHub: https://github.com/craftpulse/craft-colour-swatches
- Plugin Store: https://plugins.craftcms.com/colour-swatches

## Common Pitfalls

- Treating a multi-colour swatch like a single one — for a single-colour swatch you read custom keys directly off the swatch (`swatch.background`), but a multi-colour swatch's `swatch.color` is an array you must iterate (`{% for c in swatch.color %}{{ c.background }}{% endfor %}`).
- Not defining a `default` swatch — if no swatch is pre-selected and the field is optional, template code must handle null values.
- Defining palettes in field settings instead of the config file — config-file palettes are reusable across fields and environments. Prefer `config/colour-swatches.php`.
- Missing the `color` key (required) in the colour definition — the `color` hex value is what renders the swatch preview. All other keys (like Tailwind classes) are custom options.
- Forgetting that `{{ swatch }}` returns the label, not the colour — string casting calls `__toString()` which returns `label`. Use the `.color` property (and custom keys like `.background`) for colour values.

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

The v5 swatch model uses **property access**, not method calls. The only callable is `collection()` (added in v5.1.0).

### Model Properties

```twig
{% set swatch = entry.colourField %}

{{ swatch }}                    {# Returns label (string cast via __toString()) #}
{{ swatch.label }}              {# "Primary" #}
{{ swatch.color }}              {# Single swatch: hex string. Multi-colour: array of colour objects #}
{{ swatch.background }}         {# Custom key, read directly off the swatch (single-colour) #}
{{ swatch.text }}               {# Any custom key you defined in the palette #}
```

For a single-colour swatch, the custom keys (`background`, `text`, etc.) are exposed directly on the swatch. For a multi-colour swatch, iterate `swatch.color` and read the keys off each colour object.

### Accessing Colour Values

Single-colour swatch — read custom keys directly:

```twig
{% set swatch = entry.colourField %}
{% if swatch %}
    <div class="{{ swatch.background ?? '' }} {{ swatch.text ?? '' }}">
        {{ entry.title }}
    </div>
{% endif %}
```

Multi-colour swatch (gradient) — iterate `swatch.color`:

```twig
{% set swatch = entry.colourField %}
{% if swatch %}
    {% for c in swatch.color %}
        <span class="{{ c.background ?? '' }} {{ c.text ?? '' }}">{{ c.color }}</span>
    {% endfor %}
{% endif %}
```

### Using with Tailwind Named-Key Collections

Colour Swatches pairs naturally with the named-key collection pattern (single-colour swatch):

```twig
{# _atoms/badge.twig #}
{% set defaults = collect({
    wrapper: swatch.background ?? 'bg-gray-100',
    text: swatch.text ?? 'text-gray-900',
}) %}

<span class="{{ defaults.get('wrapper') }} {{ defaults.get('text') }} rounded-full px-3 py-1 text-sm font-medium">
    {{ label }}
</span>
```

### Null Handling

```twig
{% set swatch = entry.colourField ?? null %}
{% set bgClass = swatch.background ?? 'bg-gray-100' %}
```

### Collection API

`collection()` (v5.1.0+) returns a recursive Laravel collection of the swatch's colour data — handy for `.pluck()`, `.filter()`, `.map()`, etc.

```twig
{# Pull every hex value #}
{% set hexValues = entry.colourField.collection().pluck('color').all() %}

{# Build a CSS gradient from all colours #}
{% set gradient = 'linear-gradient(' ~ entry.colourField.collection().pluck('color').implode(', ') ~ ')' %}

{# Filter on a custom key #}
{% set backgrounds = entry.colourField.collection()
    .pluck('background')
    .filter()
    .unique()
    .all() %}
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
