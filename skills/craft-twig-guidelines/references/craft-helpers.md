# Craft Twig Helpers

Reference for the Craft-registered tags, functions and filters that the conventions rely on: `{% tag %}`, `tag()`, `attr()`, `|attr`, `|parseAttr`, `|append`, `svg()`, `url()` with `false`, the `heading()` family [5.10+], the filter additions [5.10+], `collect()` versus the array filters, and safe output with inline assets.

## `{% tag %}` — Polymorphic Elements

Primary tool for rendering elements whose tag name depends on props.

```twig
{%- set element = props.get('url') ? 'a' : 'span' -%}

{%- tag element with {
    class: classes.implode(' '),
    href: props.get('url') ?? false,
    target: props.get('target') ?? false,
    rel: props.get('rel') ?? false,
    aria: {
        label: props.get('label') ?? false,
    },
} -%}
    {{ props.get('text') }}
{%- endtag -%}
```

Rules:
- Variable name must be descriptive: `element`, `heading`, `wrapper`. Never `el`, `hd`.
- `false` omits an attribute entirely from the rendered HTML.
- `null` also omits. Use `false` when explicitly excluding, `null` when absent.
- `class` accepts arrays with automatic falsy filtering.
- `aria` and `data` accept nested hashes that expand to `aria-*` / `data-*` attributes.

## `tag()` — Inline Element Function

For simple elements without complex inner content:

```twig
{{ tag('span', { class: 'sr-only', text: '(opens in new window)' }) }}
{{ tag('img', { src: image.url, alt: image.title, loading: 'lazy' }) }}
{{ tag('i', { class: ['fa-solid', icon], aria: { hidden: 'true' } }) }}

{# Craft 5.10+: pass a string as the second arg as a text-only shortcut #}
{{ tag('span', 'Read more') }}
```

- `text:` key = HTML-encoded content.
- `html:` key = raw HTML content (trusted input only).
- Self-closing elements (`img`, `input`, `br`) handled automatically.

## `attr()` — Attribute Strings

For building attributes in non-tag contexts:

```twig
<div{{ attr({ class: ['card', active ? 'card--active'], data: { id: entry.id } }) }}>
```

Returns a space-prefixed attribute string. Same `false`-means-omit and class
array filtering as `{% tag %}`.

## `|attr` Filter

For merging attributes onto existing HTML strings:

```twig
{{ svg('@webroot/icons/check.svg')|attr({ class: 'w-4 h-4', aria: { hidden: 'true' } }) }}
```

## `|parseAttr` Filter

For extracting attributes from an HTML string into a hash for manipulation:

```twig
{% set attributes = '<div class="foo" data-id="1">'|parseAttr %}
{# attributes = { class: 'foo', data: { id: '1' } } #}
```

## `|append` Filter

For adding content to an element string:

```twig
{{ svg('@webroot/icons/logo.svg')|append('<title>Company Logo</title>', 'replace') }}
```

## `svg()` Function

```twig
{{ svg('@webroot/icons/logo.svg') }}
{{ svg(entry.svgField.one()) }}
```

Combine with `|attr` for classes and aria attributes. Use `|append` for
accessible labels inside the SVG.

## `url()` with `false` Params [5.11+]

Passing `false` as the second argument strips every query-string param from
an absolute URL. Canonical links, share URLs, and "clear filters" links:

```twig
<link rel="canonical" href="{{ url(craft.app.request.absoluteUrl, false) }}">
<a href="{{ url(craft.app.request.absoluteUrl, false) }}">Clear filters</a>
```

An array still merges params in; `false` removes them all. The stripping
only applies when the passed-in URL is absolute, so feed it a full URL, not a
path. PHP has the same call as `UrlHelper::url($url, false)`, plus
`UrlHelper::removeParams($url, [...])` and `UrlHelper::removeAllParams($url)`
for finer control.
[5.11+] `false` is new. Before 5.11: rebuild the clean URL with
`siteUrl(craft.app.request.pathInfo)` instead.

## `heading()` / `h()` / `h1()`…`h6()` — Programmatic Headings [5.10+]

