# Skills Overview

9 skills covering plugin development (extending Craft), site development (content modeling, Twig templates, front-end architecture), and Craft Cloud serverless hosting. Reference files spread across each skill's `references/` directory.

## How Skills Load

Skills trigger automatically based on keywords in your prompt. Each skill also declares **companion skills** that load alongside it, so related knowledge is always available. You rarely need to load a skill manually.

Every skill has explicit "NOT for" boundaries to prevent cross-skill misfires. For example, asking about Twig templates triggers `craft-site`, not `craftcms` -- even though both involve Craft CMS.

---

## craftcms

**Track:** Plugin Development
**Reference files:** 28 (approximately 12,950 lines)
**SKILL.md:** 192 lines

The largest skill in the pack. Covers the entire surface for extending Craft CMS 5 through plugins and modules: elements, element queries, services, models, records, controllers, migrations, queue jobs, console commands, field types (built-in and custom), events, behaviors, Twig extensions, utilities, widgets, filesystems, permissions, debugging, testing, GraphQL, and all configuration (general.php, app.php, bootstrap, caching, deployment, drafts/revisions, email, sessions, conditions).

**When it triggers:** Any prompt involving PHP plugin or module development. Keywords include custom element types, custom field types, webhooks, API endpoints, queue jobs, migrations, CP settings pages, Craft configuration, permissions, GraphQL schema building, controllers, events, ECS/PHPStan, deployment, and CI/CD.

**Companion skills:** `craft-php-guidelines` (always), `ddev` (always), `craft-garnish` (when CP JavaScript is involved).

**Boundary:** Does NOT trigger for front-end Twig templates, content modeling decisions, or consuming GraphQL from front-end frameworks. Those belong in `craft-site` and `craft-content-modeling`.

---

## craft-php-guidelines

**Track:** Plugin Development
**Reference files:** 5 (approximately 520 lines)
**SKILL.md:** 138 lines

PHP coding standards and conventions for Craft CMS 5. PHPDoc requirements (every class, method, property), section headers with `=========` separators, class organization, naming conventions (services, queue jobs, records, events, enums), control flow patterns (early returns, match over switch), ECS and PHPStan configuration, and the verification checklist.

**When it triggers:** Any prompt involving writing, editing, or reviewing PHP in a Craft plugin or module. Also triggers when running ECS, PHPStan, or scaffolding with `ddev craft make`.

**Companion skills:** `craftcms` (always), `ddev` (always).

**Boundary:** Does NOT trigger for front-end Twig templates (use `craft-twig-guidelines`) or CP JavaScript (use `craft-garnish`).

---

## craft-content-modeling

**Track:** Site Development
**Reference files:** 5 (approximately 1,160 lines)
**SKILL.md:** 297 lines

Content architecture for Craft CMS 5. Covers section types (Single, Channel, Structure), entry types (global, visual identity, reserved handles), field types and field instances, Matrix configuration (CKEditor vs Matrix vs Content Block decision guide), relations and eager loading, multi-site propagation, entrification (migrating categories/tags/globals to entries), CMS editions, and the reuse-first field workflow that audits existing fields before proposing new ones.

**When it triggers:** Any prompt involving content architecture decisions: creating sections, choosing field types, configuring Matrix, setting up relations, planning multi-site content, designing field layouts, or planning taxonomies.

**Companion skills:** `craft-site` (always), `craft-twig-guidelines` (always), `ddev` (always).

**Boundary:** Does NOT trigger for PHP plugin development, custom field type code, front-end Twig templates, or build chain configuration.

---

## craft-site

**Track:** Site Development
**Reference files:** 41 (approximately 8,825 lines) -- 18 core references + 23 plugin references
**SKILL.md:** 177 lines

