# Atomic Patterns — Craft CMS Twig Implementation

> How atomic design principles are implemented in Craft CMS 5 Twig templates.
> This covers individual component construction: the props/extends/block pattern
> and the four core atom types (button, link, text, icon).
> For composing atoms into molecules, organisms, and structural layouts, see `composition-patterns.md`.
> For the underlying methodology, see `atomic-design.md`.
> For Twig coding standards (`{% tag %}`, `attr()`, naming, null handling), see `craft-twig-guidelines`.

## Documentation

- Twig `{% tag %}`: https://craftcms.com/docs/5.x/reference/twig/tags.html#tag
- Twig `tag()`: https://craftcms.com/docs/5.x/reference/twig/functions.html#tag
- Twig `attr()`: https://craftcms.com/docs/5.x/reference/twig/functions.html#attr
- Twig `{% include %}`: https://twig.symfony.com/doc/3.x/tags/include.html
- Twig `{% extends %}`: https://twig.symfony.com/doc/3.x/tags/extends.html

## Common Pitfalls

- Forgetting `only` on `{% include %}` — ambient variables leak in silently.
- Using `{% if variant == 'x' %}` to switch styles — use extends/block instead.
- Putting HTML in the props file — props declare data. Zero rendering.
- Naming by parent context (`hero-button`) — name by visual treatment (`button--primary`).
- Passing `external` as a prop — derived from URL inside the component, never passed.
- Missing block name in props file — must match the component type.
- Tracking props on components — decouple to data attributes at view level.

## Table of Contents