Build heading tags from a dynamic level without string-concatenation. Useful in
components that receive a `level` prop and need to render the matching tag
without doing `tag('h' ~ level, { text: title })` manually.

`heading()` and `h()` need [5.10+]. Before 5.10: build the tag from the level yourself. `{{ tag('h' ~ level, { text: title }) }}` (`tag()` takes an attributes array; `text` is encoded, `html` is not) or `{% tag 'h' ~ level with { class: 'text-xl' } %}Subsection{% endtag %}`. Don't ship `heading()` / `h()` to a site below 5.10.

```twig
{# heading(level, text-or-attributes) — level is an int 1-6 #}
{{ heading(2, 'Section title') }}                     {# <h2>Section title</h2> #}
{{ heading(3, { class: 'text-xl', text: 'Subsection' }) }}

{# h() is the short alias for heading() #}
{{ h(2, 'Section title') }}

{# Bound-level shortcuts — only attributes/text needed #}
{{ h1('Page title') }}
{{ h2('Section') }}
{{ h6({ class: 'sr-only', text: 'Hidden heading' }) }}
```

These are stateless tag builders — there's no auto-incrementing or current-level
tracking. Components that need to thread a level across nested contexts still
pass it as a prop. `heading()` throws `InvalidArgumentException` when level is
outside 1-6.

## Filter Additions [5.10+]

```twig
{{ price|number(locale: 'de-DE') }}                   {# locale arg #}
{{ entry.postDate|datetime('long', withTimeZone: true) }}
{{ deadline|time('short', withTimeZone: true) }}
{{ maybeNull|timestamp }}                              {# returns "now" for null/empty #}
```

## Filtering and Mapping — Default to `collect()`

For data manipulation in templates, **default to `collect()`** — one consistent, chainable API (`where`, `firstWhere`, `groupBy`, `keyBy`, `unique`, `pluck`, `map`, `filter`, `sortByDesc`) instead of mixing idioms:

```twig
{% set newsByYear = entries.collect
    .where('type', 'news')
    .sortByDesc('postDate')
    .groupBy(e => e.postDate|date('Y')) %}
```

The bare Twig/Craft array filters are fine for a **single trivial operation inline** — `{% for e in entries|filter(e => e.enabled) %}` — where a Collection adds nothing. But Twig's `|filter`/`|map` return plain arrays and Craft's `|where`/`|firstWhere`/`|group`/`|index` go through `ArrayHelper`, so they **don't chain like Collection methods**; once you need more than one step, switch to `collect()`. Don't mix both styles arbitrarily.

There is **no `|indexBy` filter** — key a list with `|index` (or `.keyBy()` on a Collection) and bucket with `|group` (or `.groupBy()`). (`|where`, `|firstWhere`, `|contains`, `|group`, `|index`, `|explodeClass`/`|explodeStyle` are all Craft-registered filters.)

## Safe Output and Inline Assets

- **`|t('category')`** — route every user-facing string through translation; never hardcode display copy.
- **`|purify`** — sanitize untrusted or rich HTML rather than reaching for `|raw`. Reserve `|raw` for trusted field output (CKEditor/Redactor); never `|raw` user-submitted or query-string-derived content.
- **`|explodeClass` / `|explodeStyle`** — normalize a class/style string to an array before merging, instead of hand-splitting on spaces.
- **`{% js %}` / `{% css %}` / `{% script %}`** — register inline assets through the View (it dedupes and positions them) instead of hand-writing `<script>`/`<style>`. (`{% js %}`/`{% css %}` go through the asset manager; `{% script %}`/`{% html %}` are verbatim.)
- **`{% dd %}` / `dump()`** — for debugging only; never ship them, and don't use `{{ x|json_encode }}` as a debug hack.
- **`|e('js')` escapes aggressively** — the standard Twig JS escaper converts *every* non-alphanumeric ASCII char, including a space (`0x20`), to a `\uXXXX` sequence (a space becomes ` `). Correct and safe for embedding strings in inline JS, but it means a translated multi-*word* string never appears verbatim in the output — so grepping rendered HTML/JS (or a test `assertSee()`) for the whole phrase silently misses. Match a single token or a raw JS identifier instead. See the `craftcms` skill's `testing.md` for the QA/grep side.

