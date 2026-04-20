# Changelog

## 1.2.0 -- 2026-04-20

Complete rewrite of configuration reference and expansion of 4 thin reference files. Full coverage of all Craft CMS 5 config settings, mail transport, search performance, app component configuration, migrations, queue jobs, code quality tooling, and CP templates. Agent architecture overhaul with explicit build-verify gates, mandatory todo lists, and removal of the redundant simplifier agent. Content modeling improvement: reuse-first field workflow. New Garnish JS skill for CP JavaScript development. Quality audit with reference file splits and description optimization across all 8 skills. Gap analysis: 9 new reference files (element authorization, sessions, custom field types, conditions, email, deployment, drafts/revisions, search, feeds) filling 12 identified coverage gaps. Headless/GraphQL consumer patterns moved from craftcms to craft-site. New /docs directory with getting-started guide, skills overview, 43-prompt guide, agent documentation, and contributing guide. GitHub issue templates upgraded to YAML forms with structured data collection.

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
