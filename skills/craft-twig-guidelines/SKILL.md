---
name: craft-twig-guidelines
description: "Twig coding standards and conventions for Craft CMS 5 templates. ALWAYS load this skill when writing, editing, or reviewing any .twig file in a Craft CMS project, even for small edits. Covers: variable naming (camelCase, no abbreviations), null handling (?? operator, ??? with empty-coalesce plugin), whitespace control ({%- trimming, NOT {%- minify -%}), include isolation (always 'only'), Craft Twig helpers ({% tag %}, tag(), attr(), |attr, |parseAttr, |append, svg()), collect() for props and class collections, .implode(), ========= comment headers on component files, and pitfalls (snake_case, macros as components, hardcoded colors)."
when_to_use: "Triggers on: .twig files; {% include %} with 'only'; polymorphic elements; props.get(); class string building; svg() with styling and aria; null coalescing; blank lines in output; minify alternatives; Twig file headers and comment blocks; currentSite, siteUrl, craft.entries, .eagerly(), .collect in template context; |e('js') aggressive escaping (spaces become \\uXXXX), js escaper, grepping escaped translated strings. NOT for Twig architecture patterns, atomic design structure, or template routing (use craft-site). NOT for PHP code (use craft-php-guidelines). NOT for content modeling or field configuration (use craft-content-modeling)."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Twig Coding Standards — Craft CMS 5

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Coding conventions for Twig templates in Craft CMS 5 projects. These apply to
all Twig code — atomic components, views, layouts, builders, partials.

## Companion Skills — Always Load Together

- **`craft-site`** — Template architecture and component patterns (atomic design, routing, builders). Required when creating or editing components, layouts, views, or builders.
- **`craft-content-modeling`** — Content architecture. Required when template code involves element queries, field access, or section decisions.

For PHP coding standards, see `craft-php-guidelines`.

## Documentation

- Twig in Craft: https://craftcms.com/docs/5.x/development/twig.html
- Template tags: https://craftcms.com/docs/5.x/reference/twig/tags.html
- Template functions: https://craftcms.com/docs/5.x/reference/twig/functions.html
- Twig 3 docs: https://twig.symfony.com/doc/3.x/

Use `WebFetch` on specific doc pages when something isn't covered here.

## Reference Files

| Task | Read | ~Tokens |
|------|------|---------|
| Correct/wrong examples for naming, `??`/`???`/`?.`, whitespace, `only` on include/render/`include_only()`, macros, comment headers, `collect()` classes, copy style; long form of the pitfalls | `references/core-conventions.md` | ~2,450 |
| `{% tag %}`, `tag()`, `attr()`, `\|attr`, `\|parseAttr`, `\|append`, `svg()`, `url(…, false)`, `heading()`/`h()` [5.10+], filter additions [5.10+], `collect()` vs array filters, `\|t`/`\|purify`/`\|raw`, `{% js %}`/`{% css %}`, `\|e('js')` escaping | `references/craft-helpers.md` | ~1,950 |
| Upgrading to 5.12 [changed 5.12]: case filters follow the site language, Twig 3.29 to 3.31 deprecations (`spaceless`, macro calls, `matches`) | `references/craft-5-12-changes.md` | ~800 |

## Rules

- **Naming**: camelCase, single word when context allows (`heading`, `buttonText`). Never snake_case, never abbreviations: `element` not `el`, `button` not `btn`, `navigation` not `nav`, `description` not `desc`.
- **Nulls**: `??` is the default. `???` only when `nystudio107/craft-emptycoalesce` or `nystudio107/craft-seomatic` is already installed (check `composer.json`; never install one just for `???`). `?.` for chains whose intermediate links may be null (`entry?.author?.fullName ?? 'Anonymous'`), not for a single property. Never `is defined and is not null`.
- **Whitespace**: `{%-` / `{{-` / `-%}` where output whitespace matters. Never `{%- minify -%}`.
- **Every `{% include %}` uses `only`.** No exceptions: without it the component silently depends on parent variables. The same goes for `{% render %}` [5.12+]:

  ```twig
  {# Correct #}
  {%- render entry.contentBlocks with { theme: 'dark' } only -%}
  ```

  [5.12+] Before 5.12 the tag fails the whole template at compile time: use `{{ entry.contentBlocks.render({ theme: 'dark' }) }}`. Inside the partial, `entry` is the rendered element, not the page entry. `include_only()` [5.12+] is the function form; [5.12+] before 5.12: `include(…, with_context = false)`. Partial lookup: `craft-site` (`references/element-partials.md`).
- **No `{% macro %}` for UI components** (no extends/block, different scoping). Macros only for string-returning helpers.
- **Every component file gets a header** (props, variants, views, layouts too), with the same `=========` separator as the PHP convention:

  ```twig
  {# =========================================================================
     Component Name
     Brief description of what this component does.
     ========================================================================= #}
  ```
