---
name: craftcms
description: "Craft CMS 5 plugin and module development in PHP. Covers elements, element queries, services, models, records, controllers, migrations, queue jobs, console commands, field types, events, Twig extensions, widgets, permissions, GraphQL, testing, and debugging."
when_to_use: "Triggers on: beforePrepare()/afterSave()/defineSources()/defineTableAttributes()/attributeHtml(), BaseNativeField, EVENT_REGISTER_*/DEFINE_*/BEFORE_*/AFTER_*, CraftVariable, custom element or field type (normalizeValue/inputHtml), webhook, batch job, CP section, dashboard widget, utility page, element action/exporter/condition, registerUserPermissions, requirePermission vs requireAdmin, kebab-case permissions, EVENT_DEFINE_RULES on Entry (fieldId + ownerId must be set), project-config/apply/write, EVENT_DEFINE_SIDEBAR_HTML/toolbar buttons, metaFieldsHtml, VueAdminTable, getIsMultiSite/refreshSites stale after new site, deleteSite phantom sites, siteId filter lost, UTC datetime/strtotime drift, ['like'] tuple matches nothing, configWarning. Always use when writing, editing, or reviewing Craft plugin/module PHP (even when no API is named) or saveField()/saveEntryType() from scripts. Plugin work: also load craft-plugins. Do NOT trigger for front-end Twig (craft-site) or content modeling (craft-content-modeling)."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft CMS 5 — Extending (Plugins & Modules)

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Extending Craft CMS 5 with PHP: plugins, modules, custom element and field types, backend integrations. Site work (content modeling, Twig, plugin selection) belongs to `craft-site` and `craft-content-modeling`.

## Companion Skills

Always load **`craft-php-guidelines`** (PHP standards, required for any PHP) and **`ddev`** (every command runs through DDEV). Also load: **`craft-garnish`** for CP JavaScript, **`craft-pest`** for tests (its rollback is opt-in and its env overrides are cwd-bound: both write silently to the dev database), **`craft-cloud`** when `craft-cloud.yaml` or `craftcms/cloud` is present, **`craft-mcp`** for MCP servers, OAuth and personal access tokens [5.12+], **`craft-plugins`** for plugin-specific work. Full notes: `task-routing.md` (Companion skills).

Docs: https://craftcms.com/docs/5.x/extend/ · class reference https://docs.craftcms.com/api/v5/ · generator https://craftcms.com/docs/5.x/extend/generator.html. Use `WebFetch` when a reference doesn't cover enough.

## Common Pitfalls (Cross-Cutting)

- Always `addSelect()` in `beforePrepare()`: the Craft convention, additive when several extensions contribute columns.
- Queue workers run in primary site context: use `->site('*')` for cross-site queries (`queue-jobs.md`).
- Never put `id` in `getConfig()`: project config uses UIDs.
- Logic belongs in services, not models or controllers. `DateTimeHelper` in elements/queries, `Carbon` in services, never mixed in one class.
- Modules register template roots, translations and `controllerNamespace` manually (`plugin-vs-module.md`).
- Never hardcode `/admin`: `cpTrigger` is configurable. `UrlHelper::cpUrl()` in PHP, `cpUrl()` in Twig.
- Split settings pages: load the full settings model, update it, then `savePluginSettings()`; passing `getBodyParams()` straight in drops unsubmitted keys (`cp.md`).
- **A route or query param named `token`** collides with Craft's `tokenParam`: 400 before your controller runs (`controllers.md`, Reserved request params).
- **`EVENT_DEFINE_RULES` on `Entry::class` runs for every entry**, including nested entries built before `fieldId`/`ownerId` exist, where `getType()` throws `Either \`sectionId\` or \`fieldId\` + \`ownerId\` must be set on the entry.` Always add the rule, decide in `'when'` behind an `isset($entry->fieldId) || isset($entry->sectionId)` guard, validate with a `Validator` subclass (`events.md`, Validation Rules on Core Elements From a Module).
- **`project-config/write` empties `config/project/` and rewrites it from the DB.** On a stale local DB it deletes teammates' YAML. Run `craft up` first, require a clean `project-config/diff`, and check `git diff -- config/project` afterwards. Schema saves from PHP belong in a migration or console command, never a bare bootstrap script (YAML is only flushed on `EVENT_AFTER_REQUEST`). See `deployment.md` (project-config/write safely) and `migrations.md` (Project config writes outside a request).
- Any non-underscore-prefixed template in a plugin's `templates/` is **directly routable in the CP**, bypassing `beforeAction()` gates. Underscore-prefix the rest (`cp.md`, CP template routing bypasses controllers).

## Reference Files

Read only what the task needs; multiple files often apply. **The full task index (130+ task-to-section mappings) is `task-routing.md`: grep it for a keyword from the task.**