- [Three-Tier Implementation](#three-tier-implementation)
- [The Props File](#the-props-file)
- [The Variant File (Extends/Block)](#the-variant-file)
- [Button Atom](#button-atom)
- [Link Atom](#link-atom)
- [Text Atom](#text-atom)
- [Icon Atom](#icon-atom)

## Three-Tier Implementation

The 5-tier atomic design model compresses to 3 component tiers plus
infrastructure. See `atomic-design.md` for why this compression works.

| Tier | Directory | What it contains |
|------|-----------|-----------------|
| **Atom** | `_atoms/` | Single UI elements. No child components. Pure HTML + Tailwind. |
| **Molecule** | `_molecules/` | Small compositions of atoms. A functional unit. |
| **Organism** | `_organisms/` | Page-section-scale compositions. Molecules + atoms. |

Frost's "templates" and "pages" map to infrastructure outside the component
system — layouts in `_boilerplate/_layouts/` handle document scaffolding, while
views in `_views/` compose organisms into page-specific arrangements. These are
not components — they're the infrastructure that consumes components. See
`boilerplate-routing.md` for the full template chain.

Design tokens (CSS custom properties for brand colors, fonts, spacing) sit
below atoms — see `tailwind-conventions.md` for the token architecture.

## The Props File

Every component category has a props base file that declares its data interface.
One props file per category, shared across all variants.

**Naming:** `_component--props.twig` — underscore prefix, `--props` suffix.

```twig
{# =========================================================================
   Button — Props
   Declares the data interface for all button variants.
   ========================================================================= #}

{%- set props = collect({
    icon: icon ?? null,
    position: position ?? 'after',
    rel: rel ?? null,
    size: size ?? 'text-base',
    target: target ?? null,
    text: text ?? '',
    type: type ?? null,
    url: url ?? null,
    utilities: utilities ?? null,
}) -%}

{# External link detection — derived, never passed #}
{%- set external = props.get('url')
    and props.get('url') starts with 'http'
    and siteUrl not in props.get('url')
-%}

{%- set props = props.merge({
    external: external,
    target: props.get('target') ?? (external ? '_blank' : null),
    rel: props.get('rel') ?? (external ? 'noopener noreferrer' : null),
}) -%}

{%- block button -%}{%- endblock -%}
```

### Props File Rules

- `collect({})` wraps all props — full Collection API available.
- `??` for every default. See `craft-twig-guidelines` for null handling rules.
- Derived values (like `external`) computed from other props, never passed by caller.
- Block name matches the component type (`button`, `card`, `hero`).
- Zero HTML. This file is data structure only.

## The Variant File

Extends the props base. Defines the visual treatment: classes and HTML.

**Naming:** `component--variant.twig` — no underscore, `--variant` suffix.

Variants use the extends/block pattern: the base template (props file) defines
the data contract, the variant template fills the block with rendering logic.
When a component needs visual variants (primary/secondary/outline), each is a
separate variant file extending the same props base — never `{% if %}` conditionals.

## Button Atom

Buttons are action elements. The HTML tag resolves from props: `url` -> `<a>`,
`type` -> `<button>`, neither -> `<span>`. This is the polymorphic element pattern.

```twig
{# =========================================================================
   Button — Primary
   Main CTA. Filled background, prominent visual weight.
   ========================================================================= #}

{%- extends '_atoms/buttons/_button--props' -%}

{%- block button -%}

    {%- set element = props.get('url') ? 'a' : (props.get('type') ? 'button' : 'span') -%}

    {%- set classes = collect({
        layout: 'inline-flex items-center group w-fit',
        color: 'bg-brand-accent text-brand-on-accent',
        font: 'font-heading font-bold',
        size: props.get('size'),
        hover: 'hover:bg-brand-accent-hover',
        focus: 'focus:ring-2 focus:ring-brand-focus focus:ring-offset-1 focus:outline-none',
        radius: 'rounded-lg',
        spacing: 'py-2 px-4 gap-2',
        utilities: props.get('utilities'),
    }) -%}

    {%- tag element with {
        class: classes.implode(' '),
        href: props.get('url') ?? false,
        target: props.get('target') ?? false,
        rel: props.get('rel') ?? false,
        type: props.get('url') ? false : (props.get('type') ?? false),
        aria: {
            label: not props.get('text') ? props.get('label') : false,
        },
    } -%}

        {%- if props.get('text') -%}
            {{- tag('span', { text: props.get('text') }) -}}
        {%- endif -%}

        {%- if props.get('icon') -%}
            {{- tag('i', {
                class: [props.get('icon'), 'transition-all duration-250 ease-in-out'],
                aria: { hidden: 'true' },
                role: 'presentation',
            }) -}}
        {%- endif -%}

        {%- if props.get('external') -%}
            {{- tag('i', {
                class: 'fa-solid fa-arrow-up-right-from-square text-xs ml-1',
                aria: { hidden: 'true' },
            }) -}}
            {{- tag('span', { class: 'sr-only', text: '(opens in new window)' }) -}}
        {%- endif -%}

    {%- endtag -%}

{%- endblock -%}
```

### Variant Rules

- Named-key class collections — see `tailwind-conventions.md` for the full pattern.
- `false` omits attributes — see `craft-twig-guidelines` for `{% tag %}` conventions.
- External link indicator rendered inside the component, not by the caller.
- `utilities` is always the last key — additive, not overriding.

## Link Atom

Links are navigation elements. Always `<a>`. They never resolve to `<button>`
or `<span>` — that's the key difference from buttons.

```twig
{# =========================================================================
   Link — Props
   ========================================================================= #}

{%- set props = collect({
    text: text ?? '',
    url: url ?? null,
    icon: icon ?? null,
    active: active ?? false,
    utilities: utilities ?? null,
}) -%}

{%- set external = props.get('url')
    and props.get('url') starts with 'http'
    and siteUrl not in props.get('url')
-%}

{%- set props = props.merge({
    external: external,
    target: external ? '_blank' : false,
    rel: external ? 'noopener noreferrer' : false,
}) -%}

{%- block link -%}{%- endblock -%}
```

```twig
{# =========================================================================
   Link — Navigation
   Styled for nav context. Supports active state with aria-current.
   ========================================================================= #}

{%- extends '_atoms/links/_link--props' -%}

{%- block link -%}

    {%- if props.get('url') -%}

        {%- set classes = collect({
            layout: 'inline-flex items-center gap-1',
            color: props.get('active')
                ? 'text-brand-accent font-bold'
                : 'text-brand-heading',
            hover: 'hover:text-brand-accent',
            transition: 'transition-colors duration-150',
            utilities: props.get('utilities'),
        }) -%}

        {%- tag 'a' with {
            class: classes.implode(' '),
            href: props.get('url'),
            target: props.get('target') ?? false,
            rel: props.get('rel') ?? false,
            aria: {
                current: props.get('active') ? 'page' : false,
            },
        } -%}
            {{ props.get('text') }}

            {%- if props.get('external') -%}
                {{- tag('i', {
                    class: 'fa-solid fa-arrow-up-right-from-square text-xs ml-1',
                    aria: { hidden: 'true' },
                }) -}}
                {{- tag('span', { class: 'sr-only', text: '(opens in new tab)' }) -}}
            {%- endif -%}
        {%- endtag -%}

    {%- endif -%}

{%- endblock -%}
```

## Text Atom

Text atoms decouple visual treatment from semantic level. A `text--h2` renders
with `<h2>` visual styles, but the `tag` prop lets the caller override the
HTML element for semantic correctness.

```twig
{# =========================================================================
   Text — Props
   ========================================================================= #}

{%- set props = collect({
    content: content ?? '',
    tag: tag ?? null,
    utilities: utilities ?? null,
}) -%}

{%- block text -%}{%- endblock -%}
```

```twig
{# =========================================================================
   Text — H2
   Section heading. Tag prop overrides the HTML element.
   ========================================================================= #}

{%- extends '_atoms/texts/_text--props' -%}

{%- block text -%}
    {%- set element = props.get('tag') ?? 'h2' -%}

    {%- set classes = collect({
        font: 'font-heading font-bold',
        size: 'text-2xl lg:text-3xl',
        color: 'text-brand-heading',
        utilities: props.get('utilities'),
    }) -%}

    {%- tag element with { class: classes.implode(' ') } -%}
        {{ props.get('content') }}
    {%- endtag -%}
{%- endblock -%}
```

```twig
{# =========================================================================
   Text — Prose
   Rich text container. Wraps CKEditor output with Tailwind prose classes.
   ========================================================================= #}

{%- extends '_atoms/texts/_text--props' -%}

{%- block text -%}
    {%- set classes = collect({
        base: 'prose prose-brand max-w-none',
        utilities: props.get('utilities'),
    }) -%}

    <div class="{{ classes.implode(' ') }}">
        {{ props.get('content') | raw }}
    </div>
{%- endblock -%}
```

Usage — semantic override:

```twig
{# Visually an h2, semantically an h3 (page already has an h2 above) #}
{%- include '_atoms/texts/text--h2' with {
    content: entry.sectionTitle,
    tag: 'h3',
} only -%}
```

## Icon Atom

FontAwesome is the universal icon system. Icons are passed as FA class strings.
The atom handles the a11y distinction: decorative icons get `aria-hidden`,
meaningful icons get `role="img"` with a label.

```twig
{# _atoms/icons/icon--fa.twig #}
{%- extends '_atoms/icons/_icon--props' -%}

{%- block icon -%}
    {%- if props.get('label') -%}
        {{- tag('span', {
            class: [props.get('icon'), props.get('size'), props.get('utilities')],
            role: 'img',
            aria: { label: props.get('label') },
        }) -}}
    {%- else -%}
        {{- tag('i', {
            class: [props.get('icon'), props.get('size'), props.get('utilities')],
            aria: { hidden: 'true' },
            role: 'presentation',
        }) -}}
    {%- endif -%}
{%- endblock -%}
```
