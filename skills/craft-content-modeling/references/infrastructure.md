# Infrastructure — Propagation, Project Config, Storage, Assets

Multi-site propagation, project config workflow, how Craft stores content internally, and asset volume/filesystem/transform architecture.

## Contents

- Propagation Methods (Multi-Site) — section/Matrix propagation, field translation methods
- Project Config Essentials — YAML workflow, deployment rules, dateModified
- How Craft Stores Content — five-table model, JSON field values, relations storage, nested sets, drafts
- Asset Volumes, Filesystems, and Transforms — three-layer model, filesystem architecture, volume settings, image transforms

## Common Pitfalls

- Not configuring propagation and translation methods before populating content — changing later resaves all entries.
- Manually editing project config YAML — let Craft manage `config/project/`.
- Forgetting `project-config/touch` after non-CP changes to YAML (Git pull, manual edit, merge conflict resolution).
- Using database IDs in URI formats — IDs differ across environments. Use `{slug}` or `{canonicalUid}`.
- Not setting `allowAdminChanges => false` in production.

---

## Propagation Methods (Multi-Site)

Available for channels and structures. Singles always propagate to all sites.

| Method | Behavior |
|--------|----------|
| Only save to site created in | Entries exist in one site only |
| Same site group | Entries propagate within the same site group |
| Same language | Entries propagate to sites sharing the same language |
| All enabled sites | Entries exist in all enabled sites (default) |
| Let each entry choose | Per-entry control via Status sidebar |

Matrix fields have their **own** propagation method, independent of the section's.

**Address elements do NOT propagate with their owner.** Despite implementing `NestedElementInterface` via `NestedElementTrait`, Address elements don't override `getSupportedSites()` or `isLocalized()`. They fall through to the base Element default: primary site only. Matrix entries get multi-site behavior because the Entry class delegates to the field's propagation config — this is Entry-specific, not trait behavior. When working with Addresses on a multi-site project, the address exists only on the primary site regardless of which sites the owner (User, Entry) propagates to.

### Field Translation Methods

Per-field setting controlling how values behave across sites:

| Method | Behavior |
|--------|----------|
| Not translatable | Same value across all sites |
| Per site | Independent value per site |
| Per site group | Shared within site group, independent across groups |
| Per language | Shared across sites with same language |
| Custom | User-defined grouping key |

Configure translation methods **before** populating content.

## Project Config Essentials

All schema changes (sections, entry types, fields, volumes, transforms, sites,
plugins, permissions) are stored as YAML in `config/project/`.

### Workflow

1. Make CP changes in **development** environment
2. YAML auto-updates in `config/project/`
3. Commit to Git
4. Deploy to staging/production
5. Run `ddev craft up` (applies migrations + project config)

### Rules

- Never manually edit YAML — let Craft manage it
- Always set `allowAdminChanges => false` in production
- Use UIDs (not IDs) — they're stable across environments
- After resolving Git merge conflicts in YAML: `ddev craft project-config/touch` then `ddev craft project-config/apply`
- Use `$ENV_VAR` syntax in YAML for environment-specific values
- **After every project config change** (whether editing `project.yaml` or any subfile in `config/project/`): run `ddev craft project-config/touch` to update the `dateModified` timestamp, then `ddev craft up` to apply. The CP auto-updates `dateModified` when changes are saved through the UI, but any change made outside the CP (Git pull, manual edit, merge conflict resolution, script) requires `project-config/touch` to signal that config has changed. Without it, `craft up` on other environments won't detect the change. This is a hard rule — never skip it.

## How Craft Stores Content

Understanding the storage architecture helps make better content modeling decisions.

### The Five-Table Model

Every element writes to multiple tables on save:

1. **`elements`** — Identity registry. Stores ID, element type, enabled/archived/soft-deleted flags, timestamps. Does NOT store content.
2. **`elements_sites`** — Per-site state. Stores URI, slug, per-site enabled status, and the **`content` JSON column** where all custom field values live.
3. **Element-type table** (`entries`, `assets`, `users`, etc.) — Type-specific attributes. For entries: section, type, author, postDate, expiryDate.
4. **`relations`** — Normalized source-to-target connections for relational fields. Enables bidirectional `relatedTo()` queries.
5. **`searchindex`** — Denormalized text projection for full-text search. Rebuildable from canonical data.

### Field Values Are JSON Keyed by Instance UID

Custom field values are stored in `elements_sites.content` as JSON, keyed by the **field layout element UID** (not the field handle). This is why field instances work — the same field definition can appear multiple times in a layout with different handles, and each stores its data independently under its own instance UID.

This matters when:
- Debugging content in the database — look up the field layout element UID, not the handle
- Writing migrations that move field data — reference UIDs
- Understanding why renaming a field handle doesn't require a migration

### Relations: Two Storage Layers

Relational fields store data in two places:
- **JSON** (`elements_sites.content`) — records which elements were selected and their order per field instance
- **`relations` table** — normalized source-to-target connections that power `relatedTo()` queries in both directions

This dual storage is why `relatedTo()` queries are fast (indexed `relations` table) while the field value on an element reflects the authoring context (JSON).

### Nested Entries (Matrix) Are Full Elements

Matrix entries are not stored in a separate content table. They are first-class elements with their own rows in `elements`, `elements_sites`, and `entries`. Parent linkage is in `elements_owners`. This means nested entries support relations, drafts, permissions, and search indexing — but also explains why deeply nested Matrix fields are expensive (many rows written per save, `max_input_vars` limits on large forms).

