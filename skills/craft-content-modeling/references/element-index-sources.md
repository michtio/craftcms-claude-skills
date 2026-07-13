# Entries Element Index Sources (Project Config)

How the **Entries** index is organized in the Control Panel after you create sections. This is site content modeling (project config), not custom element-type PHP. For `defineSources()` / custom element indexes, see the `craftcms` skill's `element-index.md`.

## Contents

- Why this matters
- Where it lives
- Source shape
- Placement rules (match siblings)
- Table columns and sort (match siblings)
- Post-create checklist
- Common pitfalls

## Why this matters

Creating a section (CP or YAML) also registers a source under `elementSources.craft\elements\Entry` in `config/project/project.yaml`. Craft often appends new sources at the **bottom** of the list with **generic** columns. Editors then see FAQs, indexes, or taxonomies in the wrong sidebar group, with columns that do not match News / Events / Products peers.

**After every new section (or single that should appear in Entries), tidy its index source.** Placement and columns are part of shipping the content model, not optional polish.

## Where it lives

```
config/project/project.yaml
  elementSources:
    craft\elements\Entry:
      - { key, type, heading?, tableAttributes?, defaultSort?, ... }
```

Also reflected when you customize the Entries index in the CP (Customize sources / columns) with `allowAdminChanges` on. Prefer doing it once in local and committing YAML.

**Precondition — the `elementSources` block only exists once sources have been customized at least once.** On a project that has never used *Customize sources*, there is no `elementSources.craft\elements\Entry` key in `project.yaml`: Craft renders default sources (every section, in section order, with generic columns), so a newly created section just appears in that default list and there is nothing in YAML to tidy. Once sources are customized, Craft persists the **full** source list to YAML and **appends** each subsequently created section to the bottom — which is when this cleanup applies. Practical rule: customize sources once (that captures the list), then maintain placement and columns as you add sections. Most multi-section sites customize early, which is why this is a routine follow-up rather than an edge case.

Related: Craft 5.9+ **custom entry index pages** group sections into separate CP nav items. That is a different feature. This doc is about the **shared Entries index** source list and columns.

## Source shape

Typical native source for a section or single:

```yaml
-
  defaultSort:
    - structure   # or postDate, title, id, field:… / fieldInstance:…
    - asc         # or desc
  defaultViewMode: ''
  disabled: false
  key: 'section:<section-uid>'   # or single:<section-uid>
  tableAttributes:
    - 'field:<field-uid>'        # global field column (prefer when one definition)
    - 'fieldInstance:<layout-element-uid>'  # layout instance column
    - dateUpdated
    - revisionNotes
    - link
    - revisionCreator
  type: native
```

Headings are sources with `type: heading` and a `heading:` label:

```yaml
-
  heading: Indexes
  key: 'heading:<uid>'
  type: heading
```

Keys use **section UIDs** (stable across environments), not handles. Find UIDs in `config/project/sections/*.yaml` filenames or `meta.__names__`.

## Placement rules (match siblings)

Order the source list so **similar section roles sit together** under the same heading. Mirror an established peer; do not invent a new group unless the project already uses one.

| New section role | Place with | Typical heading |
|------------------|------------|-----------------|
| Content channel / structure (News, Events, Products, Services, FAQs as content) | Other primary content sections | Top of list (no heading), or project-specific content group |
| Index single (`newsIndex`, `eventIndex`, `faqIndex`, `productIndex`) | Other `* Index` singles | **Indexes** |
| Taxonomy structure (`*Categories`, locations, tags-as-entries) | Other category / taxonomy sections | **Categories** |
| Reusable includes (People, FAQs as blocks source, Testimonials, Wayfinding) | Other includes | **Includes** (if the project uses it) |
| Utility singles (Search, Success) | Other utilities | **Other** |
| Global-like singles (Header, Footer, SEO) | Other globals | **Globals** |

### Placement procedure

1. Open `project.yaml` and find every source whose `key` matches the new section UID(s).
2. Note any **empty** `heading: ''` blocks Craft left at the end; remove empty headings after moving sources.
3. Cut the new source block(s) and paste **immediately after the closest peer** of the same role (e.g. FAQ Index after News Index; FAQ Categories after News Categories).
4. Keep relative order alphabetical or domain-logical **within** a heading only if the project already does that; otherwise match the existing peer cluster order (Events before News, etc.).

If the project uses Expanded Singles (or similar), each single is its own source: still place it under the same role heading as its peers.

## Table columns and sort (match siblings)

