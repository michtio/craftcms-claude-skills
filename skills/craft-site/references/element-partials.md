# Element Partials

How to use `entry.render()`, the `{% render %}` tag [5.12+] and the `_partials/` template directory in Craft CMS 5 for reusable element rendering. Element partials are a front-end feature — the CP does not use them. For CP element display (chips, cards, table rows), see the craftcms skill's `element-index.md`.

## Documentation

- Element partials: https://craftcms.com/docs/5.x/system/elements.html#rendering-elements
- `{% render %}` tag: https://craftcms.com/docs/5.x/reference/twig/tags.html#render
- Collections `render()`: https://craftcms.com/docs/5.x/development/collections.html

## Common Pitfalls

- Forgetting to create the partial template — `render()` silently falls back to a `<p>` tag with the element's title. No error, no warning — just a plain text title where your card should be.
- N+1 queries inside partials — use `.eagerly()` for any related element queries. Each partial renders independently, so without eager loading, every card in a grid fires separate queries.
- Assuming `render()` works in the CP — it's front-end only (`TEMPLATE_MODE_SITE`).
- Hardcoding the partial path instead of using the convention — the lookup path is automatic. Don't `{% include %}` the partial manually when `entry.render()` works.
- Shipping `{% render %}` to a site below 5.12 [5.12+]: it's an unknown tag there, and Twig fails to compile the **whole template**, even when the tag sits inside an `{% if %}` that never runs. Templates that must run on 5.11 and 5.12 (plugin example templates, shared component libraries, a staging site not yet upgraded) use the `.render()` method instead.
- Expecting `entry` inside a partial to be the page entry: the partial's `entry` is always the element being rendered (the Matrix block, the card), with or without `only`. Pass the page explicitly (`with { page: entry }`) or use `entry.owner` for nested entries.
- Relying on `loop is defined` in partials [changed 5.12]: list renders (`{% render entries %}`, `entries.render()`, `query.render()`) now hand each partial a `loop` variable. Before 5.12: partials rendered through `.render()` on a collection or query got no `loop`. When supporting both: `loop.index ?? null`.
- Overriding an entry type's handle per field and expecting the partial to follow — it does, but only from [5.10.14+]. Before 5.10.14: from 5.10.4 the override is respected but not prioritized, and before 5.10.4 it is ignored, so keep the partial under the original handle when supporting older releases.

## Contents

