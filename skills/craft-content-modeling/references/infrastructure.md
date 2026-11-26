# Infrastructure — Propagation, Project Config, Storage, Assets

Multi-site propagation, project config workflow, how Craft stores content internally, and asset volume/filesystem/transform architecture.

## Contents

- Propagation Methods (Multi-Site) — section/Matrix propagation, asset (volume) propagation and the add-a-site trap, field translation methods
- Project Config Essentials — YAML workflow, deployment rules, dateModified
- How Craft Stores Content — five-table model, JSON field values, relations storage, nested sets, drafts
- Asset Volumes, Filesystems, and Transforms — three-layer model, filesystem architecture, volume settings, image transforms

## Common Pitfalls

- Not configuring propagation and translation methods before populating content — changing later resaves all entries.
- Manually editing project config YAML — let Craft manage `config/project/`.
- Forgetting `project-config/touch` after non-CP changes to YAML (Git pull, manual edit, merge conflict resolution).
- Using database IDs in URI formats — IDs differ across environments. Use `{slug}` or `{canonicalUid}`.
- Not setting `allowAdminChanges => false` in production.
- [5.12+] Leaving a shared-media volume on the default **Custom** propagation on a multi-site project, or adding a second site to a single-site install without first switching volumes to **Save assets to all sites**. Existing assets don't reach the new site and Assets fields render empty there. See "Asset Propagation (Volumes)".

---

## Propagation Methods (Multi-Site)

Available for channels and structures. Singles always propagate to all sites.

| Method | Behavior |
|--------|----------|
| Only save to site created in | Entries exist in one site only |
| Same site group | Entries propagate within the same site group |
| Same language | Entries propagate to sites sharing the same language |
| All enabled sites | Entries exist in all enabled sites (default) |
| Let each entry choose | Per-entry control in the **Sites** sidebar pane [5.12+], which lists the entry's sites with per-site status toggles and an "Add a site…" menu. Before 5.12: the Status pane's per-site toggles. |

Matrix fields have their **own** propagation method, independent of the section's.

[5.12+] On multi-site installs, element edit pages show a **Sites** pane in place of the Status pane, for every element that can exist in more than one site. Only "Let each entry choose" sections and assets in Custom volumes (below) offer "Add a site…"; sites added there can be removed again. Unsaved elements, revisions, single-site installs and element types that customise their Status pane (such as users) keep the Status pane.

### Asset Propagation (Volumes) [5.12+]

[5.12+] Volumes have a **Propagation Method** (`craft\models\Volume::$propagationMethod`, a `craft\enums\PropagationMethod`). Before 5.12: every asset existed in every site and there was nothing to choose.

| Setting | YAML value | Behaviour |
|---------|-----------|-----------|
| Save assets to all sites | `all` | [5.12+] Every asset exists in every site. Before 5.12: every volume behaved this way. |
| Let each asset choose which sites it should be saved to | `custom` | An asset exists only in the sites it was saved or added to. A CP upload is saved to the site it was uploaded from; authors add or remove sites in the asset's Sites pane, and "Delete for site" works as long as another site keeps it. |