Copy **`tableAttributes`** and **`defaultSort`** from the nearest peer of the same role. Do not invent a one-off column set unless the content model has no peer.

### Role patterns (common on multi-section sites)

**Index singles** (Event Index, News Index, FAQ Index, …)

```yaml
defaultSort:
  - id
  - asc
tableAttributes:
  - dateUpdated
  - revisionNotes
  - link
  - revisionCreator
```

Always include `link` when the single has a public URL.

**Category / taxonomy structures** (News Categories, Event Categories, FAQ Categories, …)

```yaml
defaultSort:
  - structure
  - asc
tableAttributes:
  - 'fieldInstance:<icon-or-summary-instance-uid>'  # only if peers show one
  - dateUpdated
  - revisionNotes
  - link          # only if section has URLs; omit if no URLs (e.g. locations)
  - revisionCreator
```

Match peers: if News Categories shows an icon/summary column, FAQ Categories should too (same field or same field instance pattern). If Event Locations omit `link` because they have no URLs, do the same for similar no-URL taxonomies.

**Primary content channels / structures** (News, Events, Products, Services, FAQs)

```yaml
defaultSort:
  - postDate      # channel
  - desc
# or structure / asc for structures
tableAttributes:
  - 'field:<category-field-uid>'   # category / type column first when peers have it
  - dateCreated                    # optional; match peers
  - dateUpdated
  - revisionNotes
  - link                           # if hasUrls
  - revisionCreator
```

For dated content (events), peers may sort by a date field instance (`fieldInstance:…`) instead of `postDate`. Keep that pattern when adding a second dated section.

**Includes without public URLs**

```yaml
tableAttributes:
  - dateUpdated
  - revisionNotes
  - revisionCreator
  # omit link when hasUrls is false
```

### Column identifier style

| Form | Use when |
|------|----------|
| `field:<field-uid>` | Column is the field definition (common for category Entries fields). Prefer this when peers use it; add a YAML comment with the field name. |
| `fieldInstance:<layout-element-uid>` | Column is a **layout instance** (multi-instance Date/Lightswitch, or instance-specific label). Required when the same field appears multiple times. |
| Native keys (`dateUpdated`, `link`, `type`, `revisionNotes`, `revisionCreator`) | Standard Craft columns; keep the same trailing set as peers. |

When adding a category column, point at the **same kind of field** peers use (e.g. `faqCategory` for FAQs if News uses `newsCategory`), not a random layout leftover.

## Post-create checklist

Run this whenever you add or rename a section / single that appears in Entries:

1. **Section exists** under `config/project/sections/` with correct type, URLs, entry types.
2. **Permissions** for the relevant user groups (`viewEntries`, `saveEntries`, …) if non-admins edit it.
3. **Element index source** in `project.yaml`:
   - [ ] Source not left at the bottom under an empty heading
   - [ ] Placed next to role peers under the correct heading
   - [ ] `defaultSort` matches peers of the same role
   - [ ] `tableAttributes` match peers (category/date column first if applicable; same trailing meta columns)
   - [ ] `link` only when the section has URLs
   - [ ] Empty `heading: ''` sources removed
4. **`ddev craft project-config/touch`** if you edited YAML outside the CP, then **`ddev craft project-config/apply`** (or `ddev craft up`) so other environments pick it up.
5. Spot-check Entries in the CP: sidebar order and columns for the new source vs one peer.

Treat a content-model PR as incomplete if new sections ship without this tidy-up.

## Common pitfalls

- **Leaving Craft's default append position** — new FAQ Index / FAQ Categories sit under blank headings at the end of Entries; editors cannot find them next to News Index / News Categories.
- **Generic columns only** — primary content without a category/type column when every peer has one; or index singles missing `link`.
- **Showing `link` on no-URL sections** — taxonomy or include sections with `hasUrls: false` should match peers that omit `link`.
- **Wrong column key type** — using `fieldInstance` for a single-definition category field when peers use `field:`, or the reverse for multi-instance dates.
- **Sorting structures by `postDate`** — category and include structures usually use `structure` / `asc`; channels use `postDate` / `desc` (or a content date field for events).
- **Tidying only one of a pair** — adding FAQ Index but not FAQ Categories (or the reverse) leaves the model half-organized.
- **Skipping project-config touch** — manual YAML moves never reach other environments without `dateModified` update.

## See also

- Project config workflow: `infrastructure.md` (Project Config Essentials)
- Custom element indexes (PHP): `craftcms` skill → `references/element-index.md`
- Entrification and custom entry index pages (5.9): `content-patterns.md` / SKILL.md Entrification section
