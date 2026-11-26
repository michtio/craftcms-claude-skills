# Sections and Entry Types

Section settings, singles as the replacement for globals, structure navigation queries, and how Craft 5's global entry types behave, including their visual identity settings. The section-type decision table itself stays in SKILL.md; the core Craft documentation links for content modeling are listed first.

## Documentation

- Entries: https://craftcms.com/docs/5.x/reference/element-types/entries.html
- Sections: https://craftcms.com/docs/5.x/reference/element-types/entries.html#sections
- Fields: https://craftcms.com/docs/5.x/system/fields.html
- Field types: https://craftcms.com/docs/5.x/reference/field-types/
- Matrix: https://craftcms.com/docs/5.x/reference/field-types/matrix.html
- Relations: https://craftcms.com/docs/5.x/system/relations.html
- Eager loading: https://craftcms.com/docs/5.x/development/eager-loading.html
- Project config: https://craftcms.com/docs/5.x/system/project-config.html

## Section Properties

Beyond the type, sections have settings that matter for content architecture:

- **`maxAuthors`** (default 1) — allows multiple authors per entry (new in 5.0.0). Set higher for collaborative content.
- **`minAuthors`** [5.10+] (default 1) — minimum number of authors required to save an entry. Set `1` to enforce that every entry has at least one author. Validated on save; setting `minAuthors > maxAuthors` is rejected by Craft's section validator. Combine with `maxAuthors` to define an exact range (`min: 1, max: 3` = "1 to 3 authors required").
- **`enableVersioning`** (default true) — version history for entries
- **`defaultPlacement`** — `'beginning'` or `'end'` for new entries in structures
- **`previewTargets`** — array of `{label, urlFormat}` objects defining where entries can be previewed. Default: primary entry page. Add custom targets for headless frontends, staging URLs, or PDF previews.

## Singles Replace Globals

Set `preloadSingles => true` in `config/general.php` to access singles as global
Twig variables by handle — identical to the old globals behavior but with drafts,
revisions, live preview, and scheduling.

```twig
{# With preloadSingles enabled #}
{{ siteSettings.footerText }}
{{ siteSettings.socialLinks.all() }}
```

**Caveat:** Singles always propagate to all sites. This is hard-coded.

## Structure Queries for Navigation

```twig
{% set topLevel = craft.entries.section('pages').level(1).all() %}
{% set children = craft.entries.descendantOf(entry).descendantDist(1).all() %}
{% set breadcrumbs = craft.entries.ancestorOf(entry).all() %}
{% set siblings = craft.entries.siblingOf(entry).all() %}
```

## Entry Types in Craft 5

Entry types are defined globally (Settings → Entry Types), then attached to
sections and Matrix fields. One entry type can serve multiple contexts.

Key implications:
- Changing an entry type's field layout affects **every** section and Matrix field using it
- Fields come from the global pool — same field definition reused everywhere
- Per-context name/handle/description overrides available [5.6+] — useful when the same entry type serves different purposes in different sections
- The global pool demands careful field naming — use specific handles

## Entry Type Visual Identity (Craft 5 new)

Entry types have visual properties that improve the editorial experience:

- **`icon`** — custom icon identifier, shown in entry type selectors and Matrix "+" menus
- **`color`** — one of 20 options (red, orange, amber, yellow, lime, green, emerald, teal, cyan, sky, blue, indigo, violet, purple, fuchsia, pink, rose, white, gray, black)
- **`description`** [5.8+] — help text explaining what this entry type is for
- **`group`** [5.8+] — collapsible grouping in section/Matrix entry type assignments
- **`uiLabelFormat`** [5.9+] — customize the label shown in element indexes (default `'{title}'`)
- **`hasTitleField`** / **`titleFormat`** — disable the title field and auto-generate from other fields
- **`showSlugField`** (5.0.0) / **`showStatusField`** (4.5.0) — hide slug or status from editors
- **`allowLineBreaksInTitles`** [5.9+] — for long-form titles

These settings are configured in Settings → Entry Types and affect all contexts where the entry type is used. Editors navigate by icon, color, and description; investing in these settings makes the CP usable as the content model grows.
