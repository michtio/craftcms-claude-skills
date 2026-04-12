# Craft CMS 5 Plugin Development

@.claude/rules/coding-style.md
@.claude/rules/architecture.md
@.claude/rules/git-workflow.md
@.claude/rules/scaffolding.md
@.claude/rules/security.md

## Environment

```bash
ddev composer check-cs               # ECS code style
ddev composer fix-cs                 # ECS auto-fix
ddev composer phpstan                # PHPStan analysis
ddev craft pest/test                 # Pest tests
ddev craft up                        # Migrations + project config
ddev composer install                # Install deps (auto-runs craft up)
```

## Craft CMS Plugin Structure

```
src/
├── Plugin.php               # Entry point
├── assetbundles/            # CP asset bundles
├── base/                    # Abstract base classes, shared traits
├── behaviors/               # Yii2 behaviors
├── console/controllers/     # CLI commands
├── controllers/             # CP web controllers
├── db/                      # Table constants
├── elements/                # Custom element types
│   ├── actions/             # Element index actions
│   ├── conditions/          # Element condition rules
│   ├── db/                  # Element queries
│   └── exporters/           # Element exporters
├── enums/                   # PHP backed enums
├── errors/                  # Custom exceptions
├── events/                  # Event classes
├── fieldlayoutelements/     # Custom field layout elements
├── fields/                  # Custom field types
├── gql/                     # GraphQL types, queries, mutations
├── helpers/                 # Static utility helpers
├── jobs/                    # Queue jobs
├── migrations/              # Database migrations + Install.php
├── models/                  # Settings, data models
├── records/                 # ActiveRecord classes
├── services/                # Business logic services
├── templates/               # CP Twig templates
├── translations/            # Translation files
├── utilities/               # CP utilities
├── validators/              # Custom validators
├── variables/               # Twig variable classes
├── web/                     # Twig extensions, asset bundles
└── widgets/                 # Dashboard widgets
```

## Architecture

- **Work with Craft, not against it.** Follow core patterns: project config, element lifecycle, soft delete, GC, events.
- **Abstract base classes** for shared controller structure. **Traits** for cross-cutting concerns.
- **Element operations in services**, not controllers or helpers.
- **DateTimeHelper** in elements/queries, **Carbon** in services.
- **Project config** for settings that sync. Dedicated paths for managed entities.
- **`Craft::$app->onInit()`** for deferred initialization needing a fully-booted app.

## Documentation

- Plugin development guide: https://craftcms.com/docs/5.x/extend/
- Class/API reference: https://docs.craftcms.com/api/v5/
- Scaffolding (Generator): https://craftcms.com/docs/5.x/extend/generator.html
- Craft source code: `vendor/craftcms/cms/src/`

Use `WebFetch` on these URLs when skills don't cover a specific pattern.

## Project-Specific Skills

Check `.claude/skills/` in this repo for project-specific patterns.