- **Polymorphic elements** use `{% tag element with {…} %}` with a descriptive variable (`element`, `wrapper`); `false` omits an attribute. `tag()`, `attr()`, `|attr`, `svg()`: `references/craft-helpers.md`.
- **Class strings**: `collect({})` with camelCase named keys, one key per style concern, joined with `.implode(' ')`. Never `'flex ' ~ extraClass`. Full patterns: `craft-site` (`references/twig-collections.md`, `references/tailwind-conventions.md`).
- **Data manipulation**: default to `collect()` chains; a bare `|filter`/`|map` only for one trivial inline step. There is no `|indexBy` (use `|index` or `.keyBy()`).
- **Output**: every user-facing string through `|t('category')`; `|purify` for untrusted HTML, `|raw` only for trusted field output; `{% js %}`/`{% css %}` instead of hand-written `<script>`/`<style>`; never ship `{% dd %}`/`dump()`.
- **Copy style**: no em-dashes (—) or en-dashes (–) in template text or `|t` strings; use commas, colons, parentheses, or a plain hyphen, and write ranges as "4 to 10". Twig comments are exempt. Grep for `—` and `–` before finishing.

## Common Pitfalls

1. **`???` operator without the plugin** — requires `nystudio107/craft-emptycoalesce` or `nystudio107/craft-seomatic`. Check `composer.json` before using. Default to `??`.
2. **snake_case variables** — use camelCase: `heroImage` not `hero_image`.
3. **Missing `only`** — silent variable leaking, invisible coupling.
4. **`{%- minify -%}`** — deprecated. Use `{%-` whitespace control.
5. **Abbreviations** — `el`, `btn`, `nav`, `desc`, `ctr` → spell it out.
6. **`is not defined`** — verbose null checking. `??` handles it.
7. **Macros as components** — wrong scoping, no extends/block support.
8. **Hardcoded colors in class strings** — `bg-yellow-600` → `bg-brand-accent`.
9. **String concatenation for classes** — `'flex ' ~ extraClass` → use `collect({})` with named keys.
10. **`is empty` / `|default` on Craft Models** [changed 5.10]: from 5.10 every `yii\base\Model` counts as non-empty, so `{{ user|default('Guest') }}` renders the user. Test the property: `{% if entry.title is empty %}`.
11. **`options.x` pattern** — old macro convention. Use direct variable names.
12. **Blocks inside conditionals**: invalid Twig. Put the `{% if %}` inside the `{% block %}`.
13. **Hardcoded `/admin` CP URL**: `cpTrigger` is configurable. Use `cpUrl()`.
14. **Em/en-dashes in user-facing copy**: see Copy style above.
15. **Twig has no `instanceof`**: branch on `object.hasProperty()`/`hasMethod()` or have PHP pass a discriminator.
16. **Per-request output inside `{% cache %}`** (CSP nonce, `csrfInput()`, active classes, language-switcher URLs) is frozen at the first render. See the `craft-site` skill's `template-caching.md`.
17. **Grepping output for a `|e('js')`-escaped phrase**: every space becomes a `\uXXXX` sequence, so grep or assert on a single token. See `references/craft-helpers.md`.
18. **`{% render %}` on a site below 5.12** [5.12+]: unknown tag, the whole template fails to compile. Use `.render()` where the template must also run on older releases.
19. **Appending alpha to a colour** [changed 5.12]: `{{ entry.brand }}80` or `entry.brand.hex ~ '1a'` breaks once a Color field returns an 8-digit hex (translucent palette colours, or custom colours with opacity allowed). Use `rgb({{ entry.brand.rgbChannels }} / 50%)` [5.12+] or `entry.brand.rgba` [5.12+]; `entry.brand.getHex(false) ~ '80'` works on every version. Before 5.12: hex was always 6-digit.
20. **Macros called without parentheses** [5.12+]: `{{ macros.label }}` is deprecated in Twig 3.29 and a syntax error in Twig 4. Write `{{ macros.label() }}`.
21. **`|upper`/`|lower` on identifiers** [changed 5.12]: casing follows the site language, so a Turkish site lowercases `I` to `ı`. Pass `('en')` for codes and handles. See `references/craft-5-12-changes.md`.
22. **`heading()` / `h()` on an older site**: `heading()` and `h()` need [5.10+]. Before 5.10: build the tag from the level yourself. `{{ tag('h' ~ level, { text: title }) }}` (`tag()` takes an attributes array; `text` is encoded, `html` is not) or `{% tag 'h' ~ level with { class: 'text-xl' } %}Subsection{% endtag %}`. Don't ship `heading()` / `h()` to a site below 5.10.
23. **`url()` with `false`** [5.11+] strips every query param from an absolute URL. Before 5.11: `siteUrl(craft.app.request.pathInfo)`.
