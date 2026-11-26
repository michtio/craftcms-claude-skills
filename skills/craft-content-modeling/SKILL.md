---
name: craft-content-modeling
description: "Craft CMS 5 content modeling — sections, entry types, fields, Matrix, relations, project config, and content architecture strategy. Covers choosing section types, designing entry types and field layouts, selecting field types, configuring Matrix and nested entries, relations and eager loading, and multi-site propagation."
when_to_use: "Triggers on: section types (single, channel, structure), entry types, field types, field layout design, field type selection, Matrix, nested entries, relatedTo, eager loading, .with()/.eagerly(), categories, tags, globals, global sets, preloadSingles, propagation, multi-site content, project config, YAML, project-config/write/diff/apply/touch, YAML vs DB drift, restored prod DB dump, content strategy, taxonomy, asset volumes, filesystems, image transforms, user groups, content permissions, entrify/entrification, CKEditor vs Matrix, CMS editions, multi-language/localization, field translation methods, content migration, field instances, Formie forms vs project config, cross-env/multi-site Formie, elementSources/Entries index sidebar, tableAttributes, defaultSort, authoring schema from code (service layer vs YAML). Always use when planning content architecture, creating sections/fields, configuring Matrix, setting up relations, choosing field types, designing field layouts, planning multi-site propagation, tidying the Entries element index, or running project-config commands. Do NOT trigger for PHP plugin/module development, custom field type code, front-end Twig, or buildchain."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft CMS 5 — Content Modeling

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

