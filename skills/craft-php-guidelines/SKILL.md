---
name: craft-php-guidelines
description: "Craft CMS 5 PHP coding standards and conventions. ALWAYS load when writing, editing, reviewing, or discussing any PHP in a Craft plugin or module — even small edits. Also when running ECS, PHPStan, or scaffolding with ddev craft make. Covers: PHPDoc blocks (@author, @since, @throws chains), section headers (=========), class organization, naming conventions (services, queue jobs, records, events, enums), defineRules() and validation, beforePrepare() and addSelect(), MemoizableArray, DateTimeHelper vs Carbon, strict_types/declare(strict_types=1), short nullable notation (?string), typed properties, void returns, control flow (early returns, match over switch), CP Twig template conventions, form macros, translations (Craft::t), ECS/PHPStan config, scaffolding commands, and the verification checklist."
when_to_use: "Triggers on: writing service classes, models, controllers, elements, element queries, records, queue jobs, migrations, or any PHP class in a Craft context; PHP code review, refactoring, or style questions; requireAdmin vs requirePermission, manage-settings, settings permission, kebab-case permission handles never camelCase, allowAdminChanges, read-only settings, getCpNavItem dead nav item, permission handle constant on owning controller, App::env() never getenv(), App::parseEnv() for $VAR settings, no-em-dash user-facing copy. NOT for front-end Twig (craft-twig-guidelines), template architecture (craft-site), or CP JavaScript/Garnish (craft-garnish). If you are touching PHP in a Craft context, you need this skill."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft CMS 5 PHP Guidelines

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Complete PHP coding standards and conventions for Craft CMS 5 plugin and module development. These extend Craft's official coding guidelines with project-specific conventions.

**Core principles:** PHPDocs on everything — classes, methods, and properties — regardless of type hints. No `declare(strict_types=1)` in plugin source files (matching Craft core convention).

## Companion Skills — Always Load Together

- **`craftcms`** — Architecture patterns, element lifecycle, controllers, events, migrations. Required for any Craft plugin or module development.
- **`ddev`** — All commands run through DDEV. Required for running ECS, PHPStan, scaffolding, and tests.

## Documentation

- Official coding guidelines: https://craftcms.com/docs/5.x/extend/coding-guidelines.html
- Class reference: https://docs.craftcms.com/api/v5/
- Generator reference: https://craftcms.com/docs/5.x/extend/generator.html

When unsure about a convention, `WebFetch` the coding guidelines page for the authoritative answer.

## Reference Files

Read the relevant reference file(s) for your task:

| Task | Read | ~Tokens |
|------|------|---------|
| Writing PHPDocs, `@author`, `@since`, `@throws`, `@var`, `@param`, type references; console controller docblocks as `craft help` text | `references/phpdoc-standards.md` | ~1,150 |
| Class structure, section headers, ordering, shared constants, enums, control flow, comments, whitespace | `references/class-organization.md` | ~2,050 |
| Naming classes, methods, properties, files, services, events, migrations; quick-reference table; kebab-case permission handles and their constants | `references/naming-conventions.md` | ~1,500 |
| CP Twig templates, form macros, translations, copy style (no em-dashes), file headers, validation | `references/templates-and-patterns.md` | ~1,350 |
| `DateTimeHelper` vs `Carbon`, parsing DB datetimes, `App::env()`/`App::parseEnv()`, `UrlHelper::absoluteUrl()` [5.12.2+], `doesEnvVarExist()` [5.11+], DB conventions, `Db::isSafeOrderBy()` [5.12+], component registration scope | `references/dates-env-database.md` | ~1,250 |
| ECS, PHPStan (`Craft::$app` narrowing, magic property access), scaffolding commands, composer hygiene for plugin repos, commit messages | `references/tooling.md` | ~2,100 |
| Authorization parity across CP / console / GraphQL / queue surfaces, self-referential guards, one shared gate | `references/authorization-parity.md` | ~2,900 |

## Critical Rules

