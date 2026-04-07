# Boilerplate, Routing & Builders Reference

> The full template chain from HTML document to rendered page.

## Documentation

- Craft routing: https://craftcms.com/docs/5.x/system/routing.html
- Twig templates in Craft: https://craftcms.com/docs/5.x/development/twig.html
- Entry queries: https://craftcms.com/docs/5.x/reference/element-types/entries.html
- Eager loading: https://craftcms.com/docs/5.x/development/eager-loading.html

## Common Pitfalls

- Fat section templates — if your section template has more than an extends and a single include, it's doing too much. Push logic into views.
- Queries in views — views receive data, they don't fetch it. Element queries belong in section templates or routers.
- Layouts with business logic — a layout that checks `entry.someField` is coupling chrome to content. Use blocks to let views control layout slots.
- Missing fallback for entry types — always have a `view--default.twig` for when new entry types are added but templates haven't been created yet.
- Builder without devMode warning — unknown block types should be visible in development. Silent failure means content editors add blocks that never render.
- Missing `.eagerly()` on relation fields — causes N+1 queries in views and builders.
- Passing raw block objects to components — extract props explicitly from the block, never pass the block itself.

## Table of Contents

- [How Craft Connects to the Template Chain](#how-craft-connects-to-the-template-chain)
- [Layout Chain](#layout-chain)
- [Partials](#partials)
- [Routers](#routers)
- [Views](#views)
- [Builders](#builders)
- [Template Directory Structure](#template-directory-structure)

## How Craft Connects to the Template Chain

Craft's routing determines which template file is loaded for a given URL. For
entries, this is configured in the section settings:

**Settings → Sections → [Section] → Site Settings → Template**

The template path (e.g., `_routers/router--page`) points to the file Craft
renders when an entry in that section is requested. Craft provides the `entry`
variable automatically — this is the resolved entry element for the URL.

For a typical setup: every section's template path points to the same router
file. The router then dispatches to the correct view based on the entry's
section and type. This means one router handles all entry types, and adding
a new entry type only requires adding a new view file — not touching Craft's
section settings.

Category pages work similarly — the category group's template path points to
the router, and Craft provides the `category` variable.

## Layout Chain

Every page flows through this chain. Each layer adds one concern.

```
global-variables.twig              → Data: global sets, prefetch, brand context
  └── base-web-layout.twig         → Document: <!DOCTYPE>, <html data-brand>, <head>, <body>
        └── base-html-layout.twig  → Assets: meta, fonts, critical CSS, JS entry points
              └── generic-page-layout.twig  → Chrome: nav, <main>, footer, skip links
                    └── router--page.twig   → Dispatch: entry type → view
                          └── view--*.twig  → Composition: hero + builder + sections
```

### global-variables.twig

Sets up data available to every page. No HTML output.

```twig
{# _boilerplate/_layouts/global-variables.twig #}

{# Global sets — eagerly loaded once #}
{%- set settings = craft.globalSets()
    .handle('siteSettings')
    .site(currentSite)
    .eagerly()
    .collect
    .first
-%}

{%- set navigation = craft.globalSets()
    .handle('navigation')
    .site(currentSite)
    .eagerly()
    .collect
    .first
-%}

{# Brand context #}
{%- set brand = currentSite.handle -%}

{# Prefetch URLs #}
{%- set prefetch = [
    'https://fonts.googleapis.com',
    'https://kit.fontawesome.com',
] -%}

{%- block layout -%}{%- endblock -%}
```

### base-web-layout.twig

The HTML document. Sets `data-brand` for CSS token resolution.

```twig
{# _boilerplate/_layouts/base-web-layout.twig #}
{%- extends '_boilerplate/_layouts/global-variables' -%}

{%- block layout -%}
<!DOCTYPE html>
<html lang="{{ craft.app.language|slice(0,2) }}" data-brand="{{ brand }}">
<head>
    {%- block head -%}
        {%- include '_boilerplate/_partials/head-meta' only -%}
        {%- block headLinks -%}{%- endblock -%}
        {%- block headJs -%}
            {%- include '_boilerplate/_partials/head-js' only -%}
        {%- endblock -%}
    {%- endblock -%}
</head>
<body class="antialiased">
    {%- block body -%}{%- endblock -%}
    {%- block bodyJs -%}
        {%- include '_boilerplate/_partials/body-js' only -%}
    {%- endblock -%}
</body>
</html>
{%- endblock -%}
```

### base-html-layout.twig

Adds asset loading via the nystudio107 Vite plugin. `craft.vite.script()`
outputs both `<script>` and `<link>` tags — CSS and JS in one call. Since
`<script type="module">` is inherently deferred, it belongs in `<head>`.
See `vite-buildchain.md` for the full Vite setup.

```twig
{# _boilerplate/_layouts/base-html-layout.twig #}
{%- extends '_boilerplate/_layouts/base-web-layout' -%}

{%- block headLinks -%}
    {{ parent() }}
    {%- block criticalCss -%}{%- endblock -%}
    {{ craft.vite.script('src/js/app.ts', false) }}
{%- endblock -%}

{%- block body -%}
    {%- block page -%}{%- endblock -%}
{%- endblock -%}

{%- block bodyJs -%}
    {{ parent() }}
    {%- block pageJs -%}{%- endblock -%}
{%- endblock -%}
```

### generic-page-layout.twig

Adds site chrome: navigation, main content area, footer, skip links.

```twig
{# _boilerplate/_layouts/generic-page-layout.twig #}
{%- extends '_boilerplate/_layouts/base-html-layout' -%}

{%- block page -%}

    {# Skip to main content — a11y #}
    {{- tag('a', {
        class: 'sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-brand-accent focus:text-brand-on-accent',
        href: '#main-content',
        text: 'Skip to main content',
    }) -}}

    {# Site navigation #}
    {%- include '_organisms/navigations/navigation--site' with {
        navigation: navigation,
    } only -%}

    {# Main content #}
    <main id="main-content">
        {%- block content -%}{%- endblock -%}
    </main>

    {# Footer #}
    {%- include '_organisms/footers/footer--primary' with {
        navigation: navigation,
        settings: settings,
    } only -%}

{%- endblock -%}
```

### error-page-layout.twig

Simplified layout for error pages. No navigation complexity.

```twig
{# _boilerplate/_layouts/error-page-layout.twig #}
{%- extends '_boilerplate/_layouts/base-html-layout' -%}

{%- block page -%}
    <main id="main-content" class="flex items-center justify-center min-h-screen">
        {%- block content -%}{%- endblock -%}
    </main>
{%- endblock -%}
```

## Partials

### head-meta.twig

```twig
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{%- for url in prefetch ?? [] -%}
    {{ tag('link', { rel: 'dns-prefetch', href: url }) }}
{%- endfor -%}
```

### head-js.twig

Consent management, GTM, FontAwesome kit. Project-specific — no canonical template.

### body-js.twig

Deferred scripts. Lazy load shims if needed. Project-specific.

### tab-handler.twig

Keyboard navigation detection. Adds `.user-is-tabbing` class to body.

```twig
<script>
document.body.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') document.body.classList.add('user-is-tabbing');
});
document.body.addEventListener('mousedown', () => {
    document.body.classList.remove('user-is-tabbing');
});
</script>
```

## Routers

Routers dispatch entry types to views. One router per site (usually `router--page.twig`).

### Pattern

```twig
{# _routers/router--page.twig #}
{%- extends '_boilerplate/_layouts/generic-page-layout' -%}

{%- block content -%}

    {# Resolve shared data once — avoids duplicate queries in views #}
    {%- set hero = entry.heroImage.eagerly().one() ?? null -%}

    {# Dispatch by section + entry type #}
    {%- switch entry.section.handle ~ ':' ~ entry.type.handle -%}

        {%- case 'pages:landing' -%}
            {%- include '_views/view--page-landing' with {
                entry: entry, hero: hero,
            } only -%}

        {%- case 'pages:content' -%}
            {%- include '_views/view--page-content' with {
                entry: entry, hero: hero,
            } only -%}

        {# Add cases per section:entryType combination #}

        {%- default -%}
            {%- include '_views/view--page-content' with {
                entry: entry, hero: hero,
            } only -%}

    {%- endswitch -%}

{%- endblock -%}
```

### Router Methodology

- **Switch on `section.handle ~ ':' ~ type.handle`** for precision. A `content` entry type in the `pages` section needs different treatment than a `content` type in a `help` section.
- **Always have a `default` case** pointing to the most generic view.
- **Always pass `only`** to view includes.
- **Resolve shared data once** in the router (hero image, related entries), not in each view. Avoids duplicate queries.
- **Keep routers thin.** No business logic, no HTML. Just dispatch.
- **Category pages** get their own switch block:

```twig
{%- if category is defined and category -%}
    {%- switch category.group.handle -%}
        {%- case 'topics' -%}
            {%- include '_views/view--category-topic' with {
                category: category,
            } only -%}
        {%- default -%}
            {%- include '_views/view--category-default' with {
                category: category,
            } only -%}
    {%- endswitch -%}
{%- else -%}
    {# Entry dispatch #}
{%- endif -%}
```

## Views

Views compose organisms into a full page. Named `view--{type}-{context}.twig`.

### Pattern

```twig
{# _views/view--page-landing.twig #}

{# Hero #}
{%- if hero -%}
    {%- include '_organisms/heroes/hero--primary' with {
        heading: entry.title,
        standfirst: entry.standfirst ?? null,
        image: hero,
        button: entry.heroButton.collect.first ?? null,
    } only -%}
{%- endif -%}

{# Content builder #}
{%- if entry.contentBuilder.exists() -%}
    {%- include '_organisms/builders/builder--blocks' with {
        blocks: entry.contentBuilder.eagerly().all(),
    } only -%}
{%- endif -%}

{# Related entries #}
{%- if entry.relatedEntries.exists() -%}
    {%- include '_organisms/grids/grid--blog' with {
        entries: entry.relatedEntries.eagerly().all(),
    } only -%}
{%- endif -%}
```

### View Methodology

- Views have **no layout wrapping**. The router provides layout context.
- Views are **pure composition** — organism includes in order.
- Views can use `{% embed %}` for structural skeletons when a page needs
  content slots (e.g., main + aside). See `atomic-patterns.md` embed pattern.
- Use `.eagerly()` on all relation field queries.
- Use `.exists()` to check before including optional sections.
- Pass `only` on every include.
- **Tracking data attributes go at view level**, not inside components:

```twig
<div data-tracking="{{ {
    page: entry.title,
    type: entry.type.handle,
    section: entry.section.handle,
}|json_encode }}">
    {# ... organisms ... #}
</div>
```

## Builders

Builders render Matrix/entry blocks. They contain the switch statement mapping
block types to components.

### Pattern

```twig
{# _organisms/builders/builder--blocks.twig #}
{%- extends '_organisms/builders/_builder--props' -%}

{%- block builder -%}
    {%- for block in props.get('blocks') -%}
        {%- switch block.type.handle -%}

            {%- case 'richText' -%}
                {%- include '_molecules/contents/content--prose' with {
                    heading: block.heading ?? null,
                    content: block.body ?? null,
                } only -%}

            {%- case 'callout' -%}
                {%- include '_organisms/callouts/callout--primary' with {
                    heading: block.heading ?? null,
                    content: block.description ?? null,
                    button: block.target.collect.first ?? null,
                    image: block.image.eagerly().one() ?? null,
                } only -%}

            {%- case 'imageGallery' -%}
                {%- include '_organisms/sliders/slider--images' with {
                    images: block.images.eagerly().all(),
                } only -%}

            {# Add cases per block type #}

            {%- default -%}
                {%- if devMode -%}
                    <div class="p-4 bg-red-100 text-red-800 rounded">
                        Unknown block type: <code>{{ block.type.handle }}</code>
                    </div>
                {%- endif -%}

        {%- endswitch -%}
    {%- endfor -%}
{%- endblock -%}
```

### Builder Methodology

- Every block include uses `only`.
- **Extract props explicitly** — never pass the raw block object to a component.
- Use `.eagerly()` on nested relation fields within blocks.
- Use `.collect.first` for single-value Hyper link fields.
- Keep builder logic to **data extraction only**. No calculations, no theme logic.
- **Always include a `default` case** with a `devMode` warning for unknown block types.
- The switch statement is fine in vanilla Twig. The DS module replaces it with block transformers (see `craft-ds-vision.md`).
- If a builder exceeds ~25 cases, split into specialized builders per section.

## Template Directory Structure

```
cms/templates/
├── _atoms/                    ← Tier 1: singular UI elements
│   ├── buttons/               ← Plural category directories
│   ├── links/
│   ├── texts/
│   ├── images/
│   └── ...                    ← Add categories as needed
├── _molecules/                ← Tier 2: atom compositions
│   ├── cards/
│   ├── contents/
│   └── ...
├── _organisms/                ← Tier 3: page sections
│   ├── heroes/
│   ├── builders/
│   ├── layouts/               ← Embed skeletons
│   └── ...
├── _boilerplate/
│   ├── _layouts/              ← Document/page chrome chain
│   └── _partials/             ← Shared non-component partials
├── _routers/                  ← Entry type → view dispatch
├── _views/                    ← Page compositions
├── _email/                    ← Email templates
├── _errors/                   ← Error page templates
└── _formie/                   ← Formie template overrides
```

Categories grow per project — the standard scaffolds are listed in
`component-inventory.md`. Add new category directories freely as long as
they follow the plural naming convention.

### Naming Rules

- `_` prefix on directories = not directly routable by Craft. Internal only.
- Category directories use plural names: `buttons/`, `cards/`, `heroes/`.
- Props files: `_component--props.twig` (underscore prefix).
- Variants: `component--variant.twig` (no underscore).
- Routers: `router--{context}.twig`.
- Views: `view--{type}-{context}.twig`.