How to structure content in Craft CMS 5: sections, entry types, fields, Matrix, relations, asset management, and strategic patterns for real projects. This skill covers **content architecture** (what goes in the CP, how it's organized, and how templates access it). For extending Craft with PHP (plugins, modules, custom element types), see the `craftcms` skill.

## Companion Skills — Always Load Together

When this skill triggers, also load:

- **`craft-site`** — Template architecture, component patterns, routing. Required when content decisions affect how templates render data.
- **`craft-twig-guidelines`** — Twig coding standards. Required when writing any Twig examples or template code alongside content modeling.
- **`ddev`** — All commands run through DDEV. Required for running project config commands, Craft CLI, and content migrations.

Craft docs links (entries, sections, fields, field types, Matrix, relations, eager loading, project config): `references/sections-and-entry-types.md` (Documentation). Use `WebFetch` on specific doc pages when a reference file doesn't cover enough detail.

## The Craft 5 Mental Model

**Everything is becoming an entry.** Entry types are global (shared across sections and Matrix fields) and fields come from a global pool. Categories, tags, and global sets are deprecated in Craft 5 (still creatable in the CP) and removed in Craft 6. For **new projects**, always use entries: Structure sections for hierarchical taxonomy, Channel sections for flat taxonomy, Singles for site-wide settings. Timeline and `entrify` commands: `references/content-patterns.md` (Entries-as-Taxonomy).

Three decisions define your content architecture: the **section type** (Single, Channel, Structure), the **entry types** that define its shape (global, reusable), and the **relation strategy** (Entries fields, Matrix, CKEditor nested entries, or a combination).

**CMS edition first:** multiple custom user groups with per-group edit/view restrictions need **Pro or Enterprise**; Team has one fixed "Team" group and a 5-user cap. Editions table: `references/users-and-permissions.md`.

## Section Type Decision

| Need | Section Type | URI Example |
|------|-------------|-------------|
| One-off page (homepage, about, contact) | **Single** | `__home__`, `about` |
| Site-wide settings (footer, header config) | **Single** (no URI, `preloadSingles`) | — |
| Flat collection (blog, news, events) | **Channel** | `blog/{slug}` |
| Hierarchical pages (docs, services) | **Structure** | `{parent.uri}/{slug}` |
| Taxonomy (topics, categories) | **Structure** (replaces categories) | `topics/{slug}` |
| Flat tags | **Channel** (replaces tags) | — |

Section properties (`maxAuthors`, `minAuthors` [5.10+], `previewTargets`), `preloadSingles`, structure navigation queries, global entry types, per-context overrides [5.6+] and entry type visual identity (`description`/`group` [5.8+], `uiLabelFormat` [5.9+]): `references/sections-and-entry-types.md`. Singles always propagate to all sites (hard-coded).

## Fields: Reuse-First, Never Reserved

Fields are defined once globally and **instanced** into layouts; an instance can override label, handle, instructions and required. Before proposing any field you MUST:

1. **Enumerate the existing field pool** (`config/project/fields/` or Settings → Fields).
2. **Classify each proposed field** as Reuse, Reuse with settings review (flag as a decision for the user), or Create new (justify it). Only create a new field when the type or settings differ.
3. **Single-instance fields** (Matrix, Content Block, Addresses) appear once per layout and share all config across layouts.
4. **Present the plan as a table**, one row per field. Do not create a new field without it.

But don't over-reuse: if one instance could reasonably need different settings, split it. The search index can't tell instances apart.

**Check every proposed handle against the reserved list** (`Field::RESERVED_HANDLES` [5.8+], 83+ handles, case-insensitive). The common collisions: `title`, `slug`, `status`, `url`, `link`, `icon`, `parent`, `children`, `owner`, `site`, `level`, `type`, `author`, `postDate`, `enabled`, `language`. Use a domain synonym (`heading`, `targetLink`, `entryType`). Full workflow, synonym table, per-element-type lists and the multi-instance table: `references/field-pool-and-handles.md`.

## CKEditor vs Matrix vs Content Block

- **Matrix** — reorderable blocks, page builders, data grids, galleries. View modes: blocks, cards, cards-grid, index.
- **CKEditor** with nested entries — rich text with occasional inline structured content (image, code, CTA blocks).
- **Content Block** [5.8+] — single non-repeatable nested entry for a reusable field group (SEO metadata, banner config).

Decision table, nested entry type patterns and the CKEditor chunks rendering pattern: `references/content-patterns.md`.

## After creating sections — tidy the Entries element index

Once Entries sources have been customized, Craft persists them to `elementSources.craft\elements\Entry` in `config/project/project.yaml` and **appends** each new section to the bottom with **generic** columns. Required follow-up in the same change set: place the source next to **role peers** under the right heading, match **`tableAttributes`** and **`defaultSort`** to the closest similar section, include `link` only when the section has URLs, drop empty `heading: ''` leftovers. Precondition, checklist and column keys (`field:` vs `fieldInstance:`): `references/element-index-sources.md`.

## Common Pitfalls

- **Over-using Matrix** — content needing its own URL, independent querying or permissions is a separate section plus an Entries field. 15+ entry types in one Matrix is a red flag (`content-patterns.md`).
- **Duplicate, over-reused, vague or reserved fields** — run the reuse-first workflow and handle check above; `image`, `text`, `link` need domain context (`featuredImage`), not over-specifying (`blogFeaturedImage`).
- **Not planning multi-site from the start** — propagation method, field translation methods, and site settings must be configured before content exists. Changing propagation later resaves all entries (`infrastructure.md`).
- **Categories/tags/globals in new projects** — use entries; enable `preloadSingles` so singles are global Twig variables.
- **Not using `.eagerly()`** — every relational field access inside a loop needs it to prevent N+1 queries (`relations-and-eager-loading.md`).
- **Regenerating YAML from a DB that's behind the branch** — `project-config/write` and `rebuild` treat the DB as the source of truth and delete or revert teammates' YAML on a restored prod dump. Run `ddev craft up` and require a clean `project-config/diff` first. See `infrastructure.md` (Project Config Essentials) and the `craftcms` skill's `deployment.md` (project-config/write safely).
- **Database IDs in URI formats** — IDs differ across environments. Use `{slug}`, `{canonicalUid}`, or custom fields.
- **Not setting `allowAdminChanges => false` in production** — without this, production schema changes won't sync back to dev.
- **`@web` in filesystem URLs** — spoofable or empty in console/queue contexts. Use env vars (`$ASSETS_URL`) (`infrastructure.md`).
- **Ignoring entry type icon, color and description** — editors navigate by them (`sections-and-entry-types.md`).

## Reference Files

Read the relevant reference file(s) for your task.

**Task examples:**
- "Add fields to an existing entry type" / "Modify an entry type's field layout" → read `field-pool-and-handles.md` (Reuse-First Workflow)
- "Is this field handle allowed?" → read `field-pool-and-handles.md` (Reserved handles)
- "Section settings, preloadSingles, entry type icons/colors" → read `sections-and-entry-types.md`
- "Plan a blog content architecture" / "entrify categories, tags, globals" → read `content-patterns.md`
- "Which field type should I use for X?" → read `field-types.md`
- "Set up relatedTo queries" → read `relations-and-eager-loading.md`
- "Configure Matrix with nested entries" → read `field-types.md` (Matrix section)
- "Plan a multi-site content model" → read `content-patterns.md` + `infrastructure.md` (propagation)
- "Set up users, groups, and permissions" → read `users-and-permissions.md`
- "Understand project config workflow" → read `infrastructure.md` (Project Config Essentials)
- "Run project-config/write / restored a prod DB dump / YAML files deleted from config/project" → read `infrastructure.md` (Project Config Essentials) + the `craftcms` skill's `deployment.md` (project-config/write safely)
- "How does Craft store content internally?" → read `infrastructure.md` (Storage Model)
- "Set up asset volumes and filesystems" → read `infrastructure.md` (Assets section)
- "Configure URI format for a structure section" → read `object-templates.md` (Structure URI Patterns)
- "Dynamic asset upload subpath" / "subpath broken after moving field into Matrix" → read `object-templates.md` (Asset Subpath Patterns, The Matrix Gotcha)
- "Tidy Entries index after creating FAQ sections" / "new section at bottom of Entries with wrong columns" / "match FAQ Index to News Index sources" → read `element-index-sources.md`

| Reference | Scope |
|-----------|-------|
| `references/field-pool-and-handles.md` | Field instances and overrides, multi-instance vs single-instance fields, the Reuse-First Workflow, reserved handles (full lists and synonyms). |
| `references/sections-and-entry-types.md` | Section properties, singles and `preloadSingles`, structure navigation queries, global entry types, entry type visual identity. |
| `references/field-types.md` | All built-in field types: settings, Twig access patterns, query syntax, gotchas. Matrix configuration, view modes, nesting. |
| `references/relations-and-eager-loading.md` | relatedTo() shapes (4 forms), .with() eager loading, .eagerly() lazy eager loading, nested eager loading, native eager-loadable attributes. |
| `references/content-patterns.md` | Strategic patterns for blog, portfolio, multi-site corporate. Section/field/relation architecture per pattern. Entrification timeline and migration commands. CKEditor vs Matrix decisions. |
| `references/users-and-permissions.md` | Users, user groups, CMS editions, addresses, permissions architecture, field layout UI elements. |
| `references/infrastructure.md` | Multi-site propagation methods, volume propagation and the add-a-site trap [5.12+], field translation methods, project config workflow, how Craft stores content (five-table model, JSON field values, relations, nested sets), asset volumes/filesystems/transforms. |
| `references/object-templates.md` | Object template syntax: `{attribute}` vs `{{ twig }}`, URI formats, asset subpaths, preview targets, owner/rootOwner nesting, structure patterns, the Matrix gotcha. |
| `references/element-index-sources.md` | Entries CP index sources in project config: placement under headings, tableAttributes/defaultSort matched to peer sections, post-create checklist after adding sections. |