- [How It Works](#how-it-works)
- [The `{% render %}` Tag](#the--render--tag-512)
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

## The `{% render %}` Tag [5.12+]

`{% render %}` outputs an element, or a list of elements, through the same partial lookup as `render()` (https://github.com/craftcms/cms/blob/5.12.4/src/web/twig/tokenparsers/RenderTokenParser.php). [5.12+] Before 5.12: use `{{ entry.render({...}) }}` or `{{ entry.myMatrix.eagerly().render() }}`.

```twig
{% render entry %}
{% render entry.contentBlocks with { theme: 'dark' } only %}
{% render craft.entries().section('news').limit(6) with { size: 'card' } only %}
```

- **Input**: an element (any `craft\base\Renderable`), an array, a Collection, or an element query (it runs the query). `null` or an empty list outputs nothing. A non-renderable item in a list throws `… isn't renderable.`
- **`with` / `only`**: same grammar as `{% include %}`: `with { … }`, `with { … } only`, or `only` alone. Without `only`, the partial also receives the whole current template context; with `only`, just the `with` variables plus the element. House style: always add `only`, like `{% include %}` (see `craft-twig-guidelines`). `ignore missing` and `sandboxed` aren't supported.
- **`loop`**: when a list is rendered, each partial gets a `loop` hash (`index`, `index0`, `revindex`, `revindex0`, `first`, `last`, `length`, `parent`), unless you pass your own `loop` in `with`. A single element rendered inside `{% for %}` without `only` sees the outer loop's `loop` through the context instead.
- **Output**: list results are joined with a newline and returned as safe markup.
- **Tag vs method**: the tag passes the template context (unless `only`); `entry.render()` and `collection.render()` pass only the variables you give them.

### `render()` on collections and queries [changed 5.12]

- `collect([...]).render()` and `query.collect().render()` work on any Laravel Collection of renderable items [5.12+] (a `Collection::render()` macro). `ElementCollection` no longer has its own `render()` method; the macro keeps the same call syntax, so `entry.myMatrix.eagerly().render()` is unchanged.
- `query.render()` renders `query.all()` through the same code.
- List renders inject `loop` (see above) [changed 5.12]. Before 5.12: `ElementCollection::render()` went through `ElementHelper::renderElements()` and passed no `loop`.
- PHP: `ElementHelper::renderElements()` is [deprecated 5.12] in favour of `craft\helpers\Template::render($elements, $variables)` [5.12+]. The deprecation is docblock-only (nothing reaches the deprecation log). Code that must also run before 5.12 keeps `ElementHelper::renderElements()`, which works on both.
- Non-element objects can implement `craft\base\Renderable` [5.12+] (`render(array $variables = []): Markup`) to work with the tag.

## Template Lookup Path

`render()` builds a list of candidate templates and renders the first one that exists (lowest priority number wins). [5.8+] Plugins can add or reorder candidates through `Element::EVENT_RENDER`.

### Priority 1: Overridden entry type handle [5.10.14+]

```
_partials/{refHandle}/{overriddenHandle}.twig
```

Entries only, and only when the entry type's handle is overridden for the field or section it's used in (per-usage overrides, [5.6+]). Before 5.10.14: this candidate wasn't checked first (5.10.4 to 5.10.13 respected the override without prioritizing it; earlier releases ignored it), so a `cta` type renamed to `richTextCta` inside a CKEditor field could still render `_partials/entry/cta.twig` (craftcms/cms#18968).

### Priority 2: Type-specific partial

```
_partials/{refHandle}/{providerHandle}.twig
```

- `{refHandle}` — the element's reference handle: `entry`, `asset`, `user`, `address`
- `{providerHandle}` — the field layout provider's handle: for entries, this is the **original entry type handle**

Examples:
```
_partials/entry/article.twig       ← article entry type
_partials/entry/blogPost.twig      ← blogPost entry type
_partials/asset/image.twig         ← (if assets had type-specific layouts)
_partials/user.twig                ← user fallback (no type handle)
```

### Priority 3: Generic fallback

```
_partials/{refHandle}.twig
```

Examples:
```
_partials/entry.twig               ← fallback for all entry types
_partials/asset.twig               ← fallback for all assets
```

The most specific existing template wins. The generic fallback catches everything else.

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
    .with(['featuredImage', 'author', 'topics'])
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

[5.12+] The same in one line, with `loop` available in each block partial:

```twig
{% render entry.contentBlocks.eagerly() with { page: entry } only %}
```

Each block type gets its own partial: `_partials/entry/heroBlock.twig`, `_partials/entry/textBlock.twig`, etc.

### Eager loading inside partials

Use `.eagerly()` on **custom relation fields** to avoid N+1 queries when rendering a list:

```twig
{# _partials/entry/article.twig #}
{% set image = entry.featuredImage.eagerly().one() %}   {# custom Assets field #}
{% set categories = entry.topics.eagerly().all() %}     {# custom relation field #}
{% set author = entry.author %}                          {# native attribute — access directly #}
```

`.eagerly()` batches queries across all partials in the same render cycle.

**Native attributes can't be `.eagerly()`-loaded.** `entry.author` (also `entry.authors`, an asset's `uploader`, a user's `photo`) returns the element directly — not a query — so there's no `.eagerly()`/`.one()` to chain; `entry.author.eagerly()` throws. [5.8+] `entry.author`/`entry.authors` batch themselves across the query result, so a bare `entry.author` in a partial costs one query per listing; anything below the author (`author.photo`, author fields) does not, so cover it with `.with(['author.photo'])` on the **outer** query, as the Blog card grid above does with `.with(['author'])`. See `craft-content-modeling` → `relations-and-eager-loading.md` for the full `.with()`-vs-`.eagerly()` rules.

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