Defaults (`src/models/Volume.php`, `src/migrations/m261022_000000_volume_propagation_method.php` in the [pinned source](https://github.com/craftcms/cms/blob/5.12.4/src/migrations/m261022_000000_volume_propagation_method.php)):

- **New volumes default to Custom**, on multi-site installs too.
- The upgrade migration sets existing volumes to **All on multi-site installs** and **Custom on single-site installs**, and adds `propagationMethod` to every `config/project/volumes/*.yaml`. Commit those files after the local `craft up`.
- On single-site installs the setting is **hidden** (the select only renders when the install is multi-site), so volumes sit on Custom without anyone choosing it.
- Applying an older volume YAML with no `propagationMethod` key uses the same site-count rule, but only when it creates the volume. An existing volume keeps its value.
- The temporary uploads volume is always All.

**Recommendation for multi-site projects:** set every volume that holds shared media (logos, photography, product shots, downloads used on all sites) to **Save assets to all sites**, and choose deliberately each time you create a volume, because the default is Custom. Keep Custom for media that is genuinely per site (a regional press kit, per-market legal PDFs).

#### Assets may not exist in the current site

Relation fields query their targets in the owner's site (`BaseRelationField::normalizeValue()` uses `targetSiteId()`, and Assets fields have no target-site setting). So when an asset only exists in site A, `entry.heroImage.one()` on the site B version of the entry returns `null`, the Assets field looks empty to site B editors, and nothing errors. Template null-guards (`asset ?? null`) keep the page rendering, but the image is gone.

#### The add-a-second-site trap

[changed 5.12] A single-site project upgrades to 5.12, so its volumes become Custom without a visible setting. Later a second site is added. `Sites::handleChangedSite()` propagates existing assets to a new site **except those in Custom volumes**, so none of the existing assets exist in the new site and every image on its entries renders empty.

Fix, in order of preference:

1. Switch shared volumes to **Save assets to all sites** (Settings → Assets → Volumes). Do it before adding the site where you can. For an existing volume the switch queues a resave job that adds its existing assets to every site, so it also repairs a site that was already added. Commit the changed volume YAML: `craft up` on the other environments applies the same switch. Switching back to Custom moves nothing.
2. Add the asset to the missing site from its Sites pane, when only a few assets are meant to be shared.
3. Last resort in a template, by source reading and not runtime-verified: `entry.heroImage.site('*').unique().preferSites([currentSite.id]).one()`.

Programmatic uploads into Custom volumes have their own trap (`new Asset()` defaults to the primary site): see the `craftcms` skill's `elements.md` → "Assets in Custom volumes".

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

[5.12+] `craft project-config/check` verifies that the YAML's Craft and plugin schema versions match the installed code without applying anything, and exits non-zero when they don't. Run it before `craft up` in a deploy to fail fast on YAML written by a newer Craft (5.12 YAML fails it on a 5.11 box). It needs database access; `--require-yaml=0` exits 0 when there's no `project.yaml`. Details: the `craftcms` skill's `deployment.md`.

### Rules

- Never manually edit YAML — let Craft manage it
- Always set `allowAdminChanges => false` in production
- Use UIDs (not IDs) — they're stable across environments
- After resolving Git merge conflicts in YAML: `ddev craft project-config/touch` then `ddev craft project-config/apply`
- Use `$ENV_VAR` syntax in YAML for environment-specific values — including for genuinely per-environment plugin settings; don't move a setting to a DB-only column to get "per-environment tuning"
- Plugin settings — including per-instance/per-entity *operational* settings (alert thresholds, notification routing, workflow mappings) — are configuration and belong in project config, the canonical source of truth, not a DB-only column. Set them locally and deploy; prod project config is read-only by design. The risk to manage is YAML↔DB divergence (a downstream DB edit silently reverts on the next `craft up`), fixed by keeping project config authoritative — not by bypassing it. For the full rationale and the code-review misconception it corrects, see the `craftcms` skill's `architecture.md` → "Settings belong in project config".
- **After every project config change made outside the CP** (manual edit, merge conflict resolution, script): run `ddev craft project-config/touch` to update the `dateModified` timestamp, then `ddev craft up` to apply, then `ddev craft project-config/diff` must print "No pending project config YAML changes." `craft up` itself compares YAML content (`areChangesPending(force: true)`, `UpController.php:60` in `craftcms/cms` at ref=5.11.5.1), so it applies an edit without the bump. The bump is what makes the CP's "pending changes" alert notice it: that check skips the content comparison while `project.yaml`'s mtime is unchanged. Keep doing both. The CP updates `dateModified` itself when you save through the UI.
- **Never run `project-config/write` on a DB that's behind the branch** (for example, restored from a production dump). It empties `config/project/` and rewrites it from the DB, deleting teammates' YAML. Gate: `craft up`, clean `project-config/diff`, then `write`, then `git diff -- config/project`. See the `craftcms` skill's `deployment.md` → "project-config/write safely".
- **After creating sections or singles** that appear in Entries: tidy `elementSources.craft\elements\Entry` (placement under the right heading, `tableAttributes` / `defaultSort` matched to role peers). This is part of the content model, not optional CP cosmetics. Full checklist: `element-index-sources.md`.

### Authoring schema from code (migrations, scripts, MCP tools)

When code creates schema — a content migration, a setup script, an AI/MCP tool — author it through the **service layer**: `Craft::$app->getEntries()->saveSection()`, `->saveEntryType()`, `Craft::$app->getFields()->saveField()`, and the field-layout APIs (see the `craftcms` skill's `migrations.md` → "Content Migrations"). Craft validates the model (you get structured errors back), assigns/reuses UIDs, and writes the project-config YAML for you — so "author through Craft" and "YAML is the source of truth" are the same thing, not a trade-off. The YAML is only written when the code runs inside a request that ends normally (a migration or a console command). A bare script that bootstraps Craft without `$app->run()` never flushes it; see the `craftcms` skill's `migrations.md` → "Project config writes outside a request".

[5.12+] Craft's own MCP `configuration_*` tools author sections, fields and entry types through the same service layer. They need an admin user, the client granted Full access, and `allowAdminChanges` on for writes, so they belong on dev like any other schema authoring. Setup and access rules: the `craft-mcp` skill.

Do **not** have code emit raw `config/project/*.yaml` and lean on `project-config/apply` to *author* new schema. Hand-composing YAML means hand-managing UIDs, key ordering, and nested structure; validation only happens at apply time, as an all-or-nothing diff that fails opaquely. `project-config/apply` is for **propagating already-committed YAML across environments** (the deploy step), not for authoring.

This also decides *where* a change is even possible: production runs `allowAdminChanges => false`, which makes Craft refuse runtime project-config writes. So service-layer schema writes only work where `allowAdminChanges` is `true` (typically local/dev). The correct lifecycle is: author in dev via the service layer → commit the YAML Craft wrote → deploy → `craft up` applies it. An agent hand-writing YAML on a locked-down prod box and running `apply` is effectively an out-of-band deploy that drifts from Git — avoid it.

Note the boundary: this is about **schema** (project config). **Content** (entries, assets — "create a blog post") is database state written with `saveElement()` and never touches project config, regardless of `allowAdminChanges`.

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
- Writing migrations that move field data — set values through the **element API** (`setFieldValue()` + `saveElement()`), which resolves the handle to the right instance UID and writes content *and* relations; don't hand-edit the JSON or `relations` table by UID (see the `craftcms` skill's `elements.md` → "Field value storage")
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

**Environment variables:** Filesystem settings (base URL, path, bucket, subpath) are parsed with `App::parseEnv()`, so storage can differ between local/staging/production. Three forms, by Craft version:

| Form | Example | Since |
|---|---|---|
| Whole value | `$ASSETS_URL` | 5.0 |
| Variable plus subpath | `$PRIMARY_SITE_URL/uploads` | [5.5+] |
| Variable in any `/`-delimited segment, or `${VAR}` anywhere | `uploads/$SITE_HANDLE/images`, `https://${CDN_HOST}/uploads` | [5.9+] (#17794, #17949) |

A bare `$VAR` only resolves when it fills a whole `/`-delimited segment: `$SITE-uploads` is left as-is, so write `${SITE}-uploads`. On a release older than the form's version the literal text is stored and used, so the URL breaks silently. An undefined `${VAR}` resolves to an empty string.

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

[5.5+] The base URL can reuse the site URL instead of a second variable: `url: '$PRIMARY_SITE_URL/uploads'`.

`@webroot` for the `path` is less dangerous (filesystem path, not URL) but env vars are still preferred for portability. The URL is the critical one — it generates `<img src>` and download links, so a wrong value breaks every asset on the site.

### Volume Settings for Content Modeling

Each volume has its own **field layout** — this is where you add custom metadata fields for assets. Common patterns:

- **Alternative Text** (native field layout element) — always include for accessibility. Has its own translation method (`altTranslationMethod`) for multi-site. [changed 5.11] That method is honoured from the **first** save. Before 5.11, the first alt text entered was copied to every site regardless of the setting, and only edits from the second save on were scoped (craftcms/cms#19067). The 5.11 migration backfills `assets_sites.alt` from the old global `assets.alt` column, which is now ignored and is removed in Craft 6 — read alt through the element (`asset.alt`, `alt` in GraphQL), never by joining `assets.alt` in a query.
- **Title translation** — `titleTranslationMethod` controls whether asset titles differ per site (default: per site).
- **Propagation Method** [5.12+]: which sites the volume's assets exist in: All, or Custom (each asset chooses). New volumes default to Custom, and the setting is hidden on single-site installs. Alt text and title translation stay independent of it, but per-site values only exist for sites the asset is in. See "Asset Propagation (Volumes)" above.
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
| Which sites should a volume's assets exist in? [5.12+] | Shared media: **Save assets to all sites**. Per-site media only: Custom. New volumes default to Custom, so set it on purpose. Single-site projects that may add a site later: switch shared volumes to All before adding it. |

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

Transform modes: `crop` (default), `fit`, `stretch`, `letterbox`. Output formats: `jpg`, `png`, `gif`, `webp`, `avif`, plus `jxl` [5.12+] when ImageMagick supports JPEG XL (`Images::getSupportsJxl()`). JPEG XL isn't a web-safe format and many browsers won't render it, so serve it only inside `<picture>` with a fallback. [5.12+] BMP and JPEG XL uploads can be transformed and edited in the Image Editor. The `letterbox` mode supports a `fill` color (4.4.0+). `upscale` control (4.4.0+) prevents small images from being enlarged.

**Named vs ad-hoc:** Use named transforms for consistent sizes reused across templates (hero, thumbnail, card). Use ad-hoc transforms for one-off sizes or when transforms need to be dynamic. Named transforms are stored in project config and sync across environments.
