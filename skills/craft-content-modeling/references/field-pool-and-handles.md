# Field Pool: Instances, Reuse and Handles

Craft 5 fields live in one global pool and are instanced into field layouts. This file holds the instance override rules, which field types can appear more than once per layout, the mandatory reuse-first workflow for adding fields, and the full list of reserved handles to check every proposed handle against.

## Contents

- [Field Instances](#field-instances--reuse-over-duplication)
- [Multi-Instance vs Single-Instance Fields](#multi-instance-vs-single-instance-fields)
- [Adding Fields to an Entry Type: Reuse-First Workflow](#adding-fields-to-an-entry-type--reuse-first-workflow)
- [Reserved handles](#reserved-handles--check-every-proposed-field-handle-against-this-list)

## Field Instances — Reuse Over Duplication

Fields are defined once globally, then **instanced** into field layouts. Each instance can override four properties without affecting the global definition:

- **Label** — different display name per context
- **Handle** — different template handle per context (5.0.0+)
- **Instructions** — context-specific help text
- **Required** — required in one layout, optional in another
- Default Tip/Warning [5.12+] is set on the field; a layout element's own Tip/Warning overrides it (see `references/field-types.md`).

This means a single `heroImage` Assets field can be placed in a Blog Post, a Service Page, and a Project entry type — each with different labels ("Hero Image", "Banner", "Cover Photo") and different required settings. The field definition, type, and settings are shared.

**The rule: reuse field definitions via instances. Only create a new field when the type or settings differ** (e.g., different allowed volumes, different source restrictions, different character limits). Don't create `blogHeroImage`, `serviceHeroImage`, `projectHeroImage` — create one `heroImage` and instance it.

**But don't reuse just because two fields look alike today.** Apply the single-responsibility test ([SRP](https://en.wikipedia.org/wiki/Single-responsibility_principle)): is there a *reasonable* scenario where one instance would need different settings — a different character limit, translation method, or allowed volumes? If yes, the similarity is incidental, not essential — make them separate fields. Over-reuse has costs that are hard to reverse later:

- **Search can't tell instances apart.** The index records keywords against the field, not the instance, so `summary::daisy` may match a `byline` instance of the same field ([documented](https://craftcms.com/docs/5.x/system/searching.html#multi-instance-fields)). If you rely on distinct field-scoped search, the fields must be separate. (Element-query *filtering* by the overridden handle — `.summary(x).byline(y)` — does work; only the **search index** is instance-blind.)
- **A few relational/`relatedTo` cases** are community-reported to need the *original* handle — verify per case if reused-field results look wrong.

### Multi-Instance vs Single-Instance Fields

A field's `isMultiInstance()` method controls whether it can appear **multiple times in the same layout** with different handles. This is determined by `dbType()` — fields that return `null` are single-instance.

| Category | Field Types | Multi-Instance | Reusable Across Layouts |
|----------|-------------|:--------------:|:-----------------------:|
| **Relational** | Entries, Assets, Categories, Tags, Users | Yes | Yes |
| **Simple** | Plain Text, Number, Email, URL, Color, Lightswitch, Money, Range, Time, Date/Time | Yes | Yes |
| **Option** | Dropdown, Checkboxes, Multi-Select, Radio Buttons, Button Group | Yes | Yes |
| **Structured** | Table, Link, Icon, Country | Yes | Yes |
| **Nested element** | Matrix, Content Block, Addresses | **No** | Yes (with caveats) |

**Single-instance caveats:** Matrix, Content Block, and Addresses fields CAN be reused across different entry types (placed in multiple field layouts), but they can only appear **once per layout** and their configuration is fully shared — changing the entry types or settings on a Matrix field affects every entry type using it. Reuse these when contexts genuinely share the same structure. Create separate fields when different contexts need different nested entry types or settings.

## Adding Fields to an Entry Type — Reuse-First Workflow

Before proposing any field in a content model change, you MUST:

1. **Enumerate the existing field pool.** Read `config/project/fields/` (or CP Settings → Fields). List every field with its type, handle, and key settings.
2. **For each proposed field, classify into one of three categories:**
   - **Reuse** — existing field with matching type and compatible settings. Instance it into the layout; optionally override label, handle, instructions, or required.
   - **Reuse with settings review** — existing field of the correct type but slightly different settings (e.g., different allowed volumes, different character limit). Propose whether settings can be unified so one definition serves both contexts. Flag this as a decision for the user.
   - **Create new** — no existing field matches by type or functional purpose. Justify why a new field is needed.
3. **For single-instance fields** (Matrix, Content Block, Addresses) — if an existing field shares the same nested structure, reuse it. If the contexts need different nested entry types or settings, creating a new field is justified — note the shared-config caveat in your reasoning.
4. **Present the plan as a table** — one row per proposed field, showing the reuse decision, the existing field being reused (if applicable), and the rationale for any new field. Do not create a new field without this table.

Creating a field that duplicates an existing field's functionality is the most common content modeling mistake — it pollutes the global pool, confuses editors, and makes future refactoring harder.

## Reserved handles — check every proposed field handle against this list

Craft has **83+ reserved handles** across all element types via `Field::RESERVED_HANDLES` [5.8+]. Validation is case-insensitive. Using any of these as a custom field handle will cause a validation error or silent template collision where the native attribute shadows the custom field.

**Before proposing any field handle in a content model, check it against the lists below.** When a user asks for a field that matches a native attribute name, always use a domain-specific synonym. For example: user says "I need a title field" — the entry already has a native `title`, so use `heading`, `headline`, or `pageTitle` depending on context.

**Most commonly collided (the ones you'll actually try to use):**

| Reserved | Use Instead | Why |
|----------|-------------|-----|
| `title` | `heading`, `headline`, `label`, `pageTitle` | Native element title |
| `slug` | `urlSlug`, `handle` | Native URL slug |
| `status` | `state`, `phase`, `condition` | Native element status |
| `url` | `externalUrl`, `targetUrl`, `websiteUrl` | Native element URL |
| `link` | `targetLink`, `ctaLink`, `primaryLink` | Native `getLink()` method |
| `icon` | `entryIcon`, `menuIcon`, `featureIcon` | Native element icon (5.0.0) |
| `parent` | `parentEntry`, `parentItem`, `belongsTo` | Native structure parent |
| `children` | `childEntries`, `subItems`, `nestedItems` | Native structure children |
| `owner` | `entryOwner`, `ownerElement` | Native nested entry owner |
| `site` | `location`, `branch`, `region` | Native site object |
| `level` | `depth`, `tier`, `nestingLevel` | Native structure level |
| `ancestors` | `parentChain`, `breadcrumbEntries` | Native structure ancestors |
| `siblings` | `peerEntries`, `relatedSiblings` | Native structure siblings |
| `enabled` | `isActive`, `isPublished`, `isVisible` | Native enabled/disabled state |
| `language` | `locale`, `contentLanguage` | Native site language |
| `localized` | `translations`, `localizedVersions` | Native localized entries query |
| `next` / `prev` | `nextEntry` / `prevEntry` | Native structure navigation |
| `ref` | `reference`, `referenceCode` | Native reference tag |
| `type` | `entryType`, `category`, `variant` | Native entry type |
| `author` / `authors` | `writer`, `creator`, `contributor` | Native entry author(s) |
| `postDate` | `publishDate`, `releaseDate`, `goLiveDate` | Native entry post date |

**Full list of reserved handles shared across ALL element types** (from `Field::RESERVED_HANDLES` [5.8+]):

`ancestors`, `archived`, `attributes`, `behaviors`, `canonical`, `children`, `contentTable`, `dateCreated`, `dateDeleted`, `dateLastMerged`, `dateUpdated`, `descendants`, `draftId`, `enabled`, `enabledForSite`, `error`, `errors`, `fieldLayoutId`, `fieldValue`, `fieldValues`, `firstSave`, `icon`, `id`, `language`, `level`, `lft`, `link`, `localized`, `next`, `nextSibling`, `owner`, `parent`, `parents`, `prev`, `prevSibling`, `ref`, `revisionId`, `rgt`, `root`, `searchScore`, `siblings`, `site`, `siteId`, `siteSettingsId`, `slug`, `sortOrder`, `status`, `structureId`, `title`, `trashed`, `uid`, `uri`, `url`, `viewMode`

**Additional per-element-type reserved handles:**

| Element Type | Additional Reserved |
|---|---|
| **Entries** | `author`, `authorId`, `authorIds`, `authors`, `section`, `sectionId`, `type`, `postDate` |
| **Assets** | `alt`, `extension`, `filename`, `folder`, `height`, `kind`, `size`, `volume`, `width` |
| **Users** | `active`, `addresses`, `admin`, `affiliatedSiteId` [5.6+], `email`, `firstName`, `friendlyName`, `fullName`, `groups`, `lastName`, `locked`, `name`, `password`, `pending`, `photo`, `suspended`, `username` |
| **Categories** | `group` |
| **Tags** | `group` |
| **Addresses** | `address`, `countryCode`, `fullName`, `latLong`, `organization`, `organizationTaxId` |

**Also globally reserved** (from `HandleValidator::$baseReservedWords`, applies to ALL handles): `attribute`, `attributeLabels`, `attributeNames`, `attributes`, `dateCreated`, `dateUpdated`, `errors`, `false`, `fields`, `handle`, `id`, `n`, `name`, `no`, `rules`, `this`, `true`, `uid`, `y`, `yes`

### Handle check for every field in a content model

`image`, `text`, `link` are too generic (and `link` is actually reserved). For every field handle in a content model, follow this check: (1) is the handle in the reserved list? If yes, use a synonym from the table. (2) Is the handle too generic for the global field pool? If yes, add domain context: `featuredImage`, `bodyContent`, `primaryLink`. (3) Don't over-specify — `blogFeaturedImage` creates a new field when you could instance `featuredImage` with a label override.