Front-end Twig development with atomic design patterns. Covers the full site template surface: atoms, molecules, organisms, the props/extends/block pattern, layout chains, view routing, content builders, image presets, Tailwind CSS conventions (named-key collections, brand tokens, utilities prop), JavaScript boundaries (Alpine/DataStar/Vue decision tree), Vite build chain, multi-site patterns (language switchers, hreflang), front-end authentication (login, registration, password reset, profile editing), search, feeds (RSS, Atom, JSON Feed, XML sitemap), headless/hybrid patterns (GraphQL API, preview tokens, Next.js/Nuxt/Astro), and third-party integration (GTM, analytics, CMP).

The plugin reference library covers 23 Craft plugins with detailed configuration, Twig/PHP API, and common pitfalls: SEOMatic, Blitz, Formie, ImageOptimize, CKEditor, Sprig, Element API, Retour, Navigation, Hyper, Colour Swatches, Password Policy, Typogrify, Cache Igniter, Knock Knock, Elements Panel, Sherlock, Embedded Assets, Amazon SES, Timeloop, Feed Me, Imager-X, and Vite.

**When it triggers:** Any prompt involving Craft CMS front-end templates, components, layouts, Vite setup, responsive images, search pages, feeds, authentication flows, or plugin integration (Blitz caching, SEOMatic, Sprig, Formie).

**Companion skills:** `craft-twig-guidelines` (always), `craft-content-modeling` (always), `ddev` (always).

**Boundary:** Does NOT trigger for PHP plugin/module development or content modeling decisions without a template context.

---

## craft-twig-guidelines

**Track:** Site Development
**Reference files:** 0 (self-contained at 314 lines)
**SKILL.md:** 314 lines

Twig coding standards for Craft CMS 5 templates. Variable naming (camelCase, no abbreviations), null handling (`??` operator, `???` with empty-coalesce plugin), whitespace control (`{%-` trimming, never `{%- minify -%}`), include isolation (`only` keyword always required), Craft Twig helpers (`{% tag %}`, `tag()`, `attr()`, `|attr`, `|parseAttr`, `|append`, `svg()`), `collect()` conventions for props and class collections, and comment headers with `=========` separators.

**When it triggers:** Any prompt involving writing, editing, or reviewing `.twig` files in a Craft CMS project -- even small edits.

**Companion skills:** `craft-site` (always), `craft-content-modeling` (always).

**Boundary:** Does NOT trigger for Twig architecture patterns or template routing (use `craft-site`), PHP code (use `craft-php-guidelines`), or content modeling (use `craft-content-modeling`).

---

## craft-garnish

**Track:** Plugin Development
**Reference files:** 5 (approximately 2,100 lines)
**SKILL.md:** 63 lines

Garnish -- Craft CMS's undocumented built-in JavaScript UI toolkit for the control panel. Covers the class system (`Garnish.Base.extend`, inheritance, events, listeners, destroy lifecycle), UI widgets (Modal, HUD, DisclosureMenu, MenuBtn, Select, CustomSelect, ContextMenu), drag system (BaseDrag, DragSort, DragDrop, DragMove), form widgets (NiceText, CheckboxSelect, MixedInput, MultiFunctionBtn), utilities (key constants, custom jQuery events, ARIA/focus management), and Craft integration (GarnishAsset, webpack externals, `Craft.*` class pattern, Twig JS blocks).

This is the only documentation that exists for Garnish -- the official Craft docs do not cover it. Source-validated against the Craft CMS repository.

**When it triggers:** Any prompt involving JavaScript in the Craft CP: modals, drag-and-drop, disclosure menus, menu buttons, selection interfaces, CP asset bundles, Garnish classes, or CP memory leak debugging.

**Companion skills:** `craftcms` (when PHP asset bundles or CP templates are involved), `craft-php-guidelines` (when editing PHP files). Skips both for pure JS tasks to save context.

**Boundary:** Does NOT trigger for front-end JavaScript (Alpine, Vue, htmx) or Twig templates.

---

## ddev

**Track:** Shared (both plugin and site development)
**Reference files:** 0 (self-contained at 128 lines)
**SKILL.md:** 128 lines

DDEV local development environment for Craft CMS. Covers config.yaml settings, shorthand commands (`ddev composer`, `ddev craft`, `ddev npm`), add-ons (Redis, Mailpit), custom commands, Vite dev server exposure, database import/export, Xdebug toggling, site sharing, and troubleshooting.

