# Element Partials

How to use `entry.render()` and the `_partials/` template directory in Craft CMS 5 for reusable element rendering. Element partials are a front-end feature — the CP does not use them. For CP element display (chips, cards, table rows), see the craftcms skill's `element-index.md`.

## Documentation

- Element partials: https://craftcms.com/docs/5.x/system/elements.html#rendering-elements

## Common Pitfalls

- Forgetting to create the partial template — `render()` silently falls back to a `<p>` tag with the element's title. No error, no warning — just a plain text title where your card should be.
- N+1 queries inside partials — use `.eagerly()` for any related element queries. Each partial renders independently, so without eager loading, every card in a grid fires separate queries.
- Assuming `render()` works in the CP — it's front-end only (`TEMPLATE_MODE_SITE`).
- Hardcoding the partial path instead of using the convention — the lookup path is automatic. Don't `{% include %}` the partial manually when `entry.render()` works.

## Contents

- [How It Works](#how-it-works)
- [Template Lookup Path](#template-lookup-path)
- [Available Variables](#available-variables)
- [Passing Custom Variables](#passing-custom-variables)
- [Common Patterns](#common-patterns)
- [Configuration](#configuration)

## How It Works

Every element in Craft 5 has a `render()` method that looks for a matching template in `_partials/`, renders it, and returns the HTML as a `Twig\Markup` object (safe for direct output).

```twig
{# Render a single entry #}
{{ entry.render() }}

{# Render a list of entries #}
{% for entry in craft.entries().section('blog').limit(10).all() %}
    {{ entry.render() }}
{% endfor %}

{# Render with custom variables #}
{{ entry.render({ size: 'compact', showExcerpt: false }) }}
```

If no matching template exists, `render()` falls back to a `<p>` tag containing the element's title — no error is thrown.

## Template Lookup Path

`render()` searches for templates in priority order:

### Priority 1: Type-specific partial

```
_partials/{refHandle}/{providerHandle}.twig
```

- `{refHandle}` — the element's reference handle: `entry`, `asset`, `user`, `address`
- `{providerHandle}` — the field layout provider's handle: for entries, this is the **entry type handle**

Examples:
```
_partials/entry/article.twig       ← article entry type
_partials/entry/blogPost.twig      ← blogPost entry type
_partials/asset/image.twig         ← (if assets had type-specific layouts)
_partials/user.twig                ← user fallback (no type handle)
```

### Priority 2: Generic fallback

```
_partials/{refHandle}.twig
```

Examples:
```
_partials/entry.twig               ← fallback for all entry types
_partials/asset.twig               ← fallback for all assets
```

The type-specific template takes priority when it exists. The generic fallback catches everything else.

## Available Variables

Inside the partial template, the element is available under its reference handle:

| Element Type | Variable Name |
|-------------|---------------|
| Entry | `entry` |
| Asset | `asset` |
| User | `user` |
| Address | `address` |
| Custom element | The element's `refHandle()` return value |

For nested entries (Matrix, CKEditor), the `entry` variable has `owner` and `field` properties for accessing the parent context.

## Passing Custom Variables

Pass an associative array to `render()`. The variables merge into the template context:

```twig
{{ entry.render({ size: 'hero', showMeta: true, imagePreset: 'wide' }) }}
```

In the partial, guard with defaults:

```twig
{# _partials/entry/article.twig #}
{% set size = size ?? 'default' %}
{% set showMeta = showMeta ?? true %}
{% set imagePreset = imagePreset ?? 'card' %}

<article class="article article--{{ size }}">
    {% set image = entry.featuredImage.eagerly().one() %}
    {% if image %}
        {{ image.render({ preset: imagePreset }) }}
    {% endif %}

    <h3><a href="{{ entry.url }}">{{ entry.title }}</a></h3>

    {% if showMeta %}
        <time datetime="{{ entry.postDate | atom }}">
            {{ entry.postDate | date('M j, Y') }}
        </time>
    {% endif %}
</article>
```

## Common Patterns

### Blog card grid

```twig
{# templates/blog/index.twig #}
{% set entries = craft.entries()
    .section('blog')
    .with(['featuredImage'])
    .limit(12)
    .all() %}

<div class="grid grid-cols-3 gap-6">
    {% for entry in entries %}
        {{ entry.render({ size: 'card' }) }}
    {% endfor %}
</div>
```

### Varying layout by entry type

The type-specific lookup means different entry types render differently without conditionals:

```
_partials/entry/article.twig      ← article layout (image + excerpt)
_partials/entry/video.twig        ← video layout (embed + duration)
_partials/entry/event.twig        ← event layout (date + venue)
```

```twig
{# All entries render with their own partial — no if/switch needed #}
{% for entry in entries %}
    {{ entry.render() }}
{% endfor %}
```

### Nested element rendering

Matrix entries and CKEditor nested entries also support `render()`:

```twig
{# Render Matrix blocks #}
{% for block in entry.contentBlocks.all() %}
    {{ block.render() }}
{% endfor %}
```

Each block type gets its own partial: `_partials/entry/heroBlock.twig`, `_partials/entry/textBlock.twig`, etc.

### Eager loading inside partials

Use `.eagerly()` to avoid N+1 queries when rendering a list:

```twig
{# _partials/entry/article.twig #}
{% set image = entry.featuredImage.eagerly().one() %}
{% set author = entry.author.eagerly().one() %}
{% set categories = entry.topics.eagerly().all() %}
```

`.eagerly()` batches queries across all partials in the same render cycle.

### Asset partials

```twig
{# _partials/asset.twig #}
{% set preset = preset ?? 'default' %}

{% if asset.kind == 'image' %}
    <img src="{{ asset.url }}"
         width="{{ asset.width }}"
         height="{{ asset.height }}"
         alt="{{ asset.alt ?? asset.title }}"
         loading="lazy">
{% else %}
    <a href="{{ asset.url }}">{{ asset.title }}</a>
{% endif %}
```

## Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| `partialTemplatesPath` | `'_partials'` | Base directory within `templates/` for partial lookup |

```php
// config/general.php
->partialTemplatesPath('_components/partials')
```

Or via environment variable: `CRAFT_PARTIAL_TEMPLATES_PATH`.
