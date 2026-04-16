# Changelog

## 1.2.0 -- unreleased

Complete rewrite of configuration reference and expansion of 4 thin reference files. Full coverage of all Craft CMS 5 config settings, mail transport, search performance, app component configuration, migrations, queue jobs, code quality tooling, and CP templates. Agent architecture overhaul with explicit build-verify gates, mandatory todo lists, and removal of the redundant simplifier agent. Content modeling improvement: reuse-first field workflow.

### Content modeling

- **craft-content-modeling SKILL.md** — Added "Reuse-First Workflow" section that enforces field pool audit before proposing new fields. Agents must enumerate existing fields via `config/project/fields/`, classify each proposed field as reuse / reuse-with-review / create-new, and present a decision table. Also documents multi-instance vs single-instance field types (Matrix, Content Block, Addresses are single-instance) with reuse caveats. Addresses [#3](https://github.com/michtio/craftcms-claude-skills/issues/3).

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

### New

- **config-general.md** — all 130+ GeneralConfig settings across 17 categories with implications, dangerous interactions, and production hardening guidance
- **config-app.md** — all app.php components: cache (DB/Redis/APCu/Memcached), session, queue, mutex, mailer (SMTP/Gmail/Sendmail + AWS SES/Mailgun/Postmark/Sendgrid plugins), search component, logging, CORS, database replicas, module registration, multi-site maxSites
- **config-bootstrap.md** — environment variables, CRAFT_* auto-mapping, aliases (@web/@webroot/custom), config priority order, fluent API, custom.php, db.php, routes.php, htmlpurifier configs
- Web vs console split explanation — why app.web.php and app.console.php exist, decision table for which components go in which file

### Changed

- **elements.md** — Added "Attributes, Field Values, and Mass Assignment" section covering the full value flow: native attributes vs custom field values (`CustomFieldBehavior`), how `ElementsController` splits POST data into two streams, the Yii2 safe attribute gate (`SCENARIO_LIVE`), the silent drop trap when native attributes lack validation rules, `setFieldValue`/`setFieldValues`/`setFieldValueFromRequest` usage, custom field normalization/serialization lifecycle, and native field layout registration. New pitfall entry for the safe attribute trap. Cross-reference from architecture.md validator table.
- **migrations.md** (101 → 401 lines) — content migrations (creating sections/fields/entry types programmatically), common schema patterns, multi-site migrations, project config interaction, safeDown patterns, `craft migrate` vs `craft up` comparison
- **queue-jobs.md** (125 → 402 lines) — queue infrastructure (daemon vs web runner), retry strategies, failed job handling, long-running patterns, priority, built-in jobs table, queue health monitoring
- **quality.md** (177 → 405 lines) — ECS deep dive with violation table, PHPStan levels 0-9, craftcms/phpstan package, Rector for automated refactoring, CI/CD GitHub Actions workflow, pre-commit hooks. Removed duplicated Pest content (cross-references testing.md)
- **cp.md** (252 → 576 lines) — CP navigation, plugin settings pages, utility pages (full pattern), dashboard widgets (full pattern), slideout editors, Ajax endpoints, CP alerts, additional form macros, condition builders
- **craftcms SKILL.md** — configuration reference split from 1 file to 3, with expanded task routing examples (search, mail, env vars, GraphQL tokens)
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
