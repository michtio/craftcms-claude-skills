# {{pluginName}} — Craft CMS 5 Plugin

@.claude/rules/coding-style.md
@.claude/rules/architecture.md
@.claude/rules/git-workflow.md
@.claude/rules/scaffolding.md
@.claude/rules/security.md

## General

Be critical. We're equals — push back when something doesn't make sense.

Do not excessively use emojis. Do not include AI attribution in commits, PRs, issues, or comments.

Do not include "Test plan" sections in PR descriptions.

## Tools

Use `ddev` shorthand commands: `ddev composer`, `ddev craft`, `ddev npm`. Never run `php`, `composer`, or `npm` on the host — everything goes through DDEV.

Use `gh` for all GitHub operations.

## Environment

```bash
ddev composer check-cs               # ECS code style
ddev composer fix-cs                 # ECS auto-fix
ddev composer phpstan                # PHPStan analysis
ddev craft pest/test                 # Pest tests
ddev craft up                        # Migrations + project config
ddev composer install                # Install deps (auto-runs craft up)
```

## Plugin Structure

```
src/
├── {{pluginClass}}.php          # Entry point
├── controllers/                 # CP web controllers
├── db/                          # Table constants
├── elements/                    # Custom element types
│   ├── actions/                 # Element index actions
│   ├── conditions/              # Element condition rules
│   ├── db/                      # Element queries
│   └── exporters/               # Element exporters
├── enums/                       # PHP backed enums
├── events/                      # Event classes
├── jobs/                        # Queue jobs
├── migrations/                  # Database migrations + Install.php
├── models/                      # Settings, data models
├── records/                     # ActiveRecord classes
├── services/                    # Business logic services
├── templates/                   # CP Twig templates
└── translations/                # Translation files
```

## Documentation

- Plugin development: https://craftcms.com/docs/5.x/extend/
- Class reference: https://docs.craftcms.com/api/v5/
- Generator: https://craftcms.com/docs/5.x/extend/generator.html
- Craft source: `vendor/craftcms/cms/src/`
