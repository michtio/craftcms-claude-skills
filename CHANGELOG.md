# Changelog

## 1.6.2 -- 2026-06-10

Patch re-release of 1.6.1. The 1.6.1 artifact was published before its SEOMatic documentation correction landed, and published stable versions are immutable — so the corrected docs ship here as 1.6.2 rather than as a re-tag of 1.6.1. **Use 1.6.2.** The content is the host-independent guidance for managing SEOMatic's DB-backed settings via content migrations described in the 1.6.1 entry below; there are no other changes.

## 1.6.1 -- 2026-06-10

Documents how to manage SEOMatic's **DB-backed** settings via content migrations. SEOMatic's Site Settings (Identity `genericUrl`, social), the robots.txt template, and per-section Content SEO live in the `seomatic_metabundles` table, **not** project config, so they don't sync via project config. The reproducible way to change them is a content migration that edits the JSON columns with MySQL `JSON_SET` and then calls `Seomatic::$plugin->clearAllCaches()`. This is **host-independent** — identical on self-hosted, shared hosting, Servd, Craft Cloud, and locally; it's simply the only option when a host gives you no production CP access.

### Changed

- **`skills/craft-site/references/plugins/seomatic.md`** — new "Managing DB-Backed Settings via Content Migrations" section: the `seomatic_metabundles` table shape (`__GLOBAL_BUNDLE__` per `sourceSiteId` vs two-level `section` bundles — section-level `typeId` NULL and entry-type-level, both matched by `sourceHandle`), a worked content migration, and the `MetaBundles` service methods. Plus two gotchas: the empty-field fallback (`fromField` on an empty field → sitewide duplicate descriptions; fix with `fromCustom` + an object-template fallback chain) and `mainEntityOfPage` (per-page schema type) vs `siteType`/`siteSpecificType` (global identity). Recommends a Twig `<script type="application/ld+json">` partial for complex per-entry structured data. Verified against `nystudio107/craft-seomatic ^5.1.16`. New Common Pitfalls entries surface the same traps.
- **`skills/craft-cloud/references/limitations.md`** — the SEOMatic plugin-compatibility row notes that its DB-backed settings (a general SEOMatic trait, not Cloud-specific) are managed via the same content migration on Cloud, where there's no prod CP access.

## 1.6.0 -- 2026-05-30

Tenth skill — **`servd`** — plus the sixth agent (**`craft-code-reviewer-deep`**), a broad accuracy pass verified against Craft 5.10 source, a cross-skill redundancy cleanup, and a fix for the previously-orphaned `craft-cloud` skill (shipped in the docs but never listed in `plugin.json`, so it never actually loaded). Versioning is now decoupled from Craft minor releases — semver tracks the pack itself, not the Craft version, with the 1.4.x line frozen at Craft 5.9. The reference layer also gained the custom-field-input JS lifecycle (the single most common place CP JavaScript silently breaks), the full hand-built CP edit-screen surface (`asCpScreen()` + `_layouts/cp.twig` regions), condition-builder rendering, and `collect()`-first Twig guidance.

### New