**Task examples:**
- "Build a custom element type" → `elements.md` (Architecture first) + `element-index.md` + `fields.md` + `migrations.md` + `cp.md`
- "Add a webhook endpoint" → `controllers.md` + `events.md`
- "Queue job that syncs elements" → `queue-jobs.md` + `elements.md` + `debugging.md`
- "Require a field on one entry type / nested entry fails: Either `sectionId` or `fieldId` + `ownerId` must be set" → `events.md` (Validation Rules on Core Elements From a Module)
- "project-config/write deleted YAML" → `deployment.md`; "saveField()/saveEntryType() from a script changed nothing in YAML" → `migrations.md` (Project config writes outside a request)
- "Create or delete sites from code / siteId filter lost after creating a site / phantom sites after deleteSite" → `architecture.md` (Creating or deleting sites at runtime)
- "'Changed since' filter off by hours" → `architecture.md` (Those strings are naive UTC); "`['like', ...]` returns nothing" → `architecture.md` (Element-query param setters don't take Yii operator tuples)
- "Edit-screen sidebar panel / toolbar split button / metaFieldsHtml" → `cp-ui-patterns.md` (Element Edit Screen) + `elements.md`
- "Plugin settings page, tabs, config-file override warning" → `cp.md` (Settings Pages)
- "Install fails: too many keys" → `migrations.md`; "Upgrade to 5.12" [5.12+] → `upgrade-5.12.md`
- Tests → load `craft-pest`; Cloud compatibility → load `craft-cloud` (`plugin-development.md`); headless front ends → `craft-site` (`headless.md`)
- "Which Craft version does this feature need? / What can this project use on its version?" → grep `version-table.md` for the feature or version (every version tag in the pack, with older-version alternatives); it is large, so don't read it whole

**Large files: read the Contents block, then only the section.** `architecture.md`, `config-app.md`, `config-general.md`, `controllers.md`, `cp.md`, `cp-ui-patterns.md`, `element-index.md`, `elements.md`, `events.md`, `graphql.md` and `permissions.md` start with a Contents block that gives each section's line range. Read the first 40 lines, then Read only the section you need with `offset`/`limit`, never the whole file.

| Task | Read | ~Tokens |
|------|------|--------:|
| Full task index: task or symptom → file and section; full pitfall and companion notes | `references/task-routing.md` | 4.9K |
| Elements: lifecycle, queries, status, authorization, drafts, propagation, field layouts, user edit screens, events | `references/elements.md` | 8.4K |
| Element index: sources, table/card attributes, status pills, sort, conditions, actions, exporters, relation-field display | `references/element-index.md` | 6.1K |
| Services, models, records, project config, runtime site creation/deletion, MemoizableArray, API clients, validators | `references/architecture.md` | 7.4K |
| Plugin vs module differences, module template-root/translation/console registration | `references/plugin-vs-module.md` | 0.6K |
| Controllers: CP CRUD, webhooks, API endpoints, action routing, authorization | `references/controllers.md` | 3.9K |
| CP templates, form macros, settings pages, navigation, permissions, read-only mode | `references/cp.md` | 7.2K |
| CP components: widgets, utility pages, slideouts, ajax, editable tables, modals, alerts | `references/cp-components.md` | 1.8K |
| CP UI patterns: tri-state controls, status indicators, CSS tokens, condition builders, asset bundles, edit-screen sidebar/toolbar | `references/cp-ui-patterns.md` | 3.4K |
| Migrations, Install.php, foreign keys, indexes, idempotency | `references/migrations.md` | 3.9K |
| Queue jobs: BaseJob, TTR, retry, progress, batch jobs, site context | `references/queue-jobs.md` | 4.2K |
| Console commands, options, progress, output helpers, resave actions | `references/console-commands.md` | 6.0K |
| Debugging, performance, profiling, Xdebug, logging | `references/debugging.md` | 4.6K |
| PHPStan, ECS, Rector, CI, review checklist | `references/quality.md` | 3.5K |
| Testing: pointer to `craft-pest` + Codeception basics | `references/testing.md` | 0.6K |
| Field types, native fields, field layout UI elements, FieldLayoutBehavior | `references/fields.md` | 3.6K |
| Events: registration, EVENT_DEFINE_RULES, custom events, behaviors, Twig extensions, utilities, widgets, filesystems | `references/events.md` | 4.4K |
| GraphQL: auth, tokens, types, queries, mutations, directives, resolvers | `references/graphql.md` | 8.4K |
| Plugin Vite: CP asset bundles, HMR, TypeScript, Vue | `references/plugin-vite.md` | 2.7K |
| Headless & hybrid: headlessMode, CORS, preview tokens | craft-site skill `references/headless.md` | 3.4K |
| GeneralConfig (system, routing, security, users, sessions, search, assets, images) | `references/config-general.md` | 8.4K |
| Craft version table, generated from the pack's version tags | `references/version-table.md` | 13.3K |
| GeneralConfig (content, templates, performance, GC, localization, headless, GraphQL) | `references/config-general-extended.md` | 7.2K |
| App config: cache, session, queue, mutex (Redis, one database each), mailer, search, logging, CORS, DB replicas, modules | `references/config-app.md` | 8.0K |
| Config bootstrap: env vars, aliases, App::parseEnv, custom.php, db.php, routes.php | `references/config-bootstrap.md` | 3.6K |
| Caching: template cache, data cache, static caching, CDN, invalidation | `references/caching.md` | 5.2K |
| Permissions: handles, user groups, registration, checking, events | `references/permissions.md` | 4.7K |
| Element authorization: four-layer defense, can*() methods, query scoping | `references/element-authorization.md` | 4.6K |
| Sessions & auth: session model, auth tokens, invalidation, elevated sessions | `references/sessions-and-auth.md` | 3.0K |
| Identity protocols: SSO/OIDC logout, signing algs, issuer vs tenancy, SCIM | `references/identity-protocols.md` | 1.3K |
| Custom field types: value lifecycle, settings, input HTML, validation, GraphQL | `references/field-types-custom.md` | 3.5K |
| Conditions framework: custom condition rules, registration | `references/conditions.md` | 2.3K |
| Email: system messages, programmatic sending, templates, events | `references/email.md` | 2.4K |
| Deployment: pipeline, project-config/write safely, zero-downtime, CI/CD, rollback | `references/deployment.md` | 2.5K |
| Drafts & revisions: provisional drafts, autosave, applying, merge | `references/drafts-revisions.md` | 2.5K |
| Upgrading 5.11 to 5.12.4 [5.12+]: behaviour changes, plugin-code changes, deploy steps | `references/upgrade-5.12.md` | 2.1K |