**When it triggers:** Any prompt involving `ddev` commands, `.ddev/config.yaml` configuration, local development environment setup, PHP/Node version management, or container troubleshooting.

**Companion skills:** `craftcms` (always), `craft-php-guidelines` (always).

**Boundary:** Does NOT trigger for production deployment, CI/CD, or Docker outside of DDEV.

---

## craft-project-setup

**Track:** Shared (both plugin and site development)
**Reference files:** 0 (self-contained at 150 lines, plus template files)
**SKILL.md:** 150 lines

Interactive project scaffolding. Detects project type from `composer.json`, `.ddev/config.yaml`, and directory structure. Generates a tailored `CLAUDE.md` and `.claude/rules/` directory for plugin, site, module, hybrid, or monorepo projects.

**When it triggers:** Prompts like "set up Claude for this Craft project", "initialize CLAUDE.md", "scaffold project config", or starting work in a new Craft project that lacks configuration.

**Companion skills:** None at activation (it generates config that references other skills).

**Boundary:** Does NOT trigger for non-Craft projects, installing Craft itself, or writing code.

---

## craft-cloud

**Track:** Shared (both plugin and site development, when hosted on Cloud)
**Reference files:** 12
**SKILL.md:** 114 lines

Craft Cloud, Pixel & Tonic's serverless hosting platform. Covers the `craft-cloud.yaml` config file, the Build → Migrate → Release deploy pipeline, the `craftcms/cloud` extension package (with `App::isEphemeral()` patterns and the `cloud.esi(...)` Twig helper), edge image transforms via Cloudflare Images, edge static caching with `cache.rules`, MySQL 8 / Postgres 15 constraints (no MariaDB, no `tablePrefix`), Console-based command runner and scheduled cron (hourly minimum), auto-processed queue jobs (15-minute cap), plugin Cloud-compatibility requirements, and self-hosted → Cloud migration.

**When it triggers:** Prompts like "deploy to Craft Cloud", "configure `craft-cloud.yaml`", "make this plugin Cloud-compatible", "migrate to Craft Cloud", or any mention of `App::isEphemeral()`, `cloud.esi()`, the `craftcms/cloud` package, or `CRAFT_CLOUD_*` env vars. Also auto-loaded as a companion to `craftcms` and `craft-site` when the project is detected as a Cloud project (`craft-cloud.yaml` at repo root, or `craftcms/cloud` in `composer.json`).

**Companion skills:** `craftcms` (for plugin Cloud-compat work), `craft-site` (for edge caching / ESI in templates), `ddev` (for local-dev parity), `craft-php-guidelines` (for plugin PHP edits).

**Boundary:** Does NOT cover generic Craft deployment (Forge, Servd, bare metal — see `craftcms/deployment.md`). Does NOT cover general DDEV usage unrelated to Cloud parity.

---

## Skill Boundaries at a Glance

Understanding which skill handles what prevents misfires and gets you better results.

| Question | Skill |
|----------|-------|
| "How do I build a custom element type?" | `craftcms` |
| "What section type should I use for a blog?" | `craft-content-modeling` |
| "Build a card component with props" | `craft-site` |
| "What's the naming convention for services?" | `craft-php-guidelines` |
| "How do I add a modal in my plugin's CP?" | `craft-garnish` |
| "How do I expose the Vite dev server in DDEV?" | `ddev` |
| "Set up this project for Claude Code" | `craft-project-setup` |
| "Should I use camelCase in Twig variables?" | `craft-twig-guidelines` |
| "Configure Redis for caching" | `craftcms` (config-app.md) |
| "Build a language switcher" | `craft-site` (multi-site-patterns.md) |
| "Plan a multi-site content model" | `craft-content-modeling` |
| "Add drag-to-reorder to my settings page" | `craft-garnish` |
| "Deploy Craft to production" | `craftcms` (deployment.md) |
| "Set up login and registration forms" | `craft-site` (auth-flows.md) |