### Structures Use Nested Sets

Structure sections store hierarchy in `structureelements` using a **nested set model** (left/right boundary values). This makes ancestry and descendant queries very fast without recursion, but reordering large structures requires recalculating boundary values across many rows.

### Drafts Reuse Unchanged Nested Entries

When a draft is created, unchanged nested entries are not duplicated — they are reused from the canonical element. Only when a nested entry is modified in the draft does it get its own derivative element row. This minimizes storage overhead but means draft creation time scales with the number of modified blocks, not total blocks.

## Asset Volumes, Filesystems, and Transforms

### The Three-Layer Model

1. **Filesystem** — the storage backend (local disk, S3, Google Cloud, Azure). Defined once with a handle, base URL, and settings. Plugins add cloud filesystems.
2. **Volume** — the content layer. References a filesystem, adds a field layout for asset metadata, and controls permissions. This is what editors see.
3. **Image Transform** — the processing layer. Named transforms (defined in Settings) or ad-hoc transforms (defined in templates). Can be stored on a separate filesystem from originals.

### Filesystem Architecture Decisions

| Approach | When to use |
|----------|-------------|
| **One filesystem, one volume** | Simple projects. Local dev with a single uploads directory. |
| **One filesystem, multiple volumes** | When you want separate content buckets (Images, Documents, Videos) but all stored in the same S3 bucket. Each volume uses a unique `subpath` (e.g., `images/`, `documents/`). |
| **Multiple filesystems, multiple volumes** | When storage requirements differ — images on a CDN-optimized filesystem, documents on standard storage, private files on a non-public filesystem. |
| **Separate transform filesystem** | When you want transforms on a CDN or different storage tier. Set `transformFs` on the volume — originals stay on the primary filesystem. |

**Subpath rules:** When volumes share a filesystem, each must have a unique first-level subpath directory. If Volume A uses `images/`, Volume B cannot use `images/` or `images/photos/` — but `documents/` is fine.

**Environment variables:** Filesystem handles and subpaths support `$ENV_VAR` syntax via `App::parseEnv()`, so storage can differ between local/staging/production.

**Never use `@web` for filesystem URLs.** `@web` is auto-detected from the HTTP request's `Host` header — it can be spoofed if `trustedHostPatterns` isn't configured, and it resolves to empty in console/queue contexts (no HTTP request). Use environment variables instead:

```yaml
# Wrong — @web is unreliable
fs:
  localImages:
    url: '@web/uploads'
    settings:
      path: '@webroot/uploads'

# Correct — explicit env vars
fs:
  localImages:
    url: '$ASSETS_URL'
    settings:
      path: '$ASSETS_PATH'
```

```
# .env
ASSETS_URL=https://mysite.ddev.site/uploads
ASSETS_PATH=/var/www/html/web/uploads
```

`@webroot` for the `path` is less dangerous (filesystem path, not URL) but env vars are still preferred for portability. The URL is the critical one — it generates `<img src>` and download links, so a wrong value breaks every asset on the site.

### Volume Settings for Content Modeling

Each volume has its own **field layout** — this is where you add custom metadata fields for assets. Common patterns:

- **Alternative Text** (native field layout element) — always include for accessibility. Has its own translation method (`altTranslationMethod`) for multi-site.
- **Title translation** — `titleTranslationMethod` controls whether asset titles differ per site (default: per site).
- **Custom fields** — photographer credit, copyright notice, focal point, usage rights, expiry date.
- **Reserved handles** on volumes: `alt`, `extension`, `filename`, `folder`, `height`, `kind`, `size`, `volume`, `width`.

File type restrictions are set on the **Assets field** (per usage), not on the volume itself. The same volume can serve images in one field and documents in another.

### Modeling Decisions

| Question | Guidance |
|----------|----------|
| How many volumes? | One per logical content bucket. Separate images from documents from private files. |
| How many filesystems? | One per storage requirement. Dev uses local, production uses S3 — same volume handle, different filesystem per environment. |
| Should transforms use a separate filesystem? | Yes if you want transforms on a CDN or cheaper storage. Otherwise the primary filesystem works fine. |
| Do volumes need different field layouts? | Yes — photos need credit/copyright fields, documents need version/category fields. |
| How to handle multi-site asset metadata? | Set `altTranslationMethod` and `titleTranslationMethod` per volume. Most projects use "per site" for alt text (accessibility translations) and "not translatable" for filenames. |

### Image Transforms

```twig
{# Named transform (defined in Settings -> Assets -> Image Transforms) #}
<img src="{{ asset.getUrl('thumb') }}" alt="{{ asset.alt }}">

{# Ad-hoc transform #}
{% set transform = { width: 300, height: 200, mode: 'crop', format: 'webp' } %}
<img src="{{ asset.getUrl(transform) }}" alt="{{ asset.alt }}">

{# Srcset #}
{{ asset.getImg({ width: 300 }, ['1.5x', '2x', '3x']) }}
```

Transform modes: `crop` (default), `fit`, `stretch`, `letterbox`. Formats: `jpg`, `png`, `webp`, `avif`. The `letterbox` mode supports a `fill` color (4.4.0+). `upscale` control (4.4.0+) prevents small images from being enlarged.

**Named vs ad-hoc:** Use named transforms for consistent sizes reused across templates (hero, thumbnail, card). Use ad-hoc transforms for one-off sizes or when transforms need to be dynamic. Named transforms are stored in project config and sync across environments.