- **`skills/servd/`** — tenth skill covering Servd managed hosting end-to-end: SKILL.md + 6 reference files (`deploy-and-environments`, `asset-storage`, `caching`, `database-and-queue`, `limitations`, `local-dev`). Covers git push-to-deploy and `servd.yaml`, the local/staging/production workflow with uni-directional Project Config sync, the `servd/craft-asset-storage` plugin, Servd static caching with Blitz in reverse-proxy mode, MariaDB/MySQL over an SSH tunnel, backups, the Dedicated Queue Runner, and the ephemeral filesystem.
- **`agents/craft-code-reviewer-deep.md`** — sixth agent (Opus, `xhigh` effort) for high-stakes PRs — release branches, security-sensitive code, migrations, multi-service flows — tracing cross-file data flow and verifying claims against Craft source rather than surface pattern-matching.
- **`skills/craftcms/references/cp.md`** — "Layout regions for an edit screen" (the `content`/`sidebar`/`details`/`footer`/`contextMenu`/`toolbar` regions of `_layouts/cp.twig`, settable as a block or a same-named `{% set %}` var) and "Fuller edit screen via `asCpScreen()`" (the `action`/`redirectUrl`/`errorSummary`/`metaSidebar`/`additionalButtons` method surface on `CpScreenResponseBehavior`). Verified against core source.
- **`skills/craftcms/references/field-types-custom.md`** + **`skills/craft-garnish/references/integration.md`** — the custom-field-input JS lifecycle: `namespaceInputId`/`registerJsWithVars` (a bare input id gets namespaced by the field layout, and the same `inputHtml` renders at many namespaces in Matrix/nested entries), the `Cp::` helper table as the PHP-side equivalent of the `forms.*` macros, and the `appendHeadHtml`/`appendBodyHtml`/`initUiElements` re-init order with destroy discipline for document/window-bound listeners.
- **`skills/craftcms/references/cp-ui-patterns.md`** — rendering a condition builder in a CP template via `getBuilderHtml()`/`Conditions::createCondition()`, the zero-arg `BaseConditionRule::inputHtml()` (distinct from a field type's), and a dedicated form-field tip/warning section.
- **`skills/craft-twig-guidelines/SKILL.md`** — `collect()`-first filtering/mapping guidance (bare Twig/Craft array filters don't chain and shouldn't be mixed with Collection methods; there is no `|indexBy` filter) and a safe-output/inline-asset section (`|t`, `|purify` vs `|raw`, `|explodeClass`/`|explodeStyle`, `{% js %}`/`{% css %}` via the View).
- **`skills/craft-site/references/twig-collections.md`** — a greatest-n-per-group recipe (one entry per author) via Collection `.unique('authorId')` rather than a SQL `GROUP BY`, since Craft 5 authors live in the `entries_authors` junction with no `authorId` column to group on.
- **`skills/craft-site/references/plugins/vite.md`** — `nystudio107/craft-vite` plugin reference.

### Changed

- **Accuracy fixes verified against Craft 5.10 source and upstream plugin docs** — `canView`/`canSave`/`canDelete` are public, not protected (protected would fatal); `getContentColumnType()` was removed in Craft 5, use the static `dbType()` (and its no-column return is `null`, not `false`); `inputHtml()` returns `string`, not `?string`; `BaseRelationField::elementType()` is `public static`; `revertToRevision()` requires `$creatorId` and `saveElementAsDraft()` returns `bool`; corrected `reassignEntries()` signature; replaced a fabricated `TestCase::graphql()` with `Gql::executeQuery()`; removed a nonexistent `'craft'` webpack external and fixed the `MixedInput` method list, `Craft.Slideout` superclass, and a phantom `dropTarget` event; categories/tags/globals are deprecated, not CP-disabled; `minAuthors` defaults to 1; corrected the Team edition and `entrify` global-set options; Cloud `artifact-path` defaults to webroot, not the whole project; `resave/all` (not `search/reindex`); `App::mailerConfig()` for SES; fixed an inverted `<picture>` fallback; corrected the Colour-Swatches property API, Embedded Assets `embed.html`, Imager-X vendor (`spacecatninja`), Hyper FQCN link type, and Timeloop limit default. Also fixed the `forms.multiselectField` macro casing and that the CP nav event lives on `craft\web\twig\variables\Cp`, not `craft\helpers\Cp`.
- **`skills/craft-php-guidelines/`** — reframed the `=========` separators, method-level `@author`, and `@param` casing as deliberate house style that diverges from Craft core (dash separators, class-only `@author`); softened the overstated "match over switch — always" to the actual guideline.
- **Cross-skill redundancy cut** — `craft-twig-guidelines` collapses `collect()`/class-collection duplication to pointers into `craft-site`; `tooling.md` is now the canonical ECS/PHPStan config (deferred from `quality.md`); `craftcms/caching.md` converts legacy array config to the fluent `GeneralConfig` API; `craft-site/blitz.md` trimmed to the integration surface; `ddev` documents built-in Mailpit (not an add-on), project bootstrap, `ddev launch`, the `ddev share` ngrok note, and env-var injection.
- **`agents/`** — explicit effort levels on the five existing agents (`high`; `xhigh` for the planner).
- **`skills/craft-site/references/element-partials.md`** — native attributes (`entry.author`, an asset's `uploader`, a user's `photo`) return the element directly, so `.eagerly()` throws; cover them with `.with()` on the outer query instead.
- **`.claude-plugin/plugin.json`** — registered the orphaned `craft-cloud` skill and added `servd` to the skills array (both now actually load).
- **README, `docs/skills-overview.md`, `docs/getting-started.md`, `docs/agents.md`, `.claude-plugin/marketplace.json`, `craft-project-setup` banner** — reconciled counts to 10 skills, 105 reference files, 6 agents, 23 plugin references; documented `craft-code-reviewer-deep`; grouped README example prompts by domain; added the deep-reviewer and Vite rows; fixed the Imager-X vendor; added Servd hosting detection (`servd.yaml` / `servd/craft-asset-storage` / `SERVD_*` env vars), monorepo detection, and a hybrid merge strategy to `craft-project-setup`.
- **`bin/release.sh`** — reconciled the header comment to the decoupled versioning policy (pack-driven semver, not Craft-minor-mirroring).
- **CI** — the GitHub Release `--latest` flag is now derived from commit reachability instead of publish order.

## 1.5.3 -- 2026-05-28

Ninth skill — **`craft-cloud`** — covering Pixel & Tonic's serverless hosting platform end-to-end. Cloud was previously scattered across one-line mentions in five files (a deployment table row, an image-transform note, a migration cache warning, the `craft setup/cloud` command, a couple of image-preset pointers). That fragmentation works as long as you're already self-hosting and Cloud is "another option"; it falls apart the moment a project actually ships on Cloud, where the differences from self-hosted Craft are substantial enough to be its own knowledge surface. The new skill consolidates the platform's full surface — `craft-cloud.yaml`, the Build → Migrate → Release pipeline, the `craftcms/cloud` extension, edge image transforms, edge static caching with `cache.rules` + ESI, MySQL 8 / Postgres 15 constraints, plugin Cloud-compatibility requirements, and the self-hosted → Cloud migration — verified against `craftcms.com/docs/cloud/` and the `craftcms/cloud-extension-yii2@main` source. Authored content covers gaps the docs leave open (mail strategy, log strategy, plugin compatibility matrix, DDEV parity recipe) and is clearly marked as community knowledge rather than Pixel & Tonic-blessed.

### New

- **`skills/craft-cloud/SKILL.md`** — frontmatter with Cloud-specific triggers (`craft-cloud.yaml`, `cloud.esi()`, `App::isEphemeral()`, `CRAFT_EPHEMERAL`, `edge.craft.cloud`, etc.), companion-skill notes for `craftcms` + `craft-site` + `ddev` + `craft-php-guidelines`, a "What's different on Cloud vs self-hosted" decision table (14 rows), 14 cross-cutting pitfalls, and routing into 12 reference files.
- **`skills/craft-cloud/references/config-file.md`** — full `craft-cloud.yaml` key reference verified against `craftcms.com/docs/cloud/config`. Documents every key (`php-version`, `node-version`, `node-path`, `npm-script`, `artifact-path`, `app-path`, `webroot`, `cache.rules`, `redirects`, `rewrites`) with worked examples. `cache.rules` syntax matches the docs' actual `pattern` / `query-string.mode` / `query-string.keys` / `session` shape — duration is set in the response, not in cache.rules.
- **`skills/craft-cloud/references/deploy-pipeline.md`** — Build → Migrate → Release pipeline, On Push vs Manual triggers, 15-minute build cap, build-time system vars (`CRAFT_CLOUD_PROJECT_ID`, `CRAFT_CLOUD_ENVIRONMENT_ID`, `CRAFT_CLOUD_BUILD_ID`, `CRAFT_CLOUD_CDN_BASE_URL`, `CRAFT_CLOUD_ARTIFACT_BASE_URL`, `GIT_SHA`, `NODE_ENV=production`), runtime env vars in Console (including write-only vars), failed-deploy semantics (no rollback, prior version stays live).
- **`skills/craft-cloud/references/extension.md`** — `craftcms/cloud` package internals, source-verified against `craftcms/cloud-extension-yii2@main`. Includes the **actual** `cloud/up` command sequence (read from `UpController.php`): triggers `EVENT_BEFORE_UP`, runs `setup/php-session-table`, runs `setup/db-cache-table`, runs `up` if Craft is installed (migrations + project config), purges the static cache gateway, triggers `EVENT_AFTER_UP`. Documents `App::isEphemeral()` patterns, the Path service for transient writes, `cloud.esi(...)` Twig helper with verified signature (`(template, variables = {})` — template path first, scalar variables only), the filesystem-type table (`AssetsFs`, `BuildArtifactsFs`, `BuildsFs`, `CpResourcesFs`, `StorageFs`, `TmpFs`), and the auto-handled `sendContentAsFile()` upload + 302 redirect to a pre-signed S3 URL.
- **`skills/craft-cloud/references/assets-and-transforms.md`** — Cloud filesystem type (mandatory Subpath, `aws s3 sync` migration pattern with the required `assets/` URL segment), edge image transforms (70MB / 100MP / 12,000px / 1,600px AVIF / 50MP animated limits, `stretch` mode = `object-fit: cover` semantics, automatic WEBP/AVIF content negotiation, no template changes required).
- **`skills/craft-cloud/references/database.md`** — MySQL 8.0 / Postgres 15 (no MariaDB), `tablePrefix` unsupported, auto-wired connection (don't touch `db.php` or `CRAFT_DB_*`), nightly + on-demand backups, restore commands per engine (Postgres custom format requires `pg_restore` with `--no-owner --clean --single-transaction --if-exists --no-acl`).
- **`skills/craft-cloud/references/caching-and-edge.md`** — full `cache.rules` syntax with first-match-wins ordering, opt-outs (`{% expires %}` with no duration, `setNoCacheHeaders()`), `asyncCsrfInputs` force-enabled, the `cloud.esi(...)` constraint set (scalar variables only, no parent Twig context inheritance, `text/html` and `text/plain` responses only, nesting strongly discouraged), tag-based auto-invalidation matching Craft's cache tag system.
- **`skills/craft-cloud/references/domains.md`** — DNS setup (`_cf-custom-hostname` TXT ownership, certificate validation CNAME + 2 TXT records, CNAME to `edge.craft.cloud` for subdomains, two A records for apex when CNAME flattening isn't available), Orange-to-Orange Cloudflare configuration, preview URL format (`project-{handle}-environment-{prefix}.preview.craft.cloud`), auto SSL via Cloudflare, `www` not auto-added.
- **`skills/craft-cloud/references/commands-and-cron.md`** — Console command runner (255-char cap after `craft`, 15-minute timeout, no interactive prompts, no shell interpolation/piping, 6-month history retention), scheduled commands (hourly minimum, max 5 per environment, can't be edited in place), queue jobs auto-processed (don't schedule a runner — explicit anti-pattern), 15-minute per-job cap with batched-job pattern for longer work.
- **`skills/craft-cloud/references/plugin-development.md`** — full Cloud-compatible plugin checklist: Craft 4.6+ minimum, asset bundles with alias-based `sourcePath` (no runtime publishing, instantiate without DB access, composer `type: craft-plugin`), `App::isEphemeral()` gating, Path service for transient writes, `Craft::info/warning/error()` for logs (never files), 15-min queue budget with `BaseBatchedJob`, **mandatory `csrfInput()` function** (raw token output can leak tokens across users behind the edge cache), cookie-free design on cacheable requests, auto-handled `sendContentAsFile()`, asset-select preference over direct uploads, "Tested on Craft Cloud" badge.
- **`skills/craft-cloud/references/migration.md`** — self-hosted → Cloud cutover sequence: pre-migration audit table (Craft version, MariaDB, table prefix, custom `db.php`, local filesystems, third-party S3 plugins, mail adapter, ImageOptimize / Imager-X, `.htaccess`, custom queue runners, scheduled cron, forked repos, file-based logging), Phase 1 code/config, Phase 2 DB export/import per engine, Phase 3 asset sync via `aws s3 sync`, Phase 4 deploy + verify on preview URL, Phase 5 DNS cutover with maintenance mode, rollback path (DNS-only — no in-platform timeline fork), post-migration cleanup.
- **`skills/craft-cloud/references/local-dev.md`** — DDEV recipe matching Cloud's PHP/DB versions, the Cloud extension's local no-op behavior (leave it installed), `CRAFT_DB_*` env-var pattern instead of `db.php`, database restore commands per engine, optional `CRAFT_EPHEMERAL=true` for testing ephemeral code paths locally, what *not* to mirror locally (edge caching, edge transforms, queue auto-processing).
- **`skills/craft-cloud/references/limitations.md`** — documented unsupported features (consolidated from compatibility + quotas + FAQ), force-enabled settings (`asyncCsrfInputs`), runtime caps (60s web timeout, 6MB response, 200MB upload, 15-min build/CLI/queue), plan quotas (Team: 2 envs / 10GB / 250GB; Pro: 3 envs / 20GB / 500GB), **authored-content gaps clearly marked as community knowledge**: mail recommendations (Postmark, SES, SendGrid, Resend, plain SMTP), log strategy (Console output is the de-facto surface; route to external service via Monolog for persistent ops logs), per-PR preview workarounds, rollback pattern, plugin compatibility matrix (ImageOptimize: don't use; Imager-X: don't use for transforms; Blitz: redundant; SEOmatic, Sprig, Formie, CKEditor, Commerce, Typesense/Algolia: work; Freeform, Schematic, file-writing plugins: verify).

### Changed

- **`skills/craftcms/SKILL.md`** — added `craft-cloud` to the Companion Skills list with auto-load condition (`craft-cloud.yaml` at repo root or `craftcms/cloud` in `composer.json`). Added four task examples to the routing list ("Make a plugin Cloud-compatible", "Deploy a Craft project to Cloud", "Migrate a self-hosted Craft site to Cloud", "Why does my plugin's file write silently fail on Cloud?").
- **`skills/craft-site/SKILL.md`** — same companion-skill addition, framed for front-end concerns (edge caching, ESI, transform constraints, `csrfInput()` requirement).
- **`skills/craft-project-setup/SKILL.md`** — Cloud detection added in both signal lists: `craft-cloud.yaml` at repo root under Project Structure Signals, and `craftcms/cloud` in composer.json under Dependency Detection. The "Step 2: Ask clarifying questions → For all types" section now also asks about the hosting target when neither signal is present, so fresh projects planning to deploy to Cloud (before `craft-cloud.yaml` exists) get the Cloud context baked into the generated CLAUDE.md instead of needing a second setup pass. Generated project CLAUDE.md loads `craft-cloud` as a companion whenever Cloud is the detected or chosen hosting target.
- **`agents/craft-code-reviewer.md`** — new "Cloud compatibility" review section, conditional on three detection signals (`craft-cloud.yaml`, `craftcms/cloud` in composer.json, or "Hosted on Craft Cloud" in project CLAUDE.md). Severity-tagged checks mapped from the new skill's `plugin-development.md` checklist: Critical (raw CSRF token output → token leakage via edge cache, runtime asset publishing, `tablePrefix` in config, MariaDB references, unwrapped `db.php`), Important (file writes without `App::isEphemeral()`, asset bundles with hardcoded `sourcePath`, asset bundles with DB access in `init()`, file-based logging, queue jobs without batching for large datasets, redundant scheduled queue runner), Suggestion (cookies/sessions on cacheable requests, `.htaccess` in repo, `devMode`/`allowAdminChanges` in production-equivalent config, hardcoded `sendmail`). The section is skipped silently for self-hosted projects so the checks don't generate noise on Forge/Servd/bare-metal reviews.
- **`skills/craftcms/references/deployment.md`** — expanded the one-line Craft Cloud row in the hosting-platforms table into a pointer to the new skill, noting that none of the patterns in `deployment.md` apply directly because Cloud's pipeline is structurally different.
- **`skills/craftcms/references/migrations.md`** — cross-references to the new skill on the two existing Cloud mentions (the `TRUNCATE cache` pitfall and the "applies to every deployment" framing).
- **`skills/craftcms/references/console-commands.md`** — expanded the `craft setup/cloud` row to point at `craft-cloud` skill's `extension.md` and `migration.md`.
- **`skills/craft-site/references/plugins/image-optimize.md`** — the existing "Don't use ImageOptimize on Cloud" pitfall now cross-references the new skill's transform-limits and plugin-compat sections.
- **`skills/craft-site/references/image-presets.md`** — cross-reference to the new skill in the Cloud-transforms strategy row.
- **`README.md`** — added `craft-cloud` row to the skills table; updated counts from "8 skills, 86 reference files" to "9 skills, 117 reference files"; updated docs-table line.
- **`docs/skills-overview.md`** — added full `craft-cloud` section between `craft-project-setup` and "Skill Boundaries at a Glance"; updated headline count.
- **`.claude-plugin/plugin.json`** and **`.claude-plugin/marketplace.json`** — descriptions updated to mention Craft Cloud and "9 skills"; marketplace keywords now include `craft-cloud` and `serverless-hosting`.

## 1.5.2 -- 2026-05-21

Documents Craft's reserved CP DOM IDs — a footgun surfaced from a real plugin build where a tab pane defined as `<div id="notifications">` collided with Craft's toast container (`<div id="notifications" role="status">`). Craft's CP JavaScript caches chrome refs via `$('#foo')` during `Craft.CP` init and returns the first match in DOM order, so a plugin element reusing one of these IDs silently hijacks notification toasts, ARIA modal masking, or tab/layout wiring. The result is "not quite Craft" symptoms — toasts that stop appearing, modal screen-reader isolation that leaks, panes that render in the wrong layout region — without any error to grep for. Verified against `craftcms/cms@5.10` (`src/web/assets/cp/src/js/CP.js`, `src/templates/_layouts/cp.twig`, `src/web/assets/garnish/src/Garnish.js`).

### New

- **craftcms / cp.md — "Reserved DOM IDs" section.** Categorized list of every `#id` Craft's CP JavaScript looks up directly, grouped outer-to-inner to match the CP layout flow: Layout regions, Notifications & a11y, Global header & nav, Page header, Content pane, Sidebar / details, Footer. Documents the failure mode (`$('#foo')` returns the first DOM match), the symptoms, and the "how to apply" rule for tab keys, pane containers, and slideout/HUD roots. Includes a wrong/right code example for tab-key naming and a cross-reference to Garnish's modal background masking (`hideModalBackgroundLayers()`'s `.not('#notifications')` exception is exactly why `#notifications` is reserved).
- **craftcms / cp.md — Common Pitfalls entry + tab-key callout** on the Anchor-based tabs subsection. Surfaces the rule at the two most likely entry points so a reader picking tab keys or scanning the pitfalls list sees the warning before hitting the section.
- **craft-garnish / integration.md — Common Pitfalls entry.** Brief warning for plugin CP-JS authors that `Craft.CP` caches chrome refs by ID during init; points at the canonical list in `craftcms/cp.md`.
- **craft-garnish / utilities.md — ARIA & Focus Management note.** Explains why `Garnish.hideModalBackgroundLayers()` excludes `#notifications` from its mask, and the consequence for plugin authors: a body-level plugin element with `id="notifications"` also escapes the mask, breaking the modal's screen-reader isolation.

### Changed

- **craftcms / cp.md — `asCpScreen()` tabs example.** Renamed the example tab keys from `content` / `settings` to `itemContent` / `itemSettings`. `#content` is itself a reserved CP DOM ID (the main content pane), so the previous example demonstrated exactly the collision the new Reserved DOM IDs section warns against.

## 1.5.1 -- 2026-05-18

Correctness patch for v1.5.0. The new Deletion Blockers section and the `heading()` Twig helper documentation shipped with API signature errors — verified against `craft/cms@5.10.1` source after the fact. Code examples in those sections would have failed at runtime if a reader copy-pasted them. This patch fixes the signatures, framings, and a small consistency issue around the `Craft.cp` JS singleton.

### Fixed

- **craftcms / elements.md — Deletion Blockers section.** Rewrote the three code examples and surrounding prose to match the actual upstream API:
  - `deletionBlockers()` is a **static** method taking `(ElementCollection $elements, bool $hardDelete)` — was documented as an instance method using `$this->id`. The override pattern now correctly uses `parent::deletionBlockers($elements, $hardDelete)` and operates on the passed collection.
  - `RelationDeletionBlocker` constructor is positional `(string $sourceElementType, ElementCollection $elements, bool $hardDelete, array $config = [])` — was documented as taking a config array with keys `element`/`count`/`message`. The blocker computes `relationCount` internally in `init()`; no manual count is passed. The new example uses named-argument syntax for readability.
  - `EVENT_DEFINE_DELETION_BLOCKERS` listener — was accessing `$event->sender` for the element under deletion, but `$event->sender` is the **class name** for static-context events. Corrected to use `$event->elements` (the `ElementCollection`) and `$event->hardDelete` (the bool flag).
  - New "Method Signature" subsection up front clarifies the static-method shape before the worked examples land.
- **craftcms / elements.md — `ElementHelper::belongsToCanonicalOwner()` signature.** Was documented as `(ElementInterface $element): bool`; actual signature is `(NestedElementInterface $element, ElementInterface $owner): bool` — two args, first is `NestedElementInterface`. Updated the description to match the actual semantics: "true when `$element`'s primary owner is `$owner` (or `$owner`'s canonical version)."
- **craft-twig-guidelines / SKILL.md — `heading()` helper.** Rewrote the section. Was documented as "auto-incrementing" with `heading('Page title', { class: '...' })` examples — neither was correct. Actual signature is `headingFunction(int $level, array|string $attributes = '')`; the first argument is an **explicit int level** (1-6), not a tracked counter. Verified against PR #18524 description and `craft/cms@5.10.1` `src/web/twig/Extension.php`. Corrected examples use `heading(2, 'Section title')` and the bound shortcuts `h1()…h6()` that only take attributes. Removed the false "tracks the current heading level" framing.

### Changed

- **craftcms / cp-components.md — `Craft.CP` → `Craft.cp` consistency.** The Queue Completion Event paragraph mixed `Craft.CP` (prose) and `Craft.cp` (code example). Source consistently uses `Craft.cp` (the singleton instance); `Craft.CP` is the class definition. Both prose and code now use `Craft.cp`.
- **craftcms / elements.md — Contents TOC.** Added the missing entries for `5.10 Element Query and Save Utilities` and `Deletion Blockers (5.10+)` sections that landed in 1.5.0 without making it into the file's own TOC.
- **craftcms / elements.md — Renamed `5.10 Element Additions` section to `5.10 Element Query and Save Utilities`.** Disambiguates from the much larger `Deletion Blockers (5.10+)` section further down the file. The smaller section is plumbing utilities; the larger one is a substantive subsystem.

## 1.5.0 -- 2026-05-15

Opens the 1.5.x line — the Craft 5.10 realm — per the versioning policy that landed alongside this release (see `README.md` → Versioning). This is the Craft 5.10 + CKEditor 5.x ecosystem catch-up: the new deletion-blocker subsystem, Twig 3.24 surface, `SecFetchSiteFilter` CSRF alternative, `DefaultableFieldInterface`, element-query and CP-JS additions, and a full CKEditor plugin 5.x reference rewrite covering plugin 5.0.0 through 5.6.0. The CKEditor 5.0.0–5.5.0 content is also on 1.4.x (cherry-picked into 1.4.9) since it works on Craft 5.9; the plugin 5.6.0 reference-deletion-blocker integration is 1.5.x-only because it requires Craft 5.10. Craft 5.10 also carries security fixes (one high-severity RCE, two moderate) — upgrading production sites is the right call.

### New

- **README.md → Versioning section** + **bin/release.sh policy comment**. Documents the minor-version-mirrors-Craft-minor mapping (1.4.x = Craft 5.9 realm, 1.5.x = Craft 5.10, 1.6.x = 5.11, etc.), the dual-maintenance commitment for both lines, the `1.4.x` branch convention, and the cherry-pick workflow for cross-line content. `bin/release.sh` now prints the current branch in its "git push" hint (was hardcoded `main`) — important now that releases tag from multiple branches.
- **craftcms / elements.md — "Deletion Blockers (5.10+)" section.** Covers the new subsystem end-to-end: implementing `deletionBlockers()` on your own element (with `RelationDeletionBlocker` example), hooking `Element::EVENT_DEFINE_DELETION_BLOCKERS` to register blockers on third-party elements (worked `User` example), extending `BaseDeletionBlocker` for custom blocker classes, the bulk reassignment primitive (`Entries::reassignEntries()`), and the `ReplaceRelations` queue job. Closes with the deprecation list — `UsersController::EVENT_DEFINE_CONTENT_SUMMARY`, `DefineUserContentSummaryEvent`, `User::$inheritorOnDelete`, `DeleteUsers` action, `Craft.DeleteUserModal` JS — and the migration path: move any user-deletion content summaries to the new element-type-agnostic event.
- **craftcms / controllers.md — "Sec-Fetch-Site Filter (5.10+)" section.** New `craft\filters\SecFetchSiteFilter` Yii `ActionFilter` for opt-in `Sec-Fetch-Site` origin verification on non-safe methods. Covers attachment via `behaviors()` with action scoping, the `$originOnly` / `$allowSameSite` / `$safeMethods` defaults, when to use it (internal AJAX endpoints) and when not (webhook endpoints, non-browser API clients). Framed as a supplement to CSRF, not a replacement.
- **craftcms / field-types-custom.md — "Defaultable Fields (5.10+)" section.** Documents `craft\base\DefaultableFieldInterface` and its single `getDefaultValue(): mixed` method, paired with the new `--to-default` flag on `resave/*` console commands. Includes the operator invocation (`ddev craft resave/entries --to-default --with-fields=…`) and a clarification on when to implement it (existing-element backfills only — `normalizeValue()` still handles new-element initialization).
- **craftcms / cp-components.md — slideout reload + queueCompleted event.** New `Craft.CpScreenSlideout::reload()` method that re-fetches a slideout's HTML in place (used internally for cross-tab edit sync; also useful after async work that mutates the element). New `Craft.CP` `queueCompleted` event that fires when the last running queue job finishes — useful for CP screens that want to refresh themselves after long-running batch jobs (resave, propagation, import).
- **craftcms / elements.md — "5.10 Element Additions" section.** Covers `ElementQueryInterface::collectIds(): Collection` (Laravel-style chainable counterpart to `ids()`), `ElementInterface::setDirtyFieldTracking(bool)` (for programmatic saves where dirty-tracking side effects need to be suppressed), `ElementHelper::belongsToCanonicalOwner()`, and `ElementActionInterface::getTriggerId()`.
- **craft-twig-guidelines / SKILL.md — Twig 3.24 surface.** Flipped the nullsafe operator rule (Craft 5.9 carried Twig 3.21 which didn't support `?.`; Craft 5.10 carries Twig 3.24 which does — use it for deep chains, not single-property access). New `heading()` / `h()` / `h1-h6()` subsection for auto-incrementing heading helpers in composable layouts. New "Filter Additions" subsection covering `|number locale`, `|time/datetime withTimeZone`, and `|timestamp` returning "now" for null/empty. `tag()` second-argument string shortcut noted inline.
- **craftcms / graphql.md — Craft 5.10 Additions section.** `delete*` mutations now accept a `hardDelete: Boolean` argument (default `false`) that bypasses soft-delete. Assets' `url` field's `immediately` argument is no longer deprecated — that earlier deprecation was reversed in 5.10.
- **craft-content-modeling / SKILL.md — `Section::$minAuthors`.** New section property (default 0) — enforces a minimum number of authors per entry. Combine with `maxAuthors` to define an exact range. Validated on save; `minAuthors > maxAuthors` is rejected.
- **craft-site / plugins/ckeditor.md — major rewrite for plugin 5.0.0–5.6.0.** Field Settings table enumerating every settable property (`$toolbar`, `$headingLevels`, `$imageMode`, `$imageEntryTypeUid`, `$imageFieldUid`, `$advancedLinkFields`, `$fullGraphqlData`, `$jsFile`, `$cssFile`) + `getJson()`/`setJson()` accessors. New sections for: Config as Files (5.3.0+), Image Mode (5.0.0+, `IMAGE_MODE_IMG` vs `IMAGE_MODE_ENTRIES` + drag-and-drop upload), Link Configuration (5.0.0+ rebuilt modal + `$advancedLinkFields`), GraphQL Mode (`$fullGraphqlData`, `CkeditorData` vs `CkeditorMarkup` — actually 4.8.0 but previously undocumented), Fullscreen Toolbar Item, Value Helpers (`FieldData::getEntries()`, `Markup::getMarkdown()`, `Markup::getPlainText()` — also 4.8.0). The "Extending with Custom Plugins" section is a full rewrite for the **breaking** ES-module registration pattern in 5.0.0 (`BaseCkeditorPackageAsset::$namespace`, `CkeditorConfig::registerPackageAsset()`). The 5.0.0–5.5.0 portion of this rewrite is also on 1.4.x via cherry-pick (v1.4.9).
- **craft-site / plugins/ckeditor.md — "Reference Deletion Blocker (5.6.0+ — requires Craft 5.10)" section.** Plugin 5.6.0 hooks into Craft 5.10's deletion-blocker subsystem via `craft\ckeditor\deletionblockers\ReferenceDeletionBlocker` and a new `ckeditor_references` table. Documents the required upgrade step: `ddev craft resave/all --with-fields=…` to backfill the references table after upgrading. Also covers the `removePlugins` config being respected as of 5.6.0 (silently ignored before). 1.5.x-only section.

### Changed

- **craftcms / elements.md — Common Pitfalls (5.10 breaking shapes).** Three new entries: `PopulateElementEvent::$row` no longer carries `fieldValues` / `generatedFieldValues` (moved to new `$content` property — silent breakage for any handler reading those keys); entry `postDate` no longer auto-set to `dateCreated` (null until saved as enabled — sites filtering on `postDate :notempty:` see different behavior); relation-field queries now respect the parent query's target sites (cross-site relation queries need explicit `->site('*')`).
- **craftcms / controllers.md — Common Pitfalls.** New entry: `AppController::actionResourceJs()` is removed in 5.10. Plugins that loaded JS through the cross-domain proxy must migrate to normal asset bundles.
- **craft-twig-guidelines / SKILL.md — `is empty` / `|default` on Models pitfall.** Craft 5.10 treats any `yii\base\Model` as non-empty regardless of property values. Means `{% if entry is empty %}` is always false and `{{ user|default('Guest') }}` always renders the user object. Check specific properties: `{% if entry.title is empty %}`.
- **craftcms / console-commands.md — `--to-default` resave flag.** Added to the common resave flags list.
- **agents / craft-site-builder.md — nullsafe rule flipped.** Was "Never `?.`" (correct for Craft 5.9 / Twig 3.21); now "`?.` is available on Craft 5.10+ — use it for deep chains, not single-property access."

## 1.4.8 -- 2026-05-15

Tightens the plugin-class conventions added in 1.4.7 after they surfaced gaps in a real plugin review. Three additions: a hard prohibition on shipping `src/Plugin.php` / `class Plugin` (with the multi-plugin-source-tree rationale that makes it not just a style nit), the `assert($component instanceof Type)` narrowing pattern on service getters (required for PHPStan level 8 since Yii's `Component::get()` returns `?object`), and a "trait owns the `@property` map, main-class docblock describes responsibility" rule that prevents the drift mode where a docblock says "wires three services" while the code has nine. Also: a code-reviewer file-organization checklist so these conventions get caught at review time instead of slipping through.

### New

- **craftcms / architecture.md — Plugin Class Structure additions.** "Renaming an Existing Plugin" subsection with the mechanical migration recipe (`git mv`, sweep references with `grep -rln`, update `composer.json` `extra.class`, run PHPStan as safety net) for plugins that shipped with `src/Plugin.php`. The Trait Split worked example now shows the `assert($component instanceof Xxx)` pattern in each getter with an inline explanation of why it's load-bearing — Yii's `Component::get()` is declared `?object`, so PHPStan level 8 can't resolve `getItems(): Items` without the assertion. The main-plugin-class example now carries a class-level docblock that describes the plugin's responsibility ("Forum — discussion threads, posts, and moderation for Craft 5") rather than enumerating services, with the rationale that any service list in the docblock drifts the moment a service is added or removed. Explicit "no `@property-read` tags on the main class — one source of truth, the trait" rule added.
- **agents / craft-code-reviewer.md — "File organization (PHP plugins)" section** between access-control checks and Twig checks. Seven bullets with severity tags: any `src/Plugin.php` in diff → Critical; file/class name disagreeing with `composer.json` `extra.class` → Critical; services accessed via `@property-read` on the main class instead of through a `ServicesTrait` → Important; getters without `assert($component instanceof Type)` → Important (fails PHPStan level 8); duplicate `@property-read` on main class when the trait already declares `@property` → Suggestion; main-class docblock that enumerates services → Suggestion; `init()` longer than ~20 lines wiring events directly → Important.

### Changed

- **craftcms / architecture.md — Entry Class Naming rationale strengthened.** Promoted the "rename `Plugin.php`" guidance from a passive instruction to a hard rule with explicit framing: "Never ship a plugin as `src/Plugin.php` / `class Plugin`" plus the multi-plugin-source-tree explanation (every plugin's main class would otherwise be `Plugin`, distinguished only by namespace alias — ambiguous, grep-unfriendly). Previously the rule was buried in a single sentence; now it leads the subsection with rationale.
- **craftcms / plugin-vite.md — VitePluginService example aligned.** The `### 3. ServicesTrait Registration` worked example now uses the same trait pattern as the new architecture-doc example: `@property VitePluginService $vite` on the trait docblock, a typed `getVite(): VitePluginService` accessor with `assert($component instanceof VitePluginService)` narrowing. Cross-link added back to `architecture.md → Plugin Class Structure` for the full rationale.
- **project-template + plugin-template rules.** Both `scaffolding.md` and `architecture.md` variants updated to surface the three new rules in bullet form: the "never `src/Plugin.php`" framing with rationale, the `assert()` narrowing requirement on getters, the "trait owns `@property` tags" rule, the 2+ services threshold for adopting the trait, and the "main-class docblock describes responsibility, not services" rule.

## 1.4.7 -- 2026-05-13

Closes two scaffolding gaps that surfaced during a real plugin build, and runs a vendor-neutrality audit across the skills. The scaffolding gaps: the plugin entry-class naming convention (`src/Plugin.php` / `class Plugin` from the Craft generator doesn't match what any shipped plugin uses — the file and class should match the handle in PascalCase) and the `ServicesTrait` / `PluginTrait` split that keeps the main plugin class a thin orchestrator instead of accumulating `_register*` wiring inline. Both conventions are visible in every shipped Craft plugin but weren't documented anywhere a scaffolding pass would inherit them. The audit pass distinguishes load-bearing vendor mentions (composer-package detection rules, dedicated plugin reference files, FQN class references) from gratuitous ones, and strips the gratuitous ones.

### New

- **craftcms / architecture.md — "Plugin Class Structure" section** added before "Services" in the TOC. Entry Class Naming subsection documents the handle-in-PascalCase rule (`forum` → `Forum.php` / `class Forum`; `userProfile` → `UserProfile.php` / `class UserProfile`), the `composer.json` `extra.class` requirement, and the explicit rename step away from the generator's default `src/Plugin.php`. Trait Split subsection covers `src/services/ServicesTrait.php` (producer-side: `static config()` + typed `getX(): X` accessors + `@property X $name` docblocks for PHPStan/IDE magic-property typing) and `src/base/PluginTrait.php` (private `_register*` methods plus `getSettingsResponse()`, `getReadOnlySettingsResponse()`, `createSettingsModel()` lifecycle overrides), with both the trait body skeleton and a consumer-side plugin class as worked examples. The standalone `### Registration via ServicesTrait` subsection that used to live under `## Services` was folded in — redundant once the new section covered the producer side.
- **project-template + plugin scaffolding rules — entry-class and file-placement rules** added to both `.claude/rules/scaffolding.md` variants. Three rule clusters: rename the generator's default `Plugin.php` and `composer.json` `extra.class` to match the handle, place new services in `src/services/` with their typed getters in `ServicesTrait::config()`, and route new event listeners / URL rule registration / plugin lifecycle overrides through `src/base/PluginTrait.php` so the main plugin class stays a thin shell.

### Changed

- **project-template + plugin architecture rules — ServicesTrait/PluginTrait bullets.** The two new bullets in `.claude/rules/architecture.md` (both variants) were trimmed: dropped the `craft\services\Plugins::createPlugin()` source-tree reference and the reference-implementations tail. Each bullet is now one sentence at ~25 words, matching the rest of the file's density. The mechanism details live in the craftcms skill — project rules stay terse.
- **project-template / CLAUDE.md plugin structure tree.** Entry-point line was inconsistent with the new rename rule — it still showed `Plugin.php` even after `scaffolding.md` told the reader to rename it. Updated to `Forum.php  # Entry point — class name matches the plugin handle in PascalCase`.
- **Vendor-neutrality audit.** Stripped gratuitous vendor mentions where the rule could be expressed abstractly: `craft-php-guidelines / naming-conventions.md` example import aliases (`craftpulse\myplugin` → `vendor\myplugin`); `craft-php-guidelines / class-organization.md` alphabetical-import-ordering example (`craft\…` < `craftpulse\…` < `Twig\…` → `craft\…` < `vendor\…` < `Twig\…`); `craftcms / cp-ui-patterns.md` warning-parameter rule no longer cites "Blitz uses this pattern extensively" as its credential; `project-template / testing.md` dropped the "Reference implementation: `putyourlightson/craft-blitz` tests" pointer. Load-bearing vendor mentions kept as-is: composer-package detection rules (the `???` operator detection for `nystudio107/craft-empty-coalesce` / `craft-seomatic`, the project-setup dependency-detection table), dedicated plugin reference files (`craft-site/references/plugins/*.md`, `craftcms/references/plugin-vite.md`, `craft-site/references/vite-buildchain.md`), and FQN class references in third-party integration guides. The audit kept what was data and stripped what was shoutout.

## 1.4.6 -- 2026-05-13

Closes a recurring plugin-development gap: `Install.php` edits silently fail to land in `db_test` after the first test run, because custom Pest bootstraps short-circuit on "plugin already installed." Migrations propagate (their state lives in the `migrations` table); Install.php-only edits don't. The symptom — a test passing against a stale schema until someone manually recreates `db_test` — is asymmetric and easy to miss, especially during early plugin development when "there are no users yet, I'll just edit fresh-install shape" feels safe.

### New

- **craftcms / testing.md — "Schema migrations and db_test drift" subsection** under Pest Setup. Explains the mechanism (custom bootstrap's "skip if installed" check is the standard speed trade-off; consequence is `Install.php::safeUp()` only runs once per `db_test` lifetime). Documents the two paths: migration-driven (canonical — every schema change ships in BOTH `Install.php` AND a dated idempotent migration, same pattern downstream users need) and test-DB reset (escape hatch for one-off cases, brittle as a recurring discipline). Verification procedure (drop `db_test`, recreate, run Pest — if a test passes against installed-db but fails against fresh, the migration is the regression). Explicit anti-pattern call-out: don't drop `db_test` on every test run (slow, breaks parallel workers, masks the actual drift problem).
- **craftcms / testing.md — Common Pitfalls bullet.** One-line entry surfacing the symptom ("Install.php edits silently fail to land in `db_test` after the first install") so it's grep-able when scanning the pitfalls list. Points at the new subsection for the durable fix.
- **craftcms / migrations.md — "Schema-change discipline" paragraph** under the Install.php description. Cross-links to the testing.md section so someone editing Install.php for a schema change sees the pointer at the source location. Frames the rule: every schema change lands in BOTH `Install.php` (canonical fresh shape) AND a dated migration (idempotent upgrade), because editing only Install.php strands every existing install (including db_test) on the prior schema.

## 1.4.5 -- 2026-05-13

Closes a costly skill gap surfaced from a real plugin build: the boundary between `settingsHtml()` and a custom settings controller. The two patterns aren't interchangeable — `settingsHtml()` returns HTML inside a wrapper that doesn't set `tabs`, so tabs in plugin settings require leaving `settingsHtml()` for a controller-driven pattern with a template extending `_layouts/cp` directly. Includes the full controller skeleton, URL rules, template shape, and the `$hasReadOnlyCpSettings` gotcha that bites the moment `getSettingsResponse()` is overridden.

### New

- **craftcms / cp.md — "Choosing the pattern" decision rubric** at the top of Settings Pages. Single-pane settings → `settingsHtml()`; tabs / multi-section / custom non-save actions → `getSettingsResponse()` redirect → custom controller → template extending `_layouts/cp`. Explains the structural reason: the wrapper template (`vendor/craftcms/cms/src/templates/settings/plugins/_settings.twig`) extends `_layouts/cp` but never `{% set tabs = ... %}`, and `_layouts/cp.twig` reads `tabs` from its own rendering context — your `settingsHtml()` output lives in `{% block content %}`, too late to inject the variable. Names the failure mode explicitly so the reader doesn't waste hours retrofitting tabs into `settingsHtml()`.
- **craftcms / cp.md — "With tabs or custom actions: redirect to your own controller" subsection.** Full canonical pattern: `Plugin::$hasCpSettings = true`, `Plugin::$hasReadOnlyCpSettings = true` (required when overriding `getSettingsResponse()` — `Plugin::init()` only auto-detects read-only support for the default implementation), `getSettingsResponse()` redirect to `UrlHelper::cpUrl('my-plugin/settings')`, `UrlManager::EVENT_REGISTER_CP_URL_RULES` mapping plugin handle and `/settings` to `/settings/edit`, `SettingsController` extending `craft\web\Controller` with `requireAdmin(false)` view (read-only-accessible) + strict `requireAdmin()` save, `settings[xxx]` body-param shape so `savePluginSettings($plugin, $settings->toArray())` persists the full model (sidesteps the existing Split Settings footgun). Template skeleton extends `_layouts/cp` directly, sets `tabs` + `selectedTab`, uses `fullPageForm = true`, panes are `<div id="X"> [class="hidden"]`.
- **craftcms / cp.md — "Don't include `_includes/tabs.twig` directly" call-out** added to the existing Tabbed Settings Pages → Twig-level tabs subsection. Names the failure mode: the partial is a private helper that `_layouts/cp.twig` calls internally from the `tabs` variable in its own context; including it manually produces markup but no JS wiring, no ARIA controller setup, no per-tab error highlighting. The fix is always to `{% extends "_layouts/cp" %}` and `{% set tabs = ... %}`.
- **craftcms / SKILL.md — routing entry** for "Add tabs to a plugin's settings page" → `cp.md` (Settings Pages → With tabs or custom actions), with a one-line hint that `settingsHtml()` is single-pane only — so the entry triggers on the symptom (someone asking about plugin-settings tabs) even before the cp.md content is loaded.

## 1.4.4 -- 2026-05-12

Plugin shipping completeness for Craft 5 plugins — the two-workflow GitHub Actions pattern (`code-analysis` + `create-release`) the doc was missing, plus expanded PHPStan setup with `craftcms/phpstan` specifics and the Composer advisory-blocking gotcha. Also: a reviewer-heuristic tightening to stop generic framework intuitions from masquerading as Craft runtime bugs.

### New

- **craftcms / architecture.md** — New "Settings Lifecycle (Plugins)" subsection alongside the existing Settings Model section. Documents the actual mechanics of plugin settings resolution: merging happens in `craft\services\Plugins::createPlugin()` (project config + `config/{handle}.php` overrides) *before* the plugin object is constructed; Yii then applies the merged array via `setSettings()` during construction; `Plugin::getSettings()` returns the memoized model for the rest of the request. The user-visible consequence: capturing `$settings` outside an event closure registered from `init()` is equivalent to resolving inside the closure — same merged model, same values. Includes an explicit guardrail against the Laravel/Symfony "always resolve inside the closure" heuristic, which doesn't translate to Craft's Yii2 module model.
- **craftcms / quality.md** — Expanded `craftcms/phpstan Package` section with verified specifics from the upstream extension: the `BaseYii.stub` declaration of `Craft::$app` as the non-nullable union `\craft\web\Application|\craft\console\Application`, the `scanFiles` list (`Craft.php`, `Yii.php`, Twig `CoreExtension.php`), and the `earlyTerminatingMethodCalls` for `Craft::dd` / `Application::end` / `ErrorHandler::convertExceptionToError`. Replaces the previous vague bullet list. Also documents the failure mode of hand-rolled `scanFiles` configs (silently pass locally, fail on fresh CI install).
- **craftcms / quality.md** — New "Why `treatPhpDocTypesAsCertain: false`" subsection explaining when the knob is actually needed: defensive `Craft::$app instanceof WebApplication && !Craft::$app instanceof ConsoleApplication` guards in code that may run in unit tests bypassing the full app boot, or in very early bootstrap. Without the rationale, the setting (which was already in the example) read as cargo-cult.
- **craftcms / quality.md** — New `create-release.yml` workflow documentation under CI/CD Integration. Covers the Craft Console `repository_dispatch` → `ncipollo/release-action@v1` pattern: trigger event `craftcms/new-release`, the `client_payload` fields (`version`, `notes`, `latest`, `prerelease`, `tag`) populated from the Craft Console release form, `contents: write` permission requirement, and why no Composer install or test run belongs in this workflow.
- **agents/craft-code-reviewer.md** — New Rules entry telling the reviewer not to fabricate runtime bugs from generic framework intuitions. Claims about state staleness, DI timing, capture-vs-resolve, or cache lifecycle must trace through Craft's actual source (read `cms/vendor/craftcms/cms/src/` to confirm). Patterns from Laravel/Symfony service containers don't translate to Craft's Yii2 module model where plugin settings are merged once at construction and memoized. When uncertain, downgrade to Suggestion with "Verify:" framing rather than Important/Critical.

### Changed

- **craftcms / quality.md — PHPStan Levels Reference table.** Added level 10 row (PHPStan 2.0+ — stricter mixed handling including implicit mixed from missing types) and noted `--level max` as the alias for the highest level. Refined the recommendation paragraph: level 5 stays as the Craft community baseline, but the noise/value tradeoff above 5 is now framed in terms of magic getters on Yii Components, and the previous "raise to 6-8" range is replaced with a note that 8 buys real null-strictness value while 9-10 push into thin-margin territory on plugin code.
- **craftcms / quality.md — CI/CD Integration section.** Restructured around the two-workflow plugin pattern (`code-analysis.yaml` + `create-release.yml`) instead of a single quality workflow. The `code-analysis.yaml` example now matches the production-shipped craft-tailwind shape: PHP 8.2/8.3/8.4 matrix, `pull_request` + `push` + `workflow_dispatch` trigger, `composer install --no-blocking` (with `--no-security-blocking` documented as the deprecated alias still working on older Composer), `composer phpstan` / `check-cs` / `test` script invocations instead of direct `vendor/bin/*`. Notes section explicitly calls out the Composer 2.5+ advisory-blocking behaviour, the relevant Craft 5.9.x transitive advisories (`yii2 2.0.54` CVE-2026-39850, `webonyx/graphql-php 14.11.10` CVE-2026-40476-class), and why `--no-audit` is not a valid substitute for `--no-blocking` (different scope).

## 1.4.3 -- 2026-05-11

Skill gaps closed from real plugin development sessions — PHP guidelines accuracy (validator shapes, import ordering, PHPStan typing), queue job error handling, controller streaming responses. Plus: marketplace description trims for three skills so they fit under Claude Code's listing cap, and yii2-redis 2.1 breaking-change docs for Craft Redis configs.

### New

- **craft-php-guidelines / templates-and-patterns.md** — New "Inline Validators" subsection. Use string method name form (`[['attr'], 'validateAttr']`), not `[$this, '_validateFoo']` callable arrays or inline closures. Matches `craft\models\Section`, `craft\models\EntryType`. Validator methods are public, no underscore — Yii invokes by name.
- **craft-php-guidelines / naming-conventions.md** — New "Visibility Exception: Yii-Invoked Methods" section. Methods that Yii invokes by name (validators, event handlers, behavior callables, `when` predicates) are public with no underscore prefix, even if they feel internal. Explicit carve-out from the general private-underscore rule.
- **craft-php-guidelines / tooling.md** — New "PHPStan and Craft::$app" subsection. `Craft::$app` inherits Yii's base union type which doesn't expose `ApplicationTrait` methods. Narrow with a typed local (`/** @var \craft\web\Application $app */`). Patterns for web-only, console-only, and both contexts. Don't `@phpstan-ignore-line`.
- **craft-php-guidelines / class-organization.md** — New "Shared Constants — Visibility and Ownership" section. Constants whose value is part of an external contract (hash inputs, sentinels, algorithm names) must be `public const` on the owning service, referenced as `OwnerService::CONSTANT_NAME` everywhere else. PHPStan can't catch cross-file `private const` drift.
- **craftcms / testing.md** — New "Loading \Craft and \Yii without booting the app" subsection. `\Craft` and `\Yii` are global classes outside PSR-4 maps — must be `require_once`'d in test bootstrap for unit tests that don't boot the full application. Without this, Yii validators and `Craft::$app` references fatal.
- **craftcms / queue-jobs.md** — New "Best-Effort Helpers in Queue Jobs" section. When a helper inside `processItem()` is documented as best-effort, its catch block must log and return — not rethrow. Rethrowing causes `BaseBatchedJob` to retry the item, producing duplicate side effects for non-idempotent operations.
- **craftcms / controllers.md** — New "Streaming and Download Responses" section. Three forms in preference order: `asRaw()` for in-memory, stream resource for files, callable closure for lazy generation. The callable must return `[string $data, bool $finished]` — echoing inside the closure corrupts the response.
- **craftcms / config-app.md** — New yii2-redis 2.1+ compatibility callout at the top of the Redis Cache section. Explains the `Can not instantiate yii\redis\ConnectionInterface` bootstrap failure introduced by yii2-redis 2.1.0, which changed `Cache`/`Session`/`Mutex` internal type hints from concrete `Connection` to `ConnectionInterface`. References yii2-redis PR [#276](https://github.com/yiisoft/yii2-redis/pull/276) and the [2.1.0 changelog](https://github.com/yiisoft/yii2-redis/blob/2.1.2/CHANGELOG.md).

### Changed

- **`craftcms`, `craft-site`, `craft-garnish` SKILL.md descriptions** — Trimmed below Claude Code's `skillListingMaxDescChars` cap (1536). Previously 2849 / 1938 / 1753 chars; now 1449 / 1512 / 1466. Cut redundant trigger-keyword pile-ups (e.g. four separate `EVENT_REGISTER_*` / `DEFINE_*` / `BEFORE_*` / `AFTER_*` patterns collapsed to wildcard form, near-duplicate concept/keyword pairs deduplicated). All three negative ("Do NOT trigger for…") clauses now name the sibling skills explicitly (`craft-site`, `craft-content-modeling`, `craftcms`) for clearer cross-skill routing.

### Fixed

- **craft-php-guidelines / class-organization.md** — Import ordering rule corrected from "PHP built-ins first" grouping to flat case-sensitive alphabetical matching ECS's `OrderedImportsFixer`. "PHP globals first" is incompatible with `craft\ecs\SetList::CRAFT_CMS_4` — uppercase PHP globals sort after lowercase `craft\…`. Tooling wins.
- **craftcms / config-app.md** — Added the required `'class' => yii\redis\Connection::class` line to every previously-broken nested `redis` sub-array (Redis Cache snippet, Redis Session snippet, plus the cache and session blocks of the Complete Production Example). Prior snippets relied on yii2-redis defaulting the connection class internally; under 2.1+ the inline arrays must declare it or Yii's DI container can't pick a concrete class to instantiate. The Redis Queue (`proxyQueue`) and Redis Mutex snippets already declared `class` and are unchanged.

## 1.4.2 -- 2026-05-08

Agent PHP surface plus a craft-element-architecture refresh in the `craftcms` skill. The PHP additions unblock [`craftpulse/craft-cortex`](https://github.com/craftpulse/craft-cortex) Phase 1 ship-prep — cortex needed a way to enumerate the bundled agents from PHP so it could surface them as MCP resources alongside the skills.

### Added

- **`Skills::agentNames(): array<int,string>`** — sorted list of agent basenames (without `.md`) under `agents/`. Returns `[]` when the directory is absent.
- **`Skills::hasAgent(string $name): bool`** — existence probe with the same path-traversal validation as the skill probes.
- **`Skills::agentContent(string $name): string`** — full agent markdown (YAML frontmatter + body); throws `\InvalidArgumentException` on missing or unreadable.

### Changed

- **`craftcms` skill — element architecture guidance.** Default to ONE element class with native Structure participation when modelling hierarchies (mirror `craft\elements\Category`), instead of inventing parallel `Foo` + `FooReference` classes. Code-defined field layouts via `defineFieldLayouts()` and `BaseNativeField` subclasses for plugin-owned attributes. Field layout designer vs code-only is now framed as a deliberate design decision with guidance on when each applies, replacing the previous "always suppress designer" advice. Structure sections (post-entrification) get equal billing with Category as canonical structure-aware patterns.

### Fixed

- **Agents** — `bin/install` and the agent definitions use `git -C <path>` instead of `cd <path> && git ...`, avoiding the `untrusted hook` prompt some shells raise on directory transitions.

### Notes

- The `agents/` directory has been on disk and listed in `plugin.json` since v1.0.0 — this release just exposes it through the PHP API. Agent content is unchanged.
- README has a new `Skills::agentNames()` / `agentContent()` example in the PHP-consumers section.
- API addition is additive and forward-compatible. Existing consumers of `Skills::skillNames()` etc. need no changes.

## 1.4.1 -- 2026-05-06

Path-repo development hotfix. Without `branch-alias`, downstream packages declaring `michtio/craftcms-claude-skills: ^1.4` couldn't resolve when installed via a composer path repository — the path repo serves the working tree as `dev-main` (the branch name), and `dev-main` doesn't match `^1.4`. This patch makes path-repo consumers work without sacrificing the symlink-based live dev loop.

### Fixed

- **`composer.json`** — added `extra.branch-alias` mapping `dev-main` to `1.x-dev`. End-users on Packagist are unaffected (they always resolve tagged versions); path-repo developers can now declare `^1.4` constraints against the package and have them satisfied by the working tree.

## 1.4.0 -- 2026-05-06

PHP API for composer consumers. The skills repo now doubles as a composer package (`michtio/craftcms-claude-skills`) exposing the bundled Markdown content through a thin static helper. The primary consumer is [`craftpulse/craft-cortex`](https://github.com/craftpulse/craft-cortex) — a Craft CMS 5 MCP server plugin that surfaces these skills as MCP prompts and resources to AI agents (Claude Code, Cursor, Claude Desktop, anything speaking MCP). The Claude Code skills plugin format is unchanged; this is a parallel consumption path against the same source content. No skills moved or renamed.

### Added

- **`composer.json`** — package manifest. Name `michtio/craftcms-claude-skills`, type `library`, MIT, `php: ^8.2`, PSR-4 autoload `Michtio\CraftCmsClaudeSkills\` → `src/`.
- **`src/Skills.php`** — final, static, read-only helper. Public surface:
  - `skillNames(): array<int,string>` — sorted directory-backed skill names
  - `hasSkill(string $name): bool`
  - `content(string $name): string` — SKILL.md contents; throws `\InvalidArgumentException` on missing
  - `references(string $name): array<int,string>` — sorted reference filenames (no extension); throws on missing skill
  - `hasReference(string $name, string $reference): bool`
  - `referenceContent(string $name, string $reference): string` — reference contents; throws on missing
  - `path(): string` — package root absolute path
  - All name-accepting methods reject path-traversal (`.`, `..`, slashes, null bytes); hidden entries are treated as absent.
- **README** — "For PHP consumers (composer)" section documenting install and a quick `Skills::skillNames()` / `Skills::content('craftcms')` example.

### Notes

- API was validated end-to-end against `craftpulse/craft-cortex` Gate 6 before tagging — every public method is exercised by cortex's prompt and resource registries.
- No caching inside the helper. Consumers layer their own registries.
- No PHPUnit / Pest in this repo; the helper has no logic complex enough to test in isolation, and cortex's integration tests cover every code path end-to-end.

## 1.3.1 -- 2026-05-06

Manifest-sync hotfix. Both `1.2.1` and `1.3.0` shipped with stale `1.2.0` versions in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` — the manifest hadn't been bumped since the v1.2.0 prep work on 2026-04-17. Marketplace surfaces and any plugin metadata scrapers therefore reported `1.2.0` for two releases. This patch corrects all three version sites (`plugin.json` → `version`, `marketplace.json` → `metadata.version` + `plugins[0].version`) and adds release tooling to prevent recurrence.

### Fixed

- **`.claude-plugin/plugin.json`** — `version` now `1.3.1` (was `1.2.0` since 2026-04-17, despite v1.2.1 and v1.3.0 having shipped).
- **`.claude-plugin/marketplace.json`** — `metadata.version` and `plugins[0].version` both now `1.3.1` (same drift).

### Added

- **`bin/release.sh`** — single-command version bump across all three manifest sites + CHANGELOG date stamp. File-only — the developer still reviews the diff and handles the commit / tag / push themselves. Usage: `bin/release.sh <version>`.
- **`.github/workflows/release-validation.yml`** — fires on tag push (`v*`); fails the workflow if `plugin.json` or `marketplace.json` versions don't match the tag. Catches the same kind of drift before a release goes public.

## 1.3.0 -- 2026-05-04

Full CLI command reference (25→80+), CP UI patterns library, feature-first build order (replacing layer-first), full-stack code reviewer (PHP + Twig + JS + CSS), planner research/audit capabilities, permissions generation in project setup, manual testing gates, 6 API gotchas from real plugin development, 3 testing-specific pitfalls, stronger Bash restriction rules, token budget measurement tooling, cp.md split for input token efficiency, output density constraints on all agents.

### New

- **cp-components.md** — New reference file (263 lines). Dashboard widgets, utility pages, slideout editors, ajax endpoints, CP alerts. Split from cp.md to reduce input token cost when loading CP templates for settings/form work.
- **cp-ui-patterns.md** — New reference file (245 lines). Tri-state inheritance, status indicators, field warnings, CSS variables, condition builders, asset bundles, markup patterns. Split from cp.md.
- **evals/measure_tokens.py** — Token budget measurement script. Counts tokens per file using tiktoken cl100k_base, reports per-skill totals, agent costs, and load scenarios. Run: `uv run --with tiktoken python3 evals/measure_tokens.py`. Supports `--json` for tracking over time.
- **element-index.md** — New "Status Pills in Table Attributes" section: `Cp::statusLabelHtml()` with `Color` enum, the `<span class="status">` anti-pattern and its vertical-wrapping symptom.
- **element-index.md** — New "Per-Element Edit-Screen Action Menu" section: `EVENT_DEFINE_ACTION_MENU_ITEMS` vs `EVENT_REGISTER_ACTIONS` (two different surfaces), disclosure menu item shape, security guidance on which surface to register on.
- **elements.md** — New "Extending User Edit Screens" section: `UsersController::EVENT_DEFINE_EDIT_SCREENS`, `DefineEditUserScreensEvent` payload, when to use sidebar vs screens.
- **cp.md** — New "CP UI Patterns" section with 6 battle-tested patterns from Craft core and first-party plugins: (1) Tri-state inheritance controls (webhooks plugin pattern with `<div class="btn">`, `data-icon`, `.status.inactive`). (2) Status indicator classes (all modifiers — bare `.status` is invisible in Craft 5). (3) Field `warning:` parameter for "overrides global" indicators (Blitz pattern). (4) `[hidden]` attribute gotcha with `display: flex` override. (5) Craft CSS custom properties (`--bg-enabled`, `--bg-disabled`, grey/red/blue/yellow scales). (6) Platform PHP version mismatch fix.
- **console-commands.md** — Full CLI rewrite: expanded from ~25 to 80+ commands. New groups: `sections/*` (create, delete), `entry-types/merge`, `fields/*` (auto-merge, delete, merge), `elements/*` (delete, restore, delete-all-of-type), `plugin/*` (install, uninstall, enable, disable, list), `graphql/*` (create-token, dump-schema), `mailer/test`, `utils/*` (prune-revisions, prune-orphaned-entries, repair), `env/*`, `update/*`. Expanded existing groups: `users/*` (3→11 commands), `migrate/*` (1→9), `project-config/*` (4→9 with `pc/` alias), `resave/*` (full flags reference), `clear-caches/*` (4→8), `db/*` (3→6).

### Changed

- **cp.md** — New "Tabbed Settings Pages" section: three patterns for multi-tab CP pages. Twig-level tabs (separate URL per tab with `selectedTab`), anchor-based tabs (single-page with Craft JS auto show/hide), and PHP-level tabs via `asCpScreen()->tabs()` and `addTab()` fluent API.
- **cp.md** — New `buttonGroupField` form macro with tri-state caveat (not for inheritance UI — use the webhook pattern instead).
- **ddev SKILL.md** — New pitfall: host PHP version mismatch causing `platform_check.php` failures.
- **craftcms SKILL.md** — 4 new task routing entries for CP UI patterns (tri-state, tabs, field warnings, CSS variables).
- **cp.md** (1,274 → 782 lines) — Split into 3 focused files for input token efficiency. `cp.md` retains templates, forms, settings, navigation, permissions, read-only mode. Widgets, utilities, slideouts, ajax, alerts moved to `cp-components.md`. UI patterns, condition builders, asset bundles moved to `cp-ui-patterns.md`. Heaviest load scenario ("Build custom element type") dropped from 37K to 33K tokens.
- **craftcms SKILL.md** — Reference routing table now includes approximate token cost per file (~2K–8K range). Nudges cost-aware loading decisions. 3 new task routing entries (status pills, per-element action menu, user edit screens). Updated routing for split CP files. New trigger keywords: `statusLabelHtml`, `EVENT_DEFINE_ACTION_MENU_ITEMS`, `EVENT_DEFINE_EDIT_SCREENS`, `DefineEditUserScreensEvent`.
- **element-index.md** — Event reference table: added `EVENT_DEFINE_ACTION_MENU_ITEMS` row, clarified `EVENT_REGISTER_ACTIONS` as "bulk actions (index multi-select)". Two new Common Pitfalls: `<span class="status">` for labels, missing per-element action registration.
- **All 5 agents** — New "Output density" environment rule. Feature-builder: gate results in one-liners, no preamble/recap. Code-reviewer: one-block findings, omit empty sections. Debugger: lead with diagnosis, single line per ruled-out hypothesis. Planner: structured steps not essays. Site-builder: code speaks, skip introductions.
- **queue-jobs.md** — Generalized UserQuery pitfall (was too focused on `lastPasswordChangeDate`, now covers all excluded security columns). BaseBatchedJob example uses generic `SyncExternalProducts` instead of plugin-specific class. New "BaseBatchedJob Subclass Contract" section with overridable vs final method table.
- **architecture.md** — New "External API Rate-Limit Backoff" section: site-wide cache key pattern for 429 responses with `Retry-After` TTL. New "Record-to-Model Hydration Boundary" section: ActiveRecord datetime string coercion via `DateTimeHelper::toDateTime()`.
- **events.md** — CraftVariable handle case sensitivity warning (exact string matching, not case-insensitive). `__toString()` double-escape trap on HTML-builder Twig classes (return `\Twig\Markup` from `render()`, document that consumers must call `.render()`).
- **craft-feature-builder, craft-site-builder, craft-debugger agents** — New environment rule: "Dedicated tools over Bash" — use Grep/Glob/Read instead of grep/find/cat/wc via Bash. Explicit mapping of which tool replaces which shell command. Log tailing exception for debugger and feature-builder. Bash-allowed lists aligned with each agent's actual scope.
- **craft-feature-builder agent** — Rewritten from layer-first to feature-first build order. The old fixed 9-step pipeline (migration → model → service → controller → templates → browser → tests → simplify → check) assumed every feature needs every layer in the same order. New approach: identify which layers the feature needs, build them in dependency order with tests at each layer, then run closing gates (browser, full suite, simplification, check-cs/phpstan). Layer gates table covers migration, record/model, service, element query, controller, queue job, event listener, permissions, CP templates, CP JavaScript — use whichever your feature needs.
- **craft-planner agent** — Rewritten from layer-first to feature-first planning. Plans are now organized by feature (vertical slices), not by layer type. Each feature group contains steps for whatever layers it needs — an element type has different steps than a webhook or a settings page. New plan format with feature-grouped example. Rule: "Feature-first, not layer-first. Never plan Step 1: all migrations, Step 2: all models." Manual checks (required and optional) included in plan steps — each feature group ends with manual verification the user needs to confirm.
- **craft-feature-builder agent** — New "Manual testing" section with two tables: required checks (CP UX, visual rendering, email delivery, third-party webhooks, file uploads, print output) and optional sanity checks (permission gating, multi-site, queue completion, read-only mode, error states, edge cases). Builder tells the user which manual checks apply after automated tests pass. New token efficiency rule: read reference files only when building the relevant layer.
- **craft-planner agent** — Added Bash and WebFetch tools for research. New "Research and audit" section: `gh repo view`, `gh api`, `git clone --depth 1` into dev root research folder, `WebFetch` for docs. Can now audit public plugins and research patterns before planning. Token efficiency rule: use SKILL.md summaries for architectural planning, read reference files only when the plan requires specific API knowledge.
- **craft-code-reviewer agent** — Added Bash (read-only: `git diff`, `git log`, `git show`, `git blame`). Added `craft-garnish`, `craft-twig-guidelines`, and `craft-site` to default skills — the reviewer checks everything in the diff, not just PHP. New "Twig template checks" section (12 items: include isolation, variable naming, null handling, eagerly(), collect(), no queries in views). New "CSS and asset checks" section (4 items: Tailwind conventions, Craft CSS properties, Vite config, conditional bundles). Diff classification step determines which checklist sections and reference files apply. Token efficiency via selective reference loading, not skill removal.
- **craft-site-builder agent** — Token efficiency rule: read plugin references only when integrating that specific plugin.
- **All builder/debugger agents** — Rewritten Bash rules: bans anti-patterns (`grep`/`rg`/`find` for searching, `cat`/`head` for reading, `cd path && command`, `ls | grep`, `rm`), not tools. `ls` for directory inspection, `readlink` for symlinks, `tail -n` on logs are explicitly allowed. Focus on what to use instead, not a blanket tool ban.
- **git-workflow.md templates (all 3 project types)** — Commit message discipline: subject line only for most commits (under 72 chars). Body only when the why isn't obvious, capped at 3-5 lines. Explicitly bans "Verification", "How to undo", "Follow-up" sections, file-by-file change lists, and test count reports in commit messages. Bans `cd path && git commit` pattern (untrusted hooks risk).
- **architecture.md** — New pitfalls: Yii cache `get()` returns `false` for missing keys (collides with cached `false` — use string sentinels or `exists()`). Controller directory case must match namespace exactly (macOS vs Linux filesystem case sensitivity).
- **sessions-and-auth.md** — New pitfall: `User::EVENT_BEFORE_AUTHENTICATE` is the only Craft 5 hook with synchronous plaintext password access. For HIBP/breach detection, listen here, hash inside, never log plaintext.
- **testing.md** — Three new pitfalls: `craft\test\TestSetup` transitively loads Codeception (Pest-only setups must inline bootstrap). PHPUnit 12 `<env force="true"/>` doesn't overwrite `$_SERVER` (DDEV exports win — set all three: `$_SERVER`, `$_ENV`, `putenv()`). Solo edition silently caps user creation at 1 (set `CmsEdition::Pro` directly in test, not via project config).
- **craft-project-setup SKILL.md** — New "Dev root folder" detection question. Generated CLAUDE.md includes `devRootPath` and research folder paths. Research folder permissions added to `settings.local.json` template (`git clone`, `gh repo view`, `gh api`, `Read` on research folder, cleanup).
- **craft-project-setup SKILL.md** — Fixed: Step 3 now verifies which templates actually exist before generating. Files without templates (testing.md, migrations.md, settings.local.json) are generated from project context instead of silently skipped. Agent flags which files came from templates vs generated from scratch. New Step 3b: generates `.claude/settings.local.json` with pre-approved permissions for DDEV commands, git operations, and `gh`. Connected projects question asks if related folders need permissions (plugin dev site, headless frontend, shared modules). Generated CLAUDE.md now includes a Permissions section explaining the local settings file. New "Existing Configuration — Upgrade & Compare" section: when CLAUDE.md or .claude/rules/ already exist, runs a gap analysis instead of stopping. Compares current config vs fresh scaffold, presents diff table (missing sections, outdated patterns, missing files, version drift), lets user choose per-area (keep/update/skip). Works for first-time setup, upgrades after version bump, and config audits. New trigger keywords: 'upgrade Claude config', 'update CLAUDE.md', 'is my config up to date', 'audit my Claude setup'.
- **queue-jobs.md** — New "BaseBatchedJob Subclass Contract" section: method override table (overridable vs final), `defaultDescription()` pattern, full example. New pitfalls: `getDescription()` is final on `BaseBatchedJob`, `$user->lastPasswordChangeDate` returns null from element queries.
- **architecture.md** — New "Record-to-Model Hydration Boundary" section: ActiveRecord returns datetime columns as raw SQL strings, not DateTime objects. `DateTimeHelper::toDateTime()` wrapping pattern with `fromRecord()` example. New pitfall in Common Pitfalls.

## 1.2.1 -- 2026-04-29

Object template syntax, element display modes, element partials, generated fields, read-only settings pattern, Chrome DevTools MCP integration, security patterns from Craft Core, quality audit with reference file splits and description optimization across all 8 skills, expanded CP form macros and editable tables, Element Index JS loading pattern for Garnish, PHPStan pitfalls for magic property access and queue-injected properties, Address element propagation documentation.

### New

- **object-templates.md** (334 lines, craft-content-modeling) — Complete reference for Craft's mini-template system used in URI formats, asset subpaths, title formats, preview target URLs. Covers both syntaxes (`{attribute}` shortcut vs `{{ twig }}` expressions), context variables by nesting level, `owner` and `rootOwner` (since 5.4.0) for Matrix/CKEditor nested entries, structure URI patterns with automatic slash handling, asset subpath patterns with the Matrix gotcha (moving fields into Matrix changes context variables), preview target tokens, date formatting, and error handling.
- **element-partials.md** (197 lines, craft-site) — The `entry.render()` pattern for reusable front-end element rendering. Template lookup path (`_partials/{refHandle}/{providerHandle}.twig` → `_partials/{refHandle}.twig`), available variables, passing custom variables, common patterns (blog card grids, type-specific partials, Matrix block rendering), `.eagerly()` for N+1 prevention inside partials, `partialTemplatesPath` configuration.

### Changed

- **elements.md** — New "Generated Fields (5.8.0)" section documenting computed field values stored on elements. Covers the field layout API (`getGeneratedFields()`), storage and querying, use cases (computed summaries, denormalized data, sequential numbering), and limitations.
- **element-index.md** — New "Element Display Modes" section documenting all three CP display modes: chips (`chipLabelHtml()`, `showStatusIndicator()`, sizing), cards (`cardBodyHtml()`, `getCardTitle()`, field layout card view), and table rows (`attributeHtml()`). Expanded card attributes with default attributes list. Expanded thumbnails section with full resolution chain (`getThumbHtml()` → `thumbUrl()` → `thumbSvg()`), checkered/rounded options, and lazy-loading. Expanded "Index View Modes" from 10-line stub to full reference with mode table, `defaultIndexViewMode()`, and registration pattern.
- **cp.md** — New "Read-Only Mode (allowAdminChanges)" section with full controller + template pattern: `requireAdmin(false)` for view actions, `readOnly` variable threading, disabled/readonly form fields, static HTML table fallback for editable tables, `fullPageForm` toggle, and read-only notice banner.

### Chrome DevTools MCP integration

- **ddev SKILL.md** — New "Browser Debugging with Chrome DevTools MCP" section: installation command, capabilities table (page inspection, console logs, network requests, DOM queries, screenshots, navigation/login), use cases (front-end debugging, CP template verification, Garnish/JS debugging, Sprig/htmx, auth flows, read-only mode, visual regression), CP authentication pattern.
- **craft-project-setup SKILL.md** — Detection step now checks `.claude.json` for existing MCP config and offers installation during scaffolding (user choice, not forced).
- **craft-debugger agent** — New "Browser Debugging" section: front-end template inspection, CP template debugging (login, navigate to plugin pages, verify form macros and Garnish widgets), Sprig/htmx debugging, visual verification with screenshots. Code-level debugging first, browser when you need to see what the user sees.
- **craft-feature-builder agent** — New gate #6 "Browser verification": after building CP templates, log in and visually confirm forms render, editable tables work, element selects open modals, read-only mode disables fields. Console check for JS errors.
- **craft-site-builder agent** — New gate #7 "Browser verification": navigate to built pages, confirm layout, test responsive at multiple widths, walk through auth flows end-to-end. Final verification includes screenshot for user review.
- **craft-code-reviewer agent** — New "Browser Verification" section: optionally verify XSS concerns in the running site, inspect CP templates, check permission gating. Supplementary to code review, not a replacement.

### Security patterns from Craft Core fixes

- **controllers.md** — Two new pitfalls from Craft Core security fixes: (1) TOCTOU — re-check permissions after model population when POST data can change the authorization context (e.g., sectionId swap). (2) Element/block ID manipulation in POST — always verify `canSave()`/`canView()` on the resolved element after loading from a user-supplied ID.
- **craft-feature-builder agent** — Two new prevention rules: TOCTOU in save actions, element ID manipulation.
- **craft-code-reviewer agent** — Two new checklist items matching the builder's prevention rules.

### UserQuery column exclusion pitfall

- **elements.md** — New pitfall: `UserQuery::beforePrepare()` intentionally excludes security-sensitive columns (`lastPasswordChangeDate`, `password`, `invalidLoginCount`, `lastInvalidLoginDate`, `verificationCode`, `verificationCodeIssuedDate`, `lastLoginAttemptIp`). These properties are `null` on User elements from element queries. Query `Table::USERS` directly to access them.
- **sessions-and-auth.md** — Cross-referenced the same pitfall for developers working with password/session features.

### Session-reported fixes

- **ddev SKILL.md** — New "Craft CLI First, Raw SQL Last" section: prefer `ddev craft` commands over `ddev mysql`, with examples.
- **ddev SKILL.md** — New "Composer Path Repos and Volume Mounts" section: setup for local plugin development, docker-compose volume mapping, path matching requirement. Common mistakes: wrong path context, missing mount, `platform` in composer.json.
- **config-bootstrap.md** — Strengthened db.php language from "usually unnecessary" to "Deprecated in Craft 5. Remove from new projects."
- **deployment.md** — New "rebuild vs apply --force — know the direction" table: YAML→DB vs DB→YAML, which is destructive to what.
- **architecture.md** — Added `dateModified` requirement to Project Config section. Expanded edition switching to 4 steps (including dateModified update). New "Edition Helper Methods" section with constants pattern. New "Edition in Migrations" section.
- **config-bootstrap.md** — Expanded `@web` Problem section to warn about filesystem URLs being unreliable.
- **infrastructure.md** — New `@web` filesystem URL warning with wrong vs correct YAML examples and env var pattern.
- **craft-content-modeling SKILL.md** — New pitfall: using `@web` in filesystem URLs.
- **craft-site SKILL.md** — New pitfall: forgetting `project-config/touch` after manual YAML edits.
- **craft-site-builder agent** — Added `project-config/touch` note on content model gate.

### Quality fixes (from skill-creator review)

- **cp.md** — Fixed typo: `adminChanges` → `allowAdminChanges` in read-only notice. Added split settings and markup patterns to Contents TOC.
- **craft-code-reviewer agent** — Rewrote Browser Verification section: the reviewer has read-only file tools but CAN use Chrome DevTools MCP for observation (inspecting pages, checking console, screenshots). Qualitative review needs to see the rendered output. Removed duplicate empty `## Rules` heading.
- **craft-site-builder agent** — Fixed inconsistent "Chrome DevTools" → "Chrome DevTools MCP" in gate 8.
- **craft-debugger agent** — Added `ddev` skill cross-reference for Chrome DevTools MCP setup docs.
- **ddev SKILL.md** — Clarified restart instruction ("Quit and reopen Claude Code"). Fixed `.claude.json` instruction to use `claude mcp add` command instead of manual file editing. Clarified that MCP server handles DevTools Protocol connection automatically.
- **email.md** — Standardized version format: `(5.6+)` → `(since 5.6.0)`.

### Improved project detection

- **craft-project-setup SKILL.md** — Detection step completely rewritten. New dependency detection table (12 packages mapped to capabilities: SEOmatic = `???` available, Blitz = static caching, etc.). Explicit "Detect, don't assume" instruction. Front-end detection (Tailwind v3 vs v4, Alpine, Vue, Vite). Git detection (branch name, commit style). "Do not ask about things you already detected" — present results for confirmation, not as open questions.

### Community-reported fixes

- **craft-twig-guidelines SKILL.md** — New pitfall #11: blocks cannot nest inside conditionals (`{% if %}{% block %}{% endblock %}{% endif %}` is invalid Twig). New pitfall #12: hardcoded `/admin` CP URL — cpTrigger is configurable.
- **cp.md** — New "Split Settings Pages" section documenting the `savePluginSettings()` footgun: only submitted keys persist, split-settings pages must merge with existing settings. Full code pattern included.
- **cp.md** — New "CP Markup Patterns" section: sidebar badge markup (`<span class="badge">`), notice/warning semantic markup with `has-icon` pattern, `tip`/`warning` parameters on form field macros.
- **email.md** — New "Per-site email overrides" section documenting `Mailer::$siteOverrides` (since 5.6.0) with `$message->siteId` usage for multi-site plugins.
- **craftcms SKILL.md** — Added cross-cutting pitfalls: hardcoded `/admin` CP URLs, `savePluginSettings()` on split-settings pages.

### Skill routing

- **craft-content-modeling SKILL.md** — Added object-templates.md to reference table. New task routing: "Configure URI format for a structure section", "Set up dynamic asset upload subpath", "Asset subpath broken after moving field into Matrix".
- **craft-site SKILL.md** — Added element-partials.md to reference table. New task routing: "Use entry.render()", "Set up _partials/ templates", "Render Matrix blocks with partials".
- **craftcms SKILL.md** — New task routing: "Add generated fields to a custom element", "Customize chip/card appearance", "Make plugin settings read-only".

### Quality audit & reference splits

- **auth-flows.md** (878 lines) — Split into `auth-flows.md` (442 lines: login, registration, password reset, set new password) and `auth-account.md` (452 lines: edit profile, email verification, navigation partial, access control tags, user session helpers, GeneralConfig auth settings). Updated craft-site SKILL.md reference table and task routing.
- **config-general.md** (861 lines) — Split into `config-general.md` (431 lines: system, routing, security, users, sessions, search, assets, images) and `config-general-extended.md` (433 lines: content, templates, performance, GC, localization, aliases, headless/GraphQL, accessibility, preview, development, dangerous interactions). Updated craftcms SKILL.md reference table.
- **ckeditor.md** — Added warning that direct output (`{{ entry.richContent }}`) renders `Array` when nested entries exist. Chunk loop pattern is now documented as the safe default.
- **fields.md** — Added 12-entry Table of Contents for navigation (423-line file had no TOC).
- **ui-widgets.md** — Added `Craft.Slideout` cross-reference in See Also section (extends `Garnish.Modal` but was undocumented in Garnish skill).
- **integration.md** — Expanded MixedInput documentation: usage example, 4 additional methods (`focus()`, `blur()`, `onPaste()`, `reset()`), context about where it's used in Craft.
- **sprig.md** — Rewrote Blitz compatibility section: added `{% dynamicInclude %}` as preferred approach, explicit warning against wrapping Sprig in `{% cache %}` tags, 4 strategies instead of 3.
- **integration.md** — New "Element Index JS Loading" section documenting why Vite `type="module"` breaks `Craft.registerElementIndexClass()` timing. Full 3-file pattern (AssetBundle reading Vite manifest, controller registration, clean template), data injection via `POS_HEAD`, execution order diagram, and "when Vite IS fine" exemptions. Modeled after Commerce's `ProductIndexAsset`. Added `afterInit()` lifecycle hook documentation (a `Craft.BaseElementIndex` method, not `Garnish.Base`).
- **plugin-vite.md** — New top pitfall warning against using Vite for element index JS, with cross-reference to craft-garnish's integration.md pattern.
- **craft-php-guidelines SKILL.md** — New pitfall: prefer explicit getters (`getSettings()`, `getView()`) over magic property access (`->settings`, `->view`). PHPStan can't resolve `__get()` calls.
- **queue-jobs.md** — New pitfall: queue-injected `$this->queue` requires `@property Queue $queue` docblock annotation. Applies to `BaseJob`, `BaseBatchedJob`, and custom base classes.
- **quality.md** — Two new PHPStan error table rows: `$queue` undefined property fix and `__get()` magic access fix.
- **cp.md** (622 → 819 lines) — Major expansion of CP form macros. Editable table: full column type reference (12 types), raw vs field-wrapped variants, server-side handling pattern, row population from models, Garnish JS interaction (`Craft.EditableTable`), `defaultValues`/`minRows`/`maxRows`/`staticRows`. Form macros reference: expanded from 10 to 17 macros with key params table, common parameters reference, detailed examples for `autosuggestField` (env vars, aliases), `elementSelectField` (relation selector with modal), `lightswitchField` toggle pattern.
- **elements.md** — New pitfall: `NestedElementTrait` does not handle site propagation. Address elements fall through to primary site only. Matrix entries get multi-site because Entry overrides `getSupportedSites()`, not the trait. New explanation in Propagation section documenting the base Element default and the Entry-specific delegation chain.
- **infrastructure.md** — New warning: Address elements don't propagate with their owner despite being nested elements.

### Description optimization

All 8 skill descriptions rewritten for better triggering accuracy. Added explicit `NOT for` / `Do NOT trigger` clauses to reduce cross-skill false positives, with redirects to the correct skill.

- **craftcms** — Added `batch processing, data sync, permissions, registerUserPermissions, requirePermission`, config references (`config/app.php`, `config/general.php`, Redis, SMTP).
- **craft-site** — Added `front-end auth, login form, registration form, tabs, accordions, interactive components, meta tags, OpenGraph, JSON-LD, dynamic caching with Sprig, hreflang, form styling`.
- **craft-content-modeling** — Added `field layout design, field type selection`. Disambiguated `permissions` to `content permissions`.
- **craft-garnish** — Added `CP memory leak, event listener cleanup, jQuery .on() in CP, selection interface, multi-select grid`.
- **craft-php-guidelines** — Added `documenting exceptions, strict_types, declare(strict_types=1), typed properties, void return types, early returns, match over switch, writing service classes, models, controllers`.
- **craft-twig-guidelines** — Added `comment headers with ========= separators, blank lines in output, minify alternatives, Twig file headers, svg() with styling and aria, polymorphic elements, class string building`.
- **ddev** — Added `ddev share, temporary public URLs, ddev logs, ddev delete, port conflicts, ran npm/composer on host instead of ddev, wrong node_modules architecture`.
- **craft-project-setup** — Added `monorepo, create CLAUDE.md, missing CLAUDE.md`. Strong negative boundary for non-Craft projects.

## 1.2.0 -- 2026-04-20

Complete rewrite of configuration reference and expansion of 4 thin reference files. Full coverage of all Craft CMS 5 config settings, mail transport, search performance, app component configuration, migrations, queue jobs, code quality tooling, and CP templates. Agent architecture overhaul with explicit build-verify gates, mandatory todo lists, and removal of the redundant simplifier agent. Content modeling improvement: reuse-first field workflow. New Garnish JS skill for CP JavaScript development. Gap analysis: 9 new reference files (element authorization, sessions, custom field types, conditions, email, deployment, drafts/revisions, search, feeds) filling 12 identified coverage gaps. Headless/GraphQL consumer patterns moved from craftcms to craft-site. New /docs directory with getting-started guide, skills overview, 43-prompt guide, agent documentation, and contributing guide. GitHub issue templates upgraded to YAML forms with structured data collection.

### New skill: craft-garnish

- **craft-garnish** — Full reference for Garnish, Craft CMS's undocumented CP JavaScript UI toolkit. 5 reference files (2,050 lines) covering the class system (`Garnish.Base.extend`, inheritance, events, listeners, destroy lifecycle), UI widgets (Modal, HUD, DisclosureMenu, MenuBtn, Select, CustomSelect, ContextMenu), drag system (BaseDrag, Drag, DragSort, DragDrop, DragMove with full settings/events/hierarchy), utilities (key constants, custom jQuery events `activate`/`textchange`/`resize`, ARIA/focus management, UiLayerManager, geometry, animation), and Craft integration (GarnishAsset, webpack externals, `Craft.*` class pattern, Twig JS blocks, form widgets). Source-validated against `~/dev/craftcms/src/web/assets/garnish/src/`. Tested with 3 evals (DragSort, Modal, DisclosureMenu) showing +78% quality improvement over baseline.
- **Ecosystem integration** — craftcms SKILL.md now cross-references craft-garnish in companion skills, 3 task examples, and the reference table. craft-feature-builder and craft-code-reviewer agents load craft-garnish and include CP JavaScript guidance (8 review checks). craft-project-setup mentions craft-garnish for plugin projects with CP assets.

### Content modeling

- **craft-content-modeling SKILL.md** — Added "Reuse-First Workflow" section that enforces field pool audit before proposing new fields. Agents must enumerate existing fields via `config/project/fields/`, classify each proposed field as reuse / reuse-with-review / create-new, and present a decision table. Also documents multi-instance vs single-instance field types (Matrix, Content Block, Addresses are single-instance) with reuse caveats. Addresses [#3](https://github.com/michtio/craftcms-claude-skills/issues/3).

### Trigger & token efficiency

- **craftcms SKILL.md** — Added trigger keywords: GraphQL, headless, Rector, CI/CD, GitHub Actions, validator, defineRules.
- **craft-site SKILL.md** — Added trigger keywords: Blitz, ImageOptimize, Imager-X, responsive images, srcset, SEOmatic, Sprig, Formie, localization.
- **craft-content-modeling SKILL.md** — Added trigger keywords: site propagation, multi-language, localization, translation method, field instances, reserved handles. Extracted 150 lines (propagation, project config, storage model, asset volumes) into new `references/infrastructure.md` — body dropped from 447 to 297 lines.
- **craft-garnish SKILL.md** — Conditional companion loading: craftcms and craft-php-guidelines only load when the task involves PHP (asset bundles, plugin architecture). Pure JS tasks skip them, saving ~9,000 lines of context.
- **craftcms/references/elements.md** — Upgraded TOC from plain text to descriptive format with section summaries.
- **craftcms/references/events.md** — Upgraded TOC from plain text to descriptive format with section summaries.
- **.gitignore** — Added `*-workspace/` pattern to exclude eval artifacts.

### Skill consistency

- **ddev SKILL.md** — Added companion skills section (craftcms, craft-php-guidelines). Added higher-level trigger phrases (Docker, local environment, .env, Vite dev server, PHP/Node version). Stronger pushiness in description.
- **craft-twig-guidelines SKILL.md** — Changed companion language from "Load as Needed" to "Always Load Together" to match craft-site's reciprocal declaration.
- **craft-project-setup SKILL.md** — Added companion skills section documenting which skills the generated config references. Added trigger phrases (new project, onboard, bootstrap). Stronger pushiness in description.
- **craftcms SKILL.md** — Added higher-level trigger phrases (plugin development, module development, custom element type, custom field type, webhook, API endpoint, queue job, dashboard widget, utility page) for better discoverability beyond low-level API names.

### Agent architecture

- **Removed `craft-simplifier` agent.** Its checklist (reducing nesting, removing dead code, simplifying conditionals, ensuring PHPDocs and section headers) is now covered in two places: `craft-feature-builder` runs an explicit simplification pass on files it just wrote (while it still holds the full context), and `craft-code-reviewer`'s existing checklist catches anything that slips through. Running a dedicated simplifier after the builder meant re-reading files the builder just wrote without the builder's context about why they looked that way — a ~30-40% coordination tax per feature cycle, with a real risk of subtle behavior changes. Agent count drops from 6 to 5.
- **craft-feature-builder** — Added explicit build-verify gates (migration → migrate/up passes → record/model → boot check → service → tinker/test → controller → curl/browser check → CP templates → render → tests green → simplification pass → check-cs + phpstan). A gate is a runnable command with an expected outcome, not "looks right." Never write the next layer until the current layer's gate passes. Absorbed the simplifier checklist as a final pass before handoff, run while build context is still fresh.
- **craft-feature-builder** — Mandatory todo list when a plan contains more than 3 steps. One todo per plan step. `completed` only after the gate passes.
- **craft-site-builder** — Added explicit build-verify gates adapted for site work (content model → CP confirmation → sample content → atoms → molecules → organisms → routes → eager-loading audit → responsive/a11y). Same mandatory-todo rule for tasks with more than 3 pieces of work.
- **craft-planner** — Each step's verification criterion must now be a runnable command with expected outcome, not a vibe check. Explicit ordering rule: no step may require a later step to verify itself.
- **craft-feature-builder** — Added "Patterns to prevent" section with 10 rules the reviewer will flag: `where()` vs `andWhere()`, hardcoded site IDs, blanket `$allowAnonymous`, error message leakage, permission handle constants, badge count performance, `Gc::EVENT_RUN` for cleanup, conditional asset bundles, `|raw` XSS, Twig extension patterns. Prevention complements the reviewer's detection.
- **craft-code-reviewer** — Expanded checklist from 7 to 18 items. Added: `$allowAnonymous` blanket check, error message leakage, `|raw` XSS review, permission handle matching, `andWhere()` enforcement, hardcoded site ID detection, query property wiring, `getCpNavItem()` performance, synchronous cleanup detection, `defineSources()` performance, conditional asset bundle registration.

### New

- **config-general.md** — all 130+ GeneralConfig settings across 17 categories with implications, dangerous interactions, and production hardening guidance
- **config-app.md** — all app.php components: cache (DB/Redis/APCu/Memcached), session, queue, mutex, mailer (SMTP/Gmail/Sendmail + AWS SES/Mailgun/Postmark/Sendgrid plugins), search component, logging, CORS, database replicas, module registration, multi-site maxSites
- **config-bootstrap.md** — environment variables, CRAFT_* auto-mapping, aliases (@web/@webroot/custom), config priority order, fluent API, custom.php, db.php, routes.php, htmlpurifier configs
- Web vs console split explanation — why app.web.php and app.console.php exist, decision table for which components go in which file

### Changed

- **elements.md** (636 → 803 lines) — Added "Attributes, Field Values, and Mass Assignment" section (value flow, safe attribute gate, silent drop trap, `setFieldValue`/`setFieldValues`/`setFieldValueFromRequest`, normalization lifecycle, native field layout registration). New pitfalls: `where()` vs `andWhere()`, hardcoded site IDs, `defineSources()` performance, unwired query properties. Expanded soft delete section with `Gc::EVENT_RUN` for plugin cleanup. Corrected save lifecycle from 16 to 15 steps (custom table write is the developer's `afterSave()`, not a distinct Craft step). Cross-reference from architecture.md validator table.
- **controllers.md** — Fixed webhook example leaking `$e->getMessage()` to anonymous users (now logs real exception, returns generic message). New pitfalls: blanket `$allowAnonymous = true`, error message leakage, `$enableCsrfValidation` is per-controller not per-action. Authorization table clarified that blanket anonymous access requires a dedicated API controller.
- **permissions.md** — New pitfalls: `requirePermission()` on non-existent handles silently passes for admins, string literal permission handles across files cause phantom mismatches. Recommends class constants.
- **cp.md** — New pitfall: expensive `badgeCount` in `getCpNavItem()` runs on every CP page load. Updated example to show cached count pattern. Fixed XSS in `json_encode|raw` template example (added `JSON_HEX_TAG`). Replaced manual `registerJs` JSON injection with safe `registerJsVar`. Fixed utility event constant (`EVENT_REGISTER_UTILITY_TYPES` → `EVENT_REGISTER_UTILITIES`).
- **events.md** — Expanded Twig extension section (return not echo, delegate to services, `is_safe` usage). New "Conditional asset bundle registration" subsection with `isCpRequest()` scoping example.
- **templates-and-patterns.md** — New "Output Safety" subsection warning against `|raw` on admin-entered content in `<style>`/`<script>` tags.
- **migrations.md** (101 → 401 lines) — content migrations (creating sections/fields/entry types programmatically), common schema patterns, multi-site migrations, project config interaction, safeDown patterns, `craft migrate` vs `craft up` comparison
- **queue-jobs.md** (125 → 402 lines) — queue infrastructure (daemon vs web runner), retry strategies, failed job handling, long-running patterns, priority, built-in jobs table, queue health monitoring
- **craft-project-setup SKILL.md** — Added skill attribution markers for adoption tracking: composer.json `extra` key, CLAUDE.md HTML comment, `.claude/rules/` file headers. Non-functional, invisible in rendered markdown, scrapable via GitHub API.
- **Cross-reference audit** — Standardized all intra-reference cross-references to bare filenames (was inconsistent mix of `references/foo.md` and `foo.md`). Removed verbatim duplication of `defineSources()` pitfall across elements.md and element-index.md.
- **quality.md** (177 → 405 lines) — ECS deep dive with violation table, PHPStan levels 0-9, craftcms/phpstan package, Rector for automated refactoring, CI/CD GitHub Actions workflow, pre-commit hooks. Removed duplicated Pest content (cross-references testing.md)
- **cp.md** (252 → 576 lines) — CP navigation, plugin settings pages, utility pages (full pattern), dashboard widgets (full pattern), slideout editors, Ajax endpoints, CP alerts, additional form macros, condition builders
- **craftcms SKILL.md** — configuration reference split from 1 file to 3, with expanded task routing examples (search, mail, env vars, GraphQL tokens). Added 10 missing routing entries (plugin editions, Rector/upgrade, CI/CD, content migrations, DB replicas, module registration, custom validators, filesystem types, condition builders, pre-commit hooks). Fixed dashboard widget routing to include cp.md.
- **craft-feature-builder** — Added 4 more prevention rules (`addSelect()`/`select()`, `Db::parseParam()`, migration idempotency + `muteEvents`, `defineSources()` aggregate queries). Total prevention rules: 14.
- **craft-code-reviewer** — Added Twig extension check (return not echo, delegate to services, `is_safe` usage). Total checklist items: 19.
- **element-index.md** — Fixed preview targets code to match elements.md. Added `defineSources()` performance pitfall.
- **events.md** — Fixed GraphQL event count (10 → 9).
- **README** — added 4 configuration prompt examples (search performance, mail transport, production hardening, environment variables)
- **console-commands.md** (224 → 400 lines) — built-in command reference (40+ commands in 7 categories), full `craft make` generator list (12 generators), environment notes, deployment recipes
- **fields.md** (240 → 423 lines) — validation rules, search keywords, GraphQL integration (3 GQL methods), full lifecycle method table, multi-site translation, static/preview HTML, Craft 5 static config methods
- **graphql.md** (278 → 541 lines) — arguments class, query resolvers, full mutation pattern (input types, resolver, error handling), consumer query patterns (entries, assets, relations, Matrix, globals), token management, testing
- **debugging.md** (278 → 549 lines) — template debugging (dump/dd), full `{% cache %}` tag reference, N+1 detection and fixes, query logging, error handling patterns, deprecation tracking, 9-row anti-pattern table
- **auth-flows.md** (new, 878 lines) — complete front-end authentication templates: login, registration, password reset request, set new password, edit profile, email verification, navigation partial, access control tags, user session helpers, 17 GeneralConfig auth settings (craft-site skill)
- **caching.md** (new, 517 lines) — caching decision guide, full `{% cache %}` tag reference with all options, data caching with TagDependency, static caching strategy (Blitz), CDN/edge patterns, five-layer caching architecture, invalidation patterns, development debugging
- **permissions.md** (new, 424 lines) — complete built-in permission handles, user groups, admin bypass behavior, Twig/PHP permission checking, custom permission registration, element authorization events, member area/editor workflow/multi-site permission strategies

### Removed

- **configuration.md** — replaced by the three new config reference files

### Gap analysis & new reference files

A systematic gap analysis identified 12 areas where skills lacked coverage. 9 new reference files (3,166 lines) and 2 expanded files were added. Security patterns from real plugin development (password-policy, user-scoping plans) informed gaps 1-5.

**New reference files (craftcms skill):**
- **element-authorization.md** (490 lines) — Four-layer defense model (UI → Route → Query → Authorization), all 8 authorization events on `Elements::class`, element `can*()` method overrides with built-in logic for Entry/User/Asset, query scoping via `EVENT_BEFORE_PREPARE` with context guards and memoization, controller-level enforcement, defense-in-depth patterns for plugins
- **sessions-and-auth.md** (314 lines) — Dual-layer session model (PHP sessions + DB auth tokens in `Table::SESSIONS`), session invalidation on password change, the `passwordResetRequired` gap (only checked at auth, not per-request), elevated sessions, force-logout patterns for plugins
- **field-types-custom.md** (475 lines) — Complete custom field type build pattern: class hierarchy, static config methods, value lifecycle (`normalizeValue` → `serializeValue`), settings, input HTML, validation, search keywords, GraphQL integration (3 methods), preview/static HTML, element lifecycle hooks, relation fields via `BaseRelationField`
- **conditions.md** (290 lines) — Conditions framework: `BaseCondition`, `ElementCondition`, 7 built-in condition rule base types, building custom condition rules with `modifyQuery()` and `matchElement()`, registering via `EVENT_REGISTER_CONDITION_RULES`, condition builder UI
- **email.md** (255 lines) — Email system: 4 built-in system messages, custom message registration via `EVENT_REGISTER_MESSAGES`, programmatic sending with `composeFromKey()`, email template rendering pipeline (Twig → Markdown → HTML wrapper), events (`EVENT_BEFORE_PREP`, before/after send), testing with Mailpit
- **deployment.md** (262 lines) — Deployment patterns: standard pipeline (build → release → migrate → cache), production config baseline, project config commands (`craft up` vs `project-config/apply` vs `project-config/rebuild`), zero-downtime atomic/symlink deploys, CI/CD with GitHub Actions, post-deploy steps, rollback strategies, environment management, hosting platforms
- **drafts-revisions.md** (296 lines) — Drafts and revisions: provisional/saved/unpublished draft types, autosave mechanics, creating and applying drafts, field-level change tracking and merge behavior, revisions with `hasRevisions()` and `maxRevisions`, all status-checking methods (`getIsDraft`, `getIsRevision`, `getIsCanonical`, etc.), draft ownership and peer permissions, query parameters, plugin considerations for `afterSave()` side effects

**New reference files (craft-site skill):**
- **search.md** (270 lines) — Search system: full search syntax (boolean, field-targeted, wildcards, exact phrases), Twig search queries with pagination, search configuration (`defaultSearchTermOptions`, fulltext settings), search indexing internals (`searchindex` table, default indexed attributes), rebuilding commands, score and ranking
- **feeds.md** (265 lines) — Feeds and XML output: complete RSS 2.0, Atom, and JSON Feed templates, XML sitemap and sitemap index, custom routes in `config/routes.php`, date filters (`|rss`, `|atom`), multi-site feed routes

**Expanded reference files:**
- **element-index.md** (368 → 631 lines) — New "Extending Element Indexes via Events" section: 11 event reference table, adding custom columns to Users index (register + render + query prep), adding sidebar sources, custom bulk actions (full `ElementAction` class pattern), condition rules, metadata, sort options, built-in User sources
- **permissions.md** (473 → 503 lines) — Rewritten dynamic permissions section: parameterized UID convention (following Craft's `assignUserGroup:{uid}` pattern), `Permissions` class constants with namespace, `doesUserHavePermission()` resolution logic (admin bypass, lowercase storage), permission property table (`label`, `nested`, `info`, `warning`)

### Skill boundary refinement

- **headless.md** moved from craftcms to craft-site — consuming GraphQL APIs, preview tokens, and front-end framework integration (Next.js, Nuxt, Astro) are site-building concerns, not backend PHP development. Building custom GraphQL types/mutations remains in craftcms via `graphql.md`.
- **craftcms SKILL.md** — Added explicit "Do NOT trigger for consuming GraphQL/headless APIs from front-end frameworks" clause. Removed "headless, headless CMS" from triggers. Narrowed GraphQL triggers to "GraphQL custom types, GraphQL custom mutations, GraphQL schema building".
- **craft-site SKILL.md** — Added headless consumer triggers: "headless, headless CMS, GraphQL queries, preview tokens, Next.js, Nuxt, Astro, consuming GraphQL API, front-end framework integration".

### Trigger keyword expansion

- **craftcms SKILL.md** — Added trigger keywords for all 7 new reference topics: `EVENT_AUTHORIZE_VIEW`, `EVENT_AUTHORIZE_SAVE`, `canView`, `canSave`, `canDelete`, element authorization, defense-in-depth, query scoping, `EVENT_BEFORE_PREPARE`, session invalidation, `passwordResetRequired`, elevated session, `Table::SESSIONS`, custom field type build, field type development, `normalizeValue`, `serializeValue`, `inputHtml`, `BaseCondition`, `ElementCondition`, condition rule, condition builder, system messages, `composeFromKey`, email sending, Mailer, deployment, zero-downtime deploy, atomic deploy, `craft up`, `project-config/apply`, `allowAdminChanges`, drafts, revisions, provisional draft, `canCreateDrafts`, `applyDraft`, `getIsDraft`, `getIsRevision`.
- **craft-site SKILL.md** — Added trigger keywords: RSS feed, Atom feed, JSON Feed, XML sitemap, `feed.xml`, `sitemap.xml`, `|rss`, `|atom`, search page, search results, `.search()`, search index, search form, search configuration.

### Trigger evaluation

- Ran trigger evaluation against 20 queries per skill (10 should-trigger, 10 should-not-trigger). Results: craftcms 100%, craft-site 100% after headless.md move.

### Quality audit (gap files)

- All 9 new files reviewed for grammar, cross-references, code accuracy, and style consistency
- Fixed: `can*()` method visibility description (public, not protected), `ddev craft db/search-indexes` → `ddev craft search/reindex`, null-unsafe sitemap template, null-unsafe category field access in RSS, wrong docs URL in email.md, GraphQL methods description, queue job naming convention, sessions table schema, deployment pipeline commands, `hasDrafts()` code example
- Cross-reference audit: 90+ references verified, zero broken links in new files

## 1.1.1 -- 2026-04-14

### Fixed

- **craft-twig-guidelines**: Variable naming convention was incorrectly enforcing snake_case for multi-word Twig variables and flagging camelCase as an error. Now correctly requires camelCase (`buttonText`, `containerClass`) and flags snake_case (`button_text`, `container_class`) as wrong.
- **craft-project-setup**: Project template `templates.md` said "No camelCase" — now says multi-word uses camelCase with examples.
- **README**: Updated install instructions to include marketplace registration step.

## 1.1.0 -- 2026-04-12

Major expansion across all skills. Content modeling overhaul, 10 new reference files, new project setup skill, validation coverage, and storage architecture documentation.

### New

- **craft-project-setup** skill -- scaffolds CLAUDE.md and .claude/rules/ tailored to project type (plugin, site, module, hybrid)
- **multi-site-patterns.md** -- language switchers, hreflang, 4 site architectures, cross-site queries, translations, site detection
- **plugin-vite.md** -- VitePluginService for CP asset bundles, HMR, TypeScript/Vue, DDEV dev server
- **testing.md** -- Pest + Codeception, element factories, HTTP/queue/DB assertions, mocking, console/event testing
- **headless.md** -- headlessMode, GraphQL API, CORS, preview tokens, hybrid patterns, Next.js/Nuxt/Astro
- **configuration.md** -- general.php fluent API, .env variables, app.php overrides, Redis, config priority order
- **users-and-permissions.md** -- CMS editions, user groups, addresses, permissions architecture, field layout UI elements
- **composition-patterns.md** -- split from atomic-patterns.md; molecules, organisms, structural embed, component creation
- **feed-me.md** plugin reference -- data import, field mapping, duplicate handling, CLI
- **imager-x.md** plugin reference -- batch transforms, named presets, effects, optimizers, external storage

### Changed

- **craft-content-modeling**: major rewrite
  - Accurate entrification timeline (4.4 CLI, 5.0 CP disabled, 6.0 removal) replacing incorrect "deprecated" language
  - Entry type visual identity (icon, color, description, group, uiLabelFormat)
  - Field instances: reuse fields via per-context overrides instead of creating duplicates
  - Reserved field handles: 83+ handles documented with synonym table and active check instruction
  - CKEditor vs Matrix vs Content Block decision guide
  - Asset volumes/filesystems/transforms: three-layer model, architecture decisions, subpath rules
  - Storage architecture: five-table model, JSON keyed by instance UID, nested set structures, draft reuse
  - Project config: `project-config/touch` + `craft up` workflow as hard rule
  - CMS editions, section properties (maxAuthors, previewTargets), propagation methods
- **craft-php-guidelines**: restructured from 80-line stub to full skill with 5 reference files (PHPDoc standards, class organization, naming conventions, templates/patterns, tooling)
- **craftcms/architecture.md**: added plugin editions (declaring, checking, feature gating, CMS edition requirements) and Yii2 core validators (17 validators, conditional validation, custom messages)
- **craftcms/elements.md**: added CP edit pages (getCpEditUrl, asCpScreen, propagation UI, field layout designer, preview targets)
- **craft-twig-guidelines**: `???` operator guidance softened (OK with empty-coalesce or SEOmatic installed)
- **atomic-patterns.md**: split into atoms (367 lines) and composition (382 lines)
- All 6 agents: added environment rules (DDEV-only, symlinked paths, ECS scope), skill declarations, element template planning
- All skills: companion skills system (each skill declares co-dependencies for cross-loading)

### Fixed

- `web_fetch` to `WebFetch` across 22 files (matching actual tool name)
- `#ddev-generated` pitfall and example in ddev skill (was inverted/contradictory)
- Reserved handles used in content-patterns.md examples (`icon` to `topicIcon`/`serviceIcon`, `language` to `codeLanguage`)
- Bare `php craft` command in content-modeling (now `ddev craft`)
- Stale path reference in quality.md
- Portfolio field handle mismatch (`.myFeatured()` to `.featured()`)
- Content Block return type (was "Entry", now correctly "ContentBlock")
- Matrix Twig include missing `only` keyword
- Sprig plugin reference missing from craft-site SKILL.md table
- dateModified guidance: was self-contradictory ("never edit YAML" + "edit dateModified"), now uses `project-config/touch`

## 1.0.0 -- 2026-04-09

Initial release. 6 skills, 6 agents, project template, 20 plugin references.
