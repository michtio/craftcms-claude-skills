# Atomic Patterns — Craft CMS Twig Implementation

> How atomic design principles are implemented in Craft CMS 5 Twig templates.
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
- Re-implementing atom HTML in a molecule — compose via includes, don't duplicate.
- Tracking props on components — decouple to data attributes at view level.
- Missing block name in props file — must match the component type.

## Table of Contents

- [Three-Tier Implementation](#three-tier-implementation)
- [The Props File](#the-props-file)
- [The Variant File (Extends/Block)](#the-variant-file)
- [Button Atom](#button-atom)
- [Link Atom](#link-atom)
- [Text Atom](#text-atom)
- [Icon Atom](#icon-atom)
- [Molecule Pattern](#molecule-pattern)
- [Organism Pattern](#organism-pattern)
- [Structural Embed Pattern](#structural-embed-pattern)
- [Calling Components](#calling-components)
- [Creating a New Component](#creating-a-new-component)

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

Buttons are action elements. The HTML tag resolves from props: `url` → `<a>`,
`type` → `<button>`, neither → `<span>`. This is the polymorphic element pattern.

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

## Molecule Pattern

Molecules compose atoms into a functional unit. Same props/extends/block
structure — the only difference is that molecules include child atoms.

```twig
{# =========================================================================
   Card — Blog
   Blog/news teaser. Composes image, heading, prose, and link atoms.
   ========================================================================= #}

{%- extends '_molecules/cards/_card--props' -%}

{%- block card -%}
    {%- set classes = collect({
        layout: 'flex flex-col overflow-hidden',
        color: 'bg-brand-surface',
        radius: 'rounded-lg',
        shadow: 'shadow-md hover:shadow-lg transition-shadow',
        utilities: props.get('utilities'),
    }) -%}

    {%- tag 'article' with { class: classes.implode(' ') } -%}

        {%- if props.get('image') -%}
            {%- include '_atoms/images/image--responsive' with {
                image: props.get('image'),
                preset: 'teaser',
            } only -%}
        {%- endif -%}

        <div class="p-4 flex flex-col gap-2">
            {%- if props.get('heading') -%}
                {%- include '_atoms/texts/text--h3' with {
                    content: props.get('heading'),
                } only -%}
            {%- endif -%}

            {%- if props.get('description') -%}
                {%- include '_atoms/texts/text--prose' with {
                    content: props.get('description'),
                    utilities: 'line-clamp-3',
                } only -%}
            {%- endif -%}

            {%- if props.get('url') -%}
                {%- include '_atoms/links/link--primary' with {
                    text: 'Read more',
                    url: props.get('url'),
                    icon: 'fa-solid fa-arrow-right',
                } only -%}
            {%- endif -%}
        </div>

    {%- endtag -%}
{%- endblock -%}
```

### Molecule Rules

- Include atoms with `{% include ... only %}` — never re-implement atom HTML.
- The `card` prop can be a Craft entry — extract fields via `props.get('card').title`.
- Keep molecule HTML focused: structural wrapper + child includes. No business logic.

## Organism Pattern

Organisms compose molecules and atoms into full page sections. They own the
semantic wrapper (`<section>`, `<nav>`, `<footer>`), the container, and the grid.
Children own their internal layout.

```twig
{# =========================================================================
   Hero — Primary
   Full-width hero with image, heading, standfirst, and CTA.
   ========================================================================= #}

{%- extends '_organisms/heroes/_hero--props' -%}

{%- block hero -%}

    {%- set classes = collect({
        layout: 'relative overflow-hidden',
        spacing: 'py-16 lg:py-24',
        color: 'bg-brand-primary text-brand-on-primary',
        utilities: props.get('utilities'),
    }) -%}

    <section{{ attr({ class: classes.implode(' ') }) }}>
        <div class="container mx-auto px-4 grid lg:grid-cols-2 gap-8 items-center">

            <div class="flex flex-col gap-6">
                {%- if props.get('heading') -%}
                    {%- include '_atoms/texts/text--h1' with {
                        content: props.get('heading'),
                        utilities: 'text-brand-on-primary',
                    } only -%}
                {%- endif -%}

                {%- if props.get('standfirst') -%}
                    {%- include '_atoms/texts/text--prose' with {
                        content: props.get('standfirst'),
                        utilities: 'text-lg text-brand-on-primary/80',
                    } only -%}
                {%- endif -%}

                {%- if props.get('button') -%}
                    {%- include '_atoms/buttons/button--primary' with {
                        text: props.get('button').text ?? props.get('button').title ?? '',
                        url: props.get('button').url ?? '',
                        icon: 'fa-solid fa-arrow-right',
                    } only -%}
                {%- endif -%}
            </div>

            {%- if props.get('image') -%}
                {%- include '_atoms/images/image--responsive' with {
                    image: props.get('image'),
                    preset: 'hero',
                } only -%}
            {%- endif -%}

        </div>
    </section>

{%- endblock -%}
```

### Organism Rules

- Wrap in a semantic element: `<section>`, `<nav>`, `<footer>`, `<header>`.
- The organism owns the container and grid. Children own their internals.
- Use `attr()` for the section tag when the element name is static.
- The `button` prop often comes from a Hyper link field — access via
  `.collect.first` when extracting.

## Structural Embed Pattern

`{% embed %}` combines `{% include %}` and `{% extends %}` into one call. It
includes a template AND lets you override its blocks inline — at the call
site — without creating a separate file.

### The Problem It Solves

The standard pattern has two modes:

- `{% include ... only %}` — passes data through props. The component owns its
  rendering entirely. The caller has no way to inject content into specific
  structural slots.
- `{% extends %}` — creates a variant file that overrides blocks. Reusable,
  but requires a separate file for every arrangement.

There's a gap: what about structural skeletons where the wrapper is always the
same (grid, spacing, responsive breakpoints) but the content inside varies at
every call site? Creating a separate variant file for every unique content
arrangement defeats the purpose. Duplicating the structural wrapper everywhere
defeats DRY.

`{% embed %}` fills this gap. Twig's docs call it a "micro layout skeleton" —
a reusable structural shell with named content slots that you fill where you
use it.

### When to Use Embed

- **View-level layout skeletons** — a page structure with main content and an
  aside, where different views fill those regions with different organisms.
- **Organisms with content slots** — a section wrapper that defines the grid
  and spacing, but the actual content composition varies per usage.
- **One-off structural arrangements** — when the combination of components is
  unique to one page and doesn't warrant a reusable organism variant.

### When NOT to Use Embed

- **Atoms and molecules.** These are props-driven. The caller passes data, the
  component owns rendering. Embed would break that contract by letting callers
  inject arbitrary HTML into component internals.
- **Repeatable visual variants.** If the same content arrangement appears in
  multiple places, create a proper organism variant file with extends/block.
  Embed is for unique arrangements.
- **As a replacement for props.** If the content can be expressed as data (a
  string, an asset, a URL), pass it as a prop. Embed is for when the content
  is itself a composition of components — not data but structure.

### The Skeleton Template

A structural skeleton defines the wrapper HTML and named blocks for content:

```twig
{# _organisms/layouts/split--media.twig #}
{# =========================================================================
   Split — Media
   Two-column layout skeleton. Media on one side, content on the other.
   Use with {% embed %} to fill the slots.
   ========================================================================= #}

{%- set props = collect({
    reverse: reverse ?? false,
    spacing: spacing ?? 'py-16 lg:py-24',
    utilities: utilities ?? null,
}) -%}

{%- set classes = collect({
    layout: 'relative',
    spacing: props.get('spacing'),
    utilities: props.get('utilities'),
}) -%}

<section class="{{ classes.implode(' ') }}">
    <div class="container mx-auto px-4 grid lg:grid-cols-2 gap-8 items-center">
        <div class="{{ props.get('reverse') ? 'lg:order-2' : '' }}">
            {%- block media -%}{%- endblock -%}
        </div>
        <div class="{{ props.get('reverse') ? 'lg:order-1' : '' }}">
            {%- block content -%}{%- endblock -%}
        </div>
    </div>
</section>
```

The skeleton owns the structural concerns: the section wrapper, the container,
the grid, the responsive behavior, the ordering. The blocks are empty slots
for the caller to fill.

### Embedding From a View

```twig
{# _views/view--job-detail.twig #}

{# Hero #}
{%- if hero -%}
    {%- include '_organisms/heroes/hero--primary' with {
        heading: entry.title,
        image: hero,
    } only -%}
{%- endif -%}

{# Job detail — main content + aside #}
{%- embed '_organisms/layouts/split--media' with {
    reverse: true,
    spacing: 'py-12 lg:py-16',
} only -%}

    {%- block content -%}
        {%- if entry.description -%}
            {%- include '_atoms/texts/text--prose' with {
                content: entry.description,
            } only -%}
        {%- endif -%}

        {%- if entry.contentBuilder.exists() -%}
            {%- include '_organisms/builders/builder--blocks' with {
                blocks: entry.contentBuilder.eagerly().all(),
            } only -%}
        {%- endif -%}
    {%- endblock -%}

    {%- block media -%}
        {%- include '_molecules/cards/card--job-sidebar' with {
            location: entry.location ?? null,
            salary: entry.salary ?? null,
            contract: entry.contractType ?? null,
            button: entry.applyUrl ?? null,
        } only -%}
    {%- endblock -%}

{%- endembed -%}

{# Related jobs #}
{%- if entry.relatedJobs.exists() -%}
    {%- include '_organisms/grids/grid--jobs' with {
        entries: entry.relatedJobs.eagerly().all(),
    } only -%}
{%- endif -%}
```

### Embed Rules

- Always use `only` — same isolation principle as `{% include %}`.
- Embed supports `with {}` for passing props to the skeleton alongside
  block overrides. The skeleton reads props normally; the caller fills blocks.
- Blocks inside `{% embed %}` have access to the calling template's scope
  (unless `only` excludes it). This means you can reference `entry`, `hero`,
  etc. inside the blocks — they're not isolated the way a separate variant
  file would be.
- Name skeleton blocks descriptively: `content`, `media`, `sidebar`, `header`,
  `footer` — not `left`, `right`, `top`, `bottom` (those are layout positions
  that might change with `reverse`).
- Skeleton templates live in `_organisms/layouts/` — they're structural
  organisms, not a separate tier.

### Embed vs Include vs Extends

| Technique | Use case | Creates new file? |
|-----------|----------|-------------------|
| `{% include ... only %}` | Render a component with props. Caller passes data, component owns rendering. | No |
| `{% extends %}` | Create a visual variant. Override blocks in a new file. Reusable across many call sites. | Yes |
| `{% embed ... only %}` | Fill structural slots inline. Same skeleton, different content at each call site. | No |

The decision: if the content in the slots is **data** → use include with props.
If the content is **a composition of components** that varies per call site →
use embed. If the same composition repeats across multiple call sites → extract
it into an organism variant with extends.

## Calling Components

```twig
{# Atom from anywhere #}
{%- include '_atoms/buttons/button--primary' with {
    text: 'Read more',
    url: entry.url,
    icon: 'fa-solid fa-arrow-right',
} only -%}

{# Atom from a molecule/organism — pass through props #}
{%- include '_atoms/texts/text--h2' with {
    content: props.get('heading'),
    utilities: 'mb-4',
} only -%}

{# Molecule from an organism #}
{%- include '_molecules/cards/card--blog' with {
    card: entry,
    image: entry.heroImage.eagerly().one(),
} only -%}
```

Always `only`. Props explicit. No macros. See `craft-twig-guidelines` for the
full include isolation rules.

## Creating a New Component

Follow the decompose-downward workflow from `atomic-design.md` — start from the
design, not from the classification.

1. **Look at the design.** What page section are you building? That's your
   candidate organism.
2. **Identify repeated units** inside that section. Each distinct visual unit
   that could appear in multiple contexts is a candidate molecule.
3. **Within each unit, spot the base elements.** Buttons, headings, images, icons
   — these are atoms. Check if they already exist before creating new ones.
4. **Classify** using the decision tree in `component-inventory.md`.
5. **Name by visual treatment**, not by content or context.
6. **Create the props file** — `_tier/category/_component--props.twig`
   with `collect({})`, `??` defaults, derived values, and a named block.
7. **Create the variant file** — `_tier/category/component--variant.twig`
   extending the props base, with named-key class collection and rendering.
8. **Add comment headers** to both files.
9. **Test isolation** — include the component from two different contexts and
   verify identical rendering with the same props.