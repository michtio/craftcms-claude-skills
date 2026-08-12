---
name: craftcms
description: "Craft CMS 5 plugin and module development — extending Craft with PHP. Covers elements, element queries, services, models, records, controllers, migrations, queue jobs, console commands, field types, native fields, events, behaviors, Twig extensions, widgets, filesystems, permissions, project config, GraphQL, testing, and debugging. Triggers on: beforePrepare()/afterSave()/defineSources()/defineTableAttributes()/attributeHtml(), MemoizableArray, BaseNativeField, EVENT_REGISTER_*/DEFINE_*/BEFORE_*/AFTER_*, CraftVariable, custom element or field type (normalizeValue/serializeValue/inputHtml), webhook, API endpoint, queue/batch job, CP section, dashboard widget, utility page, element action/exporter/condition, registerUserPermissions, requirePermission vs requireAdmin, kebab-case permission handles, allowAdminChanges, canView/canSave/canDelete, defineRules, elevated session, project-config/apply, drafts/revisions, element edit sidebar (EVENT_DEFINE_SIDEBAR_HTML) + toolbar buttons, metaFieldsHtml, VueAdminTable, GeneralConfig, getIsMultiSite/refreshSites stale after creating a site, deleteSite phantom sites, element query stops filtering by siteId, naive UTC datetime columns and strtotime drift, element-query ['like'] tuple matches nothing, configWarning config-file overrides. Always use when writing, editing, or reviewing Craft plugin/module PHP — even when no API is named. For plugin-specific work also load craft-plugins. Do NOT trigger for front-end Twig (craft-site) or content modeling (craft-content-modeling)."
---

# Craft CMS 5 — Extending (Plugins & Modules)

Reference for extending Craft CMS 5 through plugins and modules. Covers everything from elements and services to controllers, migrations, fields, and events.

This skill is scoped to **extending** Craft — building plugins, modules, custom element types, field types, and backend integrations. For site/platform development (content modeling, sections, entry types, Twig templating, plugin selection), see the `craft-site` skill.

## Companion Skills — Always Load Together

When this skill triggers, also load:

- **`craft-php-guidelines`** — PHPDoc standards, section headers, naming conventions, class organization, ECS/PHPStan, verification checklist. Required for any PHP code.
- **`ddev`** — All commands run through DDEV. Required for running ECS, PHPStan, scaffolding, and tests.
- **`craft-garnish`** — When working on CP JavaScript, asset bundles, or interactive CP components. Covers Garnish's class system, UI widgets (Modal, HUD, DisclosureMenu, Select), drag system, and the Craft.* JS class pattern.
- **`craft-pest`** — When writing, running, fixing, or reviewing tests. Covers the `markhuot/craft-pest-core` harness, database isolation (its rollback is opt-in and its env overrides are cwd-bound — both cause silent writes to the dev database), factories, HTTP/queue/DB assertions, and CI test jobs.
- **`craft-cloud`** — When the project is hosted on Craft Cloud (detect via `craft-cloud.yaml` at the repo root or `craftcms/cloud` in `composer.json`). Required for plugin Cloud-compatibility constraints — `App::isEphemeral()` guards, asset-bundle CDN publishing, 15-minute queue-job cap, `csrfInput()` function over raw token output, and the `cloud/up` deploy lifecycle events.

## Documentation

- Extend guide: https://craftcms.com/docs/5.x/extend/
- Class reference: https://docs.craftcms.com/api/v5/
- Generator: https://craftcms.com/docs/5.x/extend/generator.html

Use `WebFetch` on specific doc pages when a reference file doesn't cover enough detail.

## Common Pitfalls (Cross-Cutting)

- Always use `addSelect()` in `beforePrepare()` — it's the Craft convention and safely additive when multiple extensions contribute columns.
- Queue workers run in primary site context — use `->site('*')` for cross-site queries.
- Including `id` in `getConfig()` — project config uses UIDs, never database IDs.
- Business logic in models or controllers — services are where logic belongs.
- Modules need manual template root, translation, and controllerNamespace registration — nothing is automatic.
- `DateTimeHelper` in elements/queries, `Carbon` in services — never mix in the same class.
- Hardcoding `/admin` in CP URLs — `cpTrigger` is configurable. Use `UrlHelper::cpUrl()` in PHP, `cpUrl()` in Twig.
- Passing `$request->getBodyParams()` directly to `savePluginSettings()` on split-settings pages — only submitted keys persist, other settings are silently dropped. Load the full settings model first, update properties, then save.
- **Naming a route or query param `token`** — it collides with Craft's reserved `tokenParam` and the request is rejected with a 400 before your controller runs. See `controllers.md` (Reserved request params).
- Any non-underscore-prefixed template in a plugin's `templates/` dir is **directly routable in the CP**, bypassing your controller's `beforeAction()` gates. Underscore-prefix every template that isn't an intentional direct route. See `cp.md` (CP template routing bypasses controllers).

## Reference Files

Read the relevant reference file(s) for your task. Multiple files often apply together.

**Task examples:**
- "Build a custom element type" → read `elements.md` (Architecture section first) + `element-index.md` + `fields.md` + `migrations.md` + `cp.md`
- "Build a hierarchical/tree element type" → read `elements.md` (Architecture: One Element Class with Native Structure)
- "Add a webhook endpoint" → read `controllers.md` + `events.md`
- "Create a queue job that syncs elements" → read `queue-jobs.md` + `elements.md` + `debugging.md`
- "Add a settings page with form fields" → read `controllers.md` + `cp.md` + `architecture.md`
- "Register a custom field type" → read `fields.md` + `events.md`
- "Fix PHPStan errors" → read `quality.md`
- "Add a dashboard widget" → read `cp-components.md` (Dashboard Widgets) + `events.md` (Widget Types section)
- "Expose template variables for plugin users" → read `events.md` (Twig Extensions section)
- "Attach custom methods to entries" → read `events.md` (Behaviors section)
- "Register a custom element or field type" → read `events.md` (Registration Pattern → Registration scope — never gate by request context)
- "Trashed custom elements never get deleted / gc not purging / rows piling up in the elements table" → read `events.md` (Registration Pattern → Registration scope)
- "Build a CP utility page" → read `cp-components.md` (Utility Pages) + `events.md` (Utilities section)
- "Set up Vite for a plugin's CP assets" → read `plugin-vite.md` + load `craft-garnish` skill
- "Add drag-to-reorder or interactive JS to a CP page" → load `craft-garnish` skill
- "Write CP JavaScript for a custom field type" → read `fields.md` + load `craft-garnish` skill
- "Build a headless Craft API" → read `graphql.md` + load `craft-site` skill for `headless.md`
- "Configure preview for a Next.js front-end" → load `craft-site` skill for `headless.md`
- "Set up Pest tests for a plugin" → load `craft-pest` skill → `isolation.md`
- "Write a test for a controller action" → load `craft-pest` skill → `patterns.md`
- "Tests are writing to my dev database / created thousands of stray elements" → load `craft-pest` skill → `isolation.md`
- "Create or delete sites from code (importer, provisioning command, fixture)" → read `architecture.md` (Creating or deleting sites at runtime)
- "Element queries stopped filtering by siteId after I created a site" → read `architecture.md` (Creating or deleting sites at runtime — `refreshSites()` doesn't invalidate the variant queries read)
- "Deleted a site but sections/category groups still reference it" → read `architecture.md` (Creating or deleting sites at runtime — `deleteSite()`'s prune vs memoized service caches)
- "Compare a record's dateUpdated against a cutoff / 'changed since' filter is off by hours" → read `architecture.md` (Those strings are naive UTC)
- "Read a datetime column out of an ActiveRecord into a model" → read `architecture.md` (Record-to-Model Hydration Boundary)
- "My element query with ['like', ...] returns nothing" → read `architecture.md` (Element-query param setters don't take Yii operator tuples)
- "Match elements by title/slug prefix" → read `architecture.md` (Element-query param setters don't take Yii operator tuples)
- "Configure Redis for caching and sessions" → read `config-app.md`
- "Set up environment variables for production" → read `config-bootstrap.md`
- "Find a GeneralConfig setting" → read `config-general.md`
- "Read a config value in plugin code (App::env, parseEnv, GeneralConfig)" → read `config-bootstrap.md` + `config-general.md`
- "Check if allowAdminChanges is enabled in plugin code" → read `config-general.md` + `cp.md` (Read-Only Mode)
- "Resolve env vars in plugin settings ($MY_API_KEY)" → read `config-bootstrap.md` (App::parseEnv)
- "Understand CRAFT_* env var conventions" → read `config-bootstrap.md`
- "Configure mail transport / SMTP" → read `config-app.md`
- "Set up custom URL routes" → read `config-bootstrap.md`
- "Configure search to find short words" → read `config-app.md`
- "Set up GraphQL tokens and schemas" → read `graphql.md` + `config-general.md`
- "Set up caching for a high-traffic site" → read `caching.md`
- "Register custom permissions for my plugin" → read `permissions.md`
- "Check user permissions in templates" → read `permissions.md`
- "Set up plugin editions / feature gating" → read `architecture.md` (Plugin Editions section)
- "Build a fluent render builder / craft.plugin.widget().render()" → read `architecture.md` (Render builders: attribute merging, option allowlists)
- "Site can't override my plugin's front-end CSS / plugin styles win" → read `architecture.md` (Plugin-registered CSS loads after the site's stylesheet)
- "Plugin JS works with shipped templates but not user-written ones" → read `architecture.md` (The JS-to-markup contract is public API)
- "Generate docs/schemas/types from a registry / generator output differs per install or edition" → read `quality.md` (Generated Artifacts Must Not Read Runtime Registries)
- "Cut a release / tag a version / Packagist isn't serving the new version" → load the `craft-plugin-release` skill
- "Deleted a site but my plugin's per-site rows are still there" → read `architecture.md` (Site deletion is a soft delete)
- "Cached false / cache returns false and I can't tell if it's a miss" → read `caching.md` (Data Caching → boolean sentinel idiom)
- "Where should plugin/operational settings (thresholds, notification routing, workflow mappings) live — project config or DB?" → read `architecture.md` (Settings belong in project config)
- "Should thresholds be DB-only to avoid cross-environment churn?" → read `architecture.md` (Settings belong in project config) — this is a misconception to correct
- "Upgrade a plugin from Craft 4 to 5" → read `quality.md` (Rector section)
- "Set up CI for a Craft plugin" → read `quality.md` (CI/CD Integration section)
- "Create sections or fields in a migration" → read `migrations.md` (Content Migrations section)
- "Install fails with 'Too many keys specified; max 64 keys allowed' / duplicate indexes piling up" → read `migrations.md` (Re-runnable index creation and MySQL's 64-key ceiling)
- "Run a module's migrations / --track=module: rejected / library-shipped module schema never applies" → read `migrations.md` (Modules and library-shipped modules have no CLI track)
- "Fix a bad stored project-config value from a plugin upgrade" → read `migrations.md` (Never call ProjectConfig::flush() inside a migration)
- "Unsuspend/restore a user programmatically / user still locked out after unsuspend" → read `elements.md` (getStatus() hides co-existing states)
- "Do I need to override settingsAttributes()?" → read `field-types-custom.md` (What settingsAttributes() actually includes)
- "Set up database read replicas" → read `config-app.md` (Database Replicas section)
- "Register a module in app.php" → read `config-app.md` (Module Registration section)
- "Create a custom validator" → read `architecture.md` (Custom Validators section)
- "Create a custom filesystem type" → read `events.md` (Filesystem Types section)
- "Build a custom condition rule for an element index" → read `cp-ui-patterns.md` (Condition Builders)
- "Build a tri-state on/inherit/off control" → read `cp-ui-patterns.md` (Tri-State Inheritance Controls)
- "Add tabbed settings page to a plugin" → read `cp.md` (Tabbed Settings Pages)
- "Plugin supports a config/<handle>.php override — how should the settings screen behave?" → read `cp.md` (Settings Pages → Config-file overrides: warn on the field, don't disable it)
- "Setting saves but nothing changes / config file silently wins" → read `cp.md` (Settings Pages → Config-file overrides)
- "Why doesn't my URL tab navigate / tabs vs sidebar nav for separate pages?" → read `cp.md` (Tabs switch panes — they never navigate)
- "Build a CP index/list screen: columns, copy chips, row actions" → read `cp-ui-patterns.md` (Index-screen column scheme) + `cp-components.md` (VueAdminTable)
- "VueAdminTable clips headings / where do intro copy and the New button go?" → read `cp-components.md` (VueAdminTable → sole pane content)
- "Utility icon not showing / icon() path" → read `cp-components.md` (Utility Pages)
- "Hide the Visibility/Editability condition builders on a layout element" → read `fields.md` (Suppressing the condition builders)
- "Show an 'overrides global' warning on a field" → read `cp-ui-patterns.md` (Field Warning Parameter)
- "What CSS variables / design tokens does Craft CP use?" → read `cp-ui-patterns.md` (Craft CSS Custom Properties — color/status/spacing/radius/control/focus/font tokens)
- "Lightswitch or checkbox for a boolean setting?" → read `cp.md` (Form Macros Reference → Lightswitch vs checkbox)
- "Render a copytext / API-key / webhook-URL field" → read `cp.md` (Form Macros Reference → copytextField)
- "Which button class for a Save / Delete / Add button?" → read `cp.md` (Form Macros Reference → Button modifier classes)
- "Add an inner sidebar sub-nav to a CP pane" → read `cp.md` (Form Macros Reference → Inner sidebar navigation)
- "Add an inline editable table to a settings page" → read `cp-components.md` (Editable Table Field)
- "Show a modal or confirmation dialog in the CP (there's no Craft.confirm())" → read `cp-components.md` (Modals) + load `craft-garnish` skill for behavior
- "What relation-field view modes / previewMode / maxRelations exist?" → read `element-index.md` (Relation Field Display/Props)
- "Add a Tip / Heading / built-in UI element to a field layout" → read `fields.md` (Field-Layout UI Elements Reference)
- "Add a panel to an element edit screen's sidebar" → read `cp-ui-patterns.md` (Element Edit Screen) + `elements.md` (EVENT_DEFINE_SIDEBAR_HTML)
- "Add a split button to an element's top toolbar" → read `cp-ui-patterns.md` (Element Edit Screen → toolbar split button) + `elements.md` (EVENT_DEFINE_ADDITIONAL_BUTTONS)
- "Why does my sidebar panel render unstyled / look wrong?" → read `cp-ui-patterns.md` (Element Edit Screen → `.meta` vs `.meta read-only`)
- "Override metaFieldsHtml() on a custom element" → read `cp-ui-patterns.md` (Element Edit Screen → metaFieldsHtml override)
- "Set up pre-commit hooks for code quality" → read `quality.md` (Pre-Commit Hooks section)
- "Restrict element access by user group" → read `element-authorization.md` + `permissions.md`
- "Scope CP element index by permission" → read `element-authorization.md` (Layer 3: Query Scoping)
- "Add authorization events to a custom element" → read `element-authorization.md` + `elements.md`
- "Build defense-in-depth for a security plugin" → read `element-authorization.md` (Defense Patterns)
- "Force-logout a user from all devices" → read `sessions-and-auth.md` (Plugin Patterns)
- "Understand how Craft sessions work" → read `sessions-and-auth.md`
- "Implement password reset required" → read `sessions-and-auth.md` (passwordResetRequired Gap)
- "Add a column to the Users element index" → read `element-index.md` (Extending Element Indexes via Events)
- "Add a bulk action to an element index" → read `element-index.md` (Adding a custom bulk action)
- "Add an action to the per-element edit-screen menu" → read `element-index.md` (Per-Element Edit-Screen Action Menu)
- "Render a status pill in a table column" → read `element-index.md` (Status Pills in Table Attributes)
- "Add a custom sidebar source to the element index" → read `element-index.md` (Adding a sidebar source)
- "Build a custom field type" → read `field-types-custom.md` + `fields.md`
- "Build a relation field type" → read `field-types-custom.md` (Relation Fields)
- "Add a condition rule to the entry index" → read `conditions.md` + `element-index.md`
- "Build a custom condition rule" → read `conditions.md`
- "Send email from a plugin" → read `email.md`
- "Register a custom system message" → read `email.md` (Registering Custom System Messages)
- "Configure SMTP transport" → read `config-app.md` + `email.md`
- "Deploy Craft CMS to production" → read `deployment.md`
- "Set up CI/CD for a Craft project" → read `deployment.md` (CI/CD Patterns)
- "Zero-downtime deploy" → read `deployment.md` (Zero-Downtime)
- "Roll back a failed deploy" → read `deployment.md` (Rollback Strategies)
- "Work with drafts and revisions" → read `drafts-revisions.md`
- "Create a draft programmatically" → read `drafts-revisions.md` (Creating Drafts)
- "Skip side effects for drafts in afterSave" → read `drafts-revisions.md` (Plugin Considerations)
- "Add generated fields to a custom element" → read `elements.md` (Generated Fields)
- "Customize how my element appears as a chip or card" → read `element-index.md` (Element Display Modes)
- "Add a screen to the User edit page" → read `elements.md` (Extending User Edit Screens)
- "Make plugin settings read-only when allowAdminChanges is off" → read `cp.md` (Read-Only Mode)
- "Add tabs to a plugin's settings page" → read `cp.md` (Settings Pages → With tabs or custom actions). `settingsHtml()` is single-pane only — tabs require a custom controller and a template extending `_layouts/cp` directly.
- "Render plugin settings inside its own CP section (not the global settings/plugins screen)" → read `cp.md` (Settings Pages → Keep settings inside the plugin's own CP section)
- "Make a plugin Cloud-compatible" → load `craft-cloud` skill → `plugin-development.md` (ephemeral filesystem, asset-bundle constraints, queue cap, CSRF function, cookie-free design)
- "Deploy a Craft project to Cloud" → load `craft-cloud` skill → `config-file.md` + `deploy-pipeline.md` + `extension.md`
- "Migrate a self-hosted Craft site to Cloud" → load `craft-cloud` skill → `migration.md`
- "Why does my plugin's file write silently fail on Cloud?" → load `craft-cloud` skill → `plugin-development.md` (Ephemeral filesystem) + `extension.md` (App::isEphemeral)
- "Build an SSO/OIDC login or SCIM provisioning feature" → read `identity-protocols.md` + `sessions-and-auth.md`
- "Handle single logout / logout_token / provider-initiated deprovisioning" → read `identity-protocols.md`

Load only the reference files your task needs — each file costs input tokens on every turn.

| Task | Read | ~Tokens |
|------|------|--------:|
| Element core: lifecycle, queries, status, authorization, drafts, revisions, propagation, field layouts, user edit screens, events | `references/elements.md` | 8.4K |
| Element index: sources, table/card attributes, status pills, sort, conditions, actions (bulk + per-element action menu), exporters, sidebar, metadata, relation-field display/props (viewMode, previewMode, maxRelations), extending via events | `references/element-index.md` | 6.1K |
| Services, models, records, project config (incl. runtime site creation/deletion caches), MemoizableArray, events, API clients, custom validators | `references/architecture.md` | 7.4K |
| Controllers: CP CRUD, webhooks, API endpoints, action routing, authorization | `references/controllers.md` | 3.9K |
| CP templates, form macros (incl. lightswitch vs checkbox, copytext, money, button classes), settings pages, navigation (incl. inner sidebar nav), permissions, read-only mode | `references/cp.md` | 7.2K |
| CP components: dashboard widgets, utility pages, slideout editors, ajax, editable tables, spinner, modals (markup + shade), alerts | `references/cp-components.md` | 1.8K |
| CP UI patterns: tri-state controls, status indicators, semantic CSS tokens (color/status/spacing/radius/control/focus/fonts), condition builders, asset bundles, element edit-screen sidebar panels + toolbar split buttons | `references/cp-ui-patterns.md` | 3.4K |
| Database migrations, Install.php, foreign keys, indexes, idempotency, deployment | `references/migrations.md` | 3.9K |
| Queue jobs, BaseJob, TTR, retry, progress, batch jobs, site context | `references/queue-jobs.md` | 4.2K |
| Console commands, arguments, options, progress bars, output helpers, resave actions | `references/console-commands.md` | 6.0K |
| Debugging, performance, query strategy, profiling, Xdebug, caching, logging | `references/debugging.md` | 4.6K |
| PHPStan, ECS, code review checklist | `references/quality.md` | 3.5K |
| Testing: pointer to the `craft-pest` skill (Pest/craft-pest-core lives there) + Codeception basics | `references/testing.md` | 0.6K |
| Field types, native fields, BaseNativeField, field layout elements (built-in Tip/Heading/LineBreak/HorizontalRule reference), FieldLayoutBehavior | `references/fields.md` | 3.6K |
| Events: registration, lifecycle, naming conventions, custom events, behaviors, Twig extensions, utilities, widgets, filesystems | `references/events.md` | 4.4K |
| GraphQL types, queries, mutations, directives, schema components, resolvers | `references/graphql.md` | 4.6K |
| Plugin Vite: VitePluginService, CP asset bundles, HMR, TypeScript, Vue in CP | `references/plugin-vite.md` | 2.7K |
| Headless & hybrid: headlessMode, GraphQL API, CORS, preview tokens, front-end frameworks | craft-site skill `references/headless.md` | 3.4K |
| GeneralConfig (system, routing, security, users, sessions, search, assets, images) | `references/config-general.md` | 8.4K |
| GeneralConfig (content, templates, performance, GC, localization, headless, GraphQL, accessibility) | `references/config-general-extended.md` | 7.2K |
| App config: cache, session, queue, mutex, mailer/SMTP, search, logging, CORS, DB replicas | `references/config-app.md` | 5.5K |
| Config bootstrap: env vars, aliases, priority order, fluent API, custom.php, db.php, routes.php | `references/config-bootstrap.md` | 3.6K |
| Caching: template cache tag, data cache, static caching (Blitz), CDN, layered strategy, invalidation | `references/caching.md` | 5.2K |
| Permissions: built-in handles, user groups, custom registration, Twig/PHP checking, authorization events | `references/permissions.md` | 4.7K |
| Element authorization: four-layer defense model, authorization events, can*() methods, query scoping | `references/element-authorization.md` | 4.6K |
| Sessions & auth internals: dual-layer session model, auth tokens, session invalidation, elevated sessions | `references/sessions-and-auth.md` | 3.0K |
| Identity protocols for SSO/provisioning plugins: back-channel vs front-channel logout, signing-alg allowlists, issuer vs tenancy (hd claim), SCIM active:false + PATCH ordering, vendor-vs-RFC deviations | `references/identity-protocols.md` | 1.3K |
| Custom field types: build pattern, value lifecycle, settings, input HTML, validation, search, GraphQL | `references/field-types-custom.md` | 3.5K |
| Conditions framework: BaseCondition, ElementCondition, custom condition rules, registering rules | `references/conditions.md` | 2.3K |
| Email system: system messages, custom messages, programmatic sending, templates, events, testing | `references/email.md` | 2.4K |
| Deployment: standard pipeline, project config deploy, zero-downtime, CI/CD, rollback | `references/deployment.md` | 2.5K |
| Drafts & revisions: draft types, provisional drafts, autosave, applying, merge, revisions | `references/drafts-revisions.md` | 2.5K |

## Plugin vs Module Differences

Plugins and modules share the same architecture patterns. The differences are in bootstrapping and registration:

| Feature | Plugin | Module |
|---------|--------|--------|
| CP template root | Automatic (by handle) | Manual via `EVENT_REGISTER_CP_TEMPLATE_ROOTS` |
| Site template root | Manual via event | Same — manual for both |
| Translation category | Automatic (by handle) | Manual `PhpMessageSource` in `init()` |
| Settings model | Built-in `createSettingsModel()` | Env vars, config files, or private plugin (`_` prefix) |
| Install migration | `migrations/Install.php` | Content migrations only |
| Console commands | Automatic `controllerNamespace` | Must set before `parent::init()`, must be bootstrapped |
| CP nav section | `$hasCpSection = true` | `EVENT_REGISTER_CP_NAV_ITEMS` |
| Project config | Settings auto-tracked | Manual `ProjectConfig::set()` only |
| Namespace alias | Automatic via Composer | Must call `Craft::setAlias()` |

### Module Template Root Registration

```php
use craft\events\RegisterTemplateRootsEvent;
use craft\web\View;

Event::on(View::class, View::EVENT_REGISTER_CP_TEMPLATE_ROOTS,
    function(RegisterTemplateRootsEvent $event) {
        $event->roots['my-module'] = __DIR__ . '/templates';
    }
);
```

### Module Translation Registration

```php
Craft::$app->i18n->translations['my-module'] = [
    'class' => \craft\i18n\PhpMessageSource::class,
    'sourceLanguage' => 'en',
    'basePath' => __DIR__ . '/translations',
    'allowOverrides' => true,
];
```

### Module Console Command Registration

```php
public function init()
{
    Craft::setAlias('@mymodule', __DIR__);

    if (Craft::$app->getRequest()->getIsConsoleRequest()) {
        $this->controllerNamespace = 'modules\\mymodule\\console\\controllers';
    } else {
        $this->controllerNamespace = 'modules\\mymodule\\controllers';
    }

    parent::init(); // MUST come after setting controllerNamespace
}
```

The module **must** be bootstrapped in `config/app.php` for console commands to be discoverable.