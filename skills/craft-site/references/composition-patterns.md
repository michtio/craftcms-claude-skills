# Composition Patterns — Craft CMS Twig Implementation

> How to compose atoms into molecules, organisms, and structural layouts.
> This covers the "putting things together" side of the component system.
> For individual atom patterns (button, link, text, icon) and the foundational
> props/extends/block mechanics, see `atomic-patterns.md`.
> For Twig coding standards (`{% tag %}`, `attr()`, naming, null handling), see `craft-twig-guidelines`.

## Documentation

- Twig `{% include %}`: https://twig.symfony.com/doc/3.x/tags/include.html
- Twig `{% extends %}`: https://twig.symfony.com/doc/3.x/tags/extends.html
- Twig `{% embed %}`: https://twig.symfony.com/doc/3.x/tags/embed.html
- Twig `{% tag %}`: https://craftcms.com/docs/5.x/reference/twig/tags.html#tag
- Twig `attr()`: https://craftcms.com/docs/5.x/reference/twig/functions.html#attr

## Common Pitfalls

- Re-implementing atom HTML in a molecule — compose via includes, don't duplicate.
- Missing `only` on `{% include %}` inside molecules/organisms — ambient variables leak in silently.
- Queries inside organisms — organisms receive data, they don't fetch it.
- Using `{% embed %}` for atoms/molecules — embed is for structural skeletons, not props-driven components.
- Using `{% if variant == 'x' %}` to switch composition — use extends/block instead.
- Creating a separate variant file for a one-off content arrangement — use embed instead.
- Naming skeleton blocks by position (`left`, `right`) — name by purpose (`content`, `media`).

## Table of Contents

- [Molecule Pattern](#molecule-pattern)
- [Organism Pattern](#organism-pattern)
- [Structural Embed Pattern](#structural-embed-pattern)
- [Calling Components](#calling-components)
- [Creating a New Component](#creating-a-new-component)

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

The decision: if the content in the slots is **data** -> use include with props.
If the content is **a composition of components** that varies per call site ->
use embed. If the same composition repeats across multiple call sites -> extract
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
