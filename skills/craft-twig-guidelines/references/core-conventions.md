# Core Conventions: Naming, Nulls, Whitespace, Isolation, Headers

The full form of the always-on rules in SKILL.md: variable naming, null handling, whitespace control, include and render isolation, macros, comment headers, `collect()` class conventions and copy style, each with correct and wrong examples. The last section holds the long form of the SKILL.md pitfalls that only carry a one-liner there.

## Variable Naming

Single-word, descriptive, lowercase preferred. When multi-word is needed, use
camelCase.

```twig
{# Correct #}
{% set heading = entry.title %}
{% set image = entry.heroImage.one() %}
{% set items = navigation.links.all() %}
{% set element = props.get('url') ? 'a' : 'span' %}
{% set buttonText = entry.callToAction %}
{% set containerClass = 'max-w-3xl' %}

{# Wrong — abbreviations #}
{% set el = props.get('url') ? 'a' : 'span' %}
{% set btn = entry.callToAction %}
{% set nav = navigation.links.all() %}

{# Wrong — snake_case #}
{% set button_text = entry.callToAction %}
{% set container_class = 'max-w-3xl' %}
```

No abbreviations: `element` not `el`, `button` not `btn`, `navigation` not `nav`,
`description` not `desc`.

Prefer single-word names when context makes the meaning clear (e.g. `heading`
inside a component is better than `sectionHeading`). But multi-word camelCase is
perfectly fine when needed for clarity.

## Null Handling

`??` is the default. Always safe, always portable.

`???` (empty coalesce) is acceptable if the project already has `nystudio107/craft-emptycoalesce` or `nystudio107/craft-seomatic` installed — both provide the operator. But never install a plugin just for `???`. Check `composer.json` first.

```twig
{# Always correct #}
{% set heading = entry.heading ?? '' %}
{% set image = entry.heroImage.one() ?? null %}
{{ props.get('label') ?? 'Default' }}

{# OK if empty-coalesce or SEOmatic is installed — checks empty, not just null #}
{% set heading = entry.heading ??? '' %}

{# Wrong — verbose, unnecessary #}
{% if entry.heading is defined and entry.heading is not null %}
{% if entry.heading is not defined %}
```

Craft 5 supports the nullsafe operator (`?.`). Use it for deep traversal through
chains that may have null links — it propagates `null` cleanly without the verbose
`is defined and is not null` dance:

```twig
{# Reach for ?. when any link in the chain may be null #}
{{ entry?.author?.fullName ?? 'Anonymous' }}

{# ?? alone is enough when only the leaf is in question #}
{{ entry.title ?? '' }}
```

`??` stays the right tool for simple "value or fallback" cases; `?.` is for chains
where intermediate links may be missing. Don't reach for `?.` on a single property
access — it adds noise without adding safety.

## Whitespace Control

Use `{%-` and `{{-` for whitespace trimming. Never use `{%- minify -%}`.

```twig
{# Correct — surgical whitespace control #}
{%- set heading = entry.title -%}
{%- if heading -%}
    {{- heading -}}
{%- endif -%}

{# Wrong — deprecated minification approach #}
{%- minify -%}
    {% set heading = entry.title %}
{%- endminify -%}
```

Apply whitespace control on tags that produce unwanted blank lines in output.
Not every tag needs it — use where visible output whitespace matters.

## Include Isolation

Every `{% include %}` MUST use `only`. No exceptions.

```twig
{# Correct — explicit, isolated #}
{%- include '_atoms/buttons/button--primary' with {
    text: entry.title,
    url: entry.url,
} only -%}

{# Wrong — ambient variables leak in #}
{%- include '_atoms/buttons/button--primary' with {
    text: entry.title,
    url: entry.url,
} -%}
```

Without `only`, a component can silently depend on variables from its parent
scope, creating invisible coupling.

The same rule covers `{% render %}` [5.12+], which takes the same `with … only`
grammar (or `only` alone). Without `only` the element partial receives the whole
parent context:

```twig
{# Correct #}
{%- render entry.contentBlocks with { theme: 'dark' } only -%}

{# Wrong: every parent variable leaks into each partial #}
{%- render entry.contentBlocks with { theme: 'dark' } -%}
```

[5.12+] Before 5.12: the tag doesn't exist and fails the whole template at compile time,
so on older sites (or templates shared with them) use `{{ entry.contentBlocks.render({ theme: 'dark' }) }}`,
which passes only the given variables. Inside the partial, `entry` is the rendered
element, never the page entry: pass the page in `with` when the partial needs it.
Partial lookup, `loop` and the collection `render()` method: `craft-site`
(`references/element-partials.md`).

`include_only()` [5.12+] (Twig 3.29) is the function form of an isolated include:
`{{ include_only('_atoms/badge', { text: label }) }}`. [5.12+] Before 5.12:
`{{ include('_atoms/badge', { text: label }, with_context = false) }}`.

## No Macros for Components

Never use `{% macro %}` for UI components. Macros don't support extends/block
and their scoping model differs from includes.

```twig
{# Wrong — macro for a component #}
{% macro button(text, url) %}
    <a href="{{ url }}">{{ text }}</a>
{% endmacro %}

{# Correct — include with isolation #}
{%- include '_atoms/buttons/button--primary' with {
    text: text,
    url: url,
} only -%}
```

Macros are acceptable for utility functions that return strings (e.g., formatting
helpers), not for rendering UI.

## Comment Headers

Every component file gets a section header comment:

```twig
{# =========================================================================
   Component Name
   Brief description of what this component does.
   ========================================================================= #}
```

Props files, variant files, views, layouts — all get headers. The `=========`
separator matches the PHP convention from `craft-php-guidelines`.

## `collect()` Conventions

When building props and class collections, these are the style rules to enforce:

- **camelCase keys** — `heroImage`, never `hero_image`.
- **One named key per concern** — a class collection gets one key per style
  concern (`layout`, `color`, `spacing`, …), never two classes fighting over the
  same element.
- **Build class strings with `.implode(' ')`** — never string concatenation
  (`'flex ' ~ extraClass`).
- **Null/empty values are harmless** — `implode(' ')` joins them as empty strings,
  producing extra spaces that browsers normalize in class attributes.

```twig
{%- set classes = collect({
    layout: 'flex items-center gap-2',
    color: 'bg-brand-primary text-brand-on-primary',
    hover: 'hover:bg-brand-accent',
    utilities: props.get('utilities'),
}) -%}

class="{{ classes.implode(' ') }}"
```

For the full `collect()` method reference and architecture patterns (props
collection, `get()`/`merge()`, entry-queries-as-Collections), see `craft-site`
(`references/twig-collections.md`); for the named-key Tailwind class pattern, see
`craft-site` (`references/tailwind-conventions.md`).

## Copy style

Never use em-dashes (—) or en-dashes (–) in user-facing copy: template text, `|t` strings, and any content authored into templates. Use commas, periods, colons, or parentheses instead; for ranges write "4 to 10" or a plain ASCII hyphen ("4-10"). Plain hyphens are fine. Twig comments (`{# … #}`) are exempt. Grep your templates for `—` and `–` before finishing. (This is the front-end half of the shared rule; the `craft-php-guidelines` skill carries the same rule for `Craft::t()` strings, field labels, CP notices, and docs.)

## Pitfalls in Detail

- **`is empty` / `|default` on Craft Models** [changed 5.10] — from 5.10 any `yii\base\Model` (entries, settings, custom models) is treated as non-empty regardless of its property values; before 5.10 these checks did not treat every model as non-empty. Means `{{ user|default('Guest') }}` always renders the user object; `{% if entry is empty %}` always false. Check the specific property you care about: `{% if entry.title is empty %}`.
- **Blocks inside conditionals** — `{% if %}{% block foo %}{% endblock %}{% endif %}` is invalid Twig. Blocks are compile-time structures and cannot be conditionally defined. Move the conditional inside the block: `{% block foo %}{% if condition %}...{% endif %}{% endblock %}`.
- **Hardcoded `/admin` CP URL** — `cpTrigger` is configurable via `CRAFT_CP_TRIGGER` env var or `cpTrigger` in general.php. Many projects use `cp` instead of `admin`. Use `cpUrl()` function or check `.env` — never hardcode `/admin/`.
- **Twig has no `instanceof`** — PHP that scopes behaviour per class (e.g. `match (true)` over `instanceof` checks in a controller) has no direct template equivalent, and the two silently drift when the template approximates it. Branch on a capability instead (`object.hasProperty('handle')`, `object.hasMethod(...)`), or have PHP pass an explicit discriminator (`type: 'entry'`) into the template.
- **Per-request output inside `{% cache %}`**: the tag stores the body and replays the `{% js %}`, `{% script %}` and `{% css %}` it captured, so a CSP nonce, `csrfInput()`, `aria-current`/active classes or language-switcher URLs inside it are frozen at the first render. Cache the query and its markup; keep those outside. Parameters go in one order only (`globally`, `using key`, `for 1 hour`/`until`, `if`/`unless`), and there is no `tag()`. See the `craft-site` skill's `template-caching.md`.
- **Grepping output for a `|e('js')`-escaped phrase** — the JS escaper turns every space into ` `, so a translated multi-word string never appears verbatim in rendered JS. Grep/assert on a single token or raw identifier. See `references/craft-helpers.md` (Safe Output and Inline Assets) and the `craftcms` skill's `testing.md`.