1. PHPDocs on everything: classes, methods, properties. No exceptions.
2. `@throws` chains: document every exception including uncaught from called methods.
3. `@author` and `@since` at the bottom of class/method docblocks, after a blank line. `@author` goes on classes **and methods**, never on properties. (Craft *core* puts `@author` at the class level only; method-level `@author` is this project's house convention. Don't "fix" it.)
4. Section headers with `// =========================================================================` on every class. (Craft *core* itself uses dash separators — `// ----` — with functional/domain labels like `// Statuses` or `// Events`. The `=====` separators and visibility labels below are a deliberate house convention for consistency across this project's plugins, not core style.)
5. `declare(strict_types=1)` is NOT used in plugin source files — Craft's internal type coercion depends on PHP's default weak typing mode. Only standalone config files like `ecs.php` use it.
6. Private methods/properties prefixed with underscore, with meaningful names: `_registerCpUrlRules()`, `$_items`, `$_sections` (never `$_instances`).
7. `addSelect()` convention in `beforePrepare()` — additive across extensions, prevents column conflicts.
8. `DateTimeHelper` in elements/queries, `Carbon` in services — never mix them in the same class.
9. Always scaffold with `ddev craft make <type> --with-docblocks`, then customize.
10. `ddev composer check-cs` and `ddev composer phpstan` must pass before every commit.

## Section Header Order

```
// Traits
// Const Properties
// Static Properties
// Public Properties
// Protected Properties
// Private Properties
// Public Methods
// Protected Methods
// Private Methods
```

Only include sections that have content. Blank line after the separator, before the first item. Full example: `references/class-organization.md`.

## PHP Standards

- Minimum PHP 8.2 (Craft CMS 5 requirement).
- PSR-12 baseline with Craft modifications (trailing commas, constant visibility).
- `craftcms/ecs` with `SetList::CRAFT_CMS_4` preset (covers both Craft 4 and 5).
- Short nullable notation: `?string` not `string|null`.
- Always specify `void` return types.
- Typed properties everywhere. No untyped public properties.
- Strict comparison always: `$foo === null`, `in_array($x, $y, true)`.
- Casts over functions: `(int)$foo` not `intval($foo)`.
- Control flow: happy path last with early returns, no `else`, `match` over `switch` for value-mapping, curly brackets always, compound conditions split into nested `if`s, named arguments at 3+ parameters. See `references/class-organization.md`.

## Common Pitfalls

- Records use the **same class name** as models (namespace distinguishes). Alias when importing both: `use ...\records\MyEntity as MyEntityRecord;`.
- Queue jobs have **no "Job" suffix** — `ResaveElements`, not `ResaveElementsJob`. Element actions likewise (`Delete`, `SetStatus`).
- Forget `parent::defineRules()` and you lose all inherited validation.
- Using `[$this, '_validateFoo']` callable arrays or inline closures in `defineRules()` — Craft core uses string method names: `[['attr'], 'validateAttr']`. The validator method is public, no underscore — Yii invokes it by name.
- Parsing a raw DB datetime with `strtotime()` or `new DateTime()`: the column is naive UTC and the process timezone is `system.timeZone`. Use `DateTimeHelper::toDateTime($value)` or Carbon with `'UTC'`. See `references/dates-env-database.md`.
- Magic property access (`$plugin->settings`, `$app->view`) fails PHPStan; use explicit getters (`getSettings()`, `getView()`). See `references/tooling.md`.
- Calling Craft-specific methods directly on `Craft::$app` — narrow with a typed local: `/** @var \craft\web\Application $app */ $app = Craft::$app;`. Don't use `@phpstan-ignore-line`.
- Contract constants (permission handles, wire formats) duplicated as `private const` drift silently: one `public const` on the owner, e.g. `SettingsController::PERMISSION_MANAGE_SETTINGS`. See `references/naming-conventions.md`.
- **Permission handles are kebab-case (`handle:manage-settings`); never camelCase**, though Craft core's own are camelCase. The PHP constant stays `SCREAMING_SNAKE_CASE`. See `references/naming-conventions.md`.
- **`App::env('VAR')`, never `getenv()`**, in plugin code and in every config example (with `use craft\helpers\App;`). `App::parseEnv()` for settings that may hold a `$VAR` or alias. See `references/dates-env-database.md`.
- The same authorization check written separately in a CP controller, a console command, and a GraphQL resolver drifts: one shared gate called by every surface, a test per surface. Console is not exempt; GraphQL schema scope is not the plugin's permission matrix. Craft has no self-approval guard either. See `references/authorization-parity.md`.
- `../*` path repositories in a plugin's `composer.json` resolve only on the author's disk. See `references/tooling.md` (Composer Hygiene).
- `Db::parseParam()` for a literal comparison turns a leading/trailing `*` into a `LIKE` wildcard. Use `andWhere(['col' => $value])`.
- Registering `EVENT_REGISTER_ELEMENT_TYPES` / `EVENT_REGISTER_FIELD_TYPES` inside a `getIsCpRequest()` branch hides the type from console/queue requests (and `Gc` stops purging it). Register unconditionally. See `references/dates-env-database.md`.
- Console controller docblocks print verbatim as `craft help`: the summary is physical docblock line 2, so no `=========` rule there, no `{@see}`/`{@link}`/`{@inheritdoc}`, no scaffolded `* Class FooController`. See `references/phpdoc-standards.md`.
- **Copy style**: no em-dashes (—) or en-dashes (–) in user-facing copy (`Craft::t()` strings, labels, CP notices, console output, README, docs). Code comments and PHPDoc are exempt. See `references/templates-and-patterns.md`.

## Verification Checklist

Before every commit:

1. `ddev composer check-cs` passes
2. `ddev composer phpstan` passes
3. Tests green
4. PHPDocs complete on all new/modified code
5. `@throws` chains verified
6. Section headers present and correct
7. Imports flat alphabetical (ECS-enforced, not "PHP globals first")
8. No em-dashes (—) or en-dashes (–) in user-facing copy (`Craft::t()` strings, labels, CP notices, README, docs)
