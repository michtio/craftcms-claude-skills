# {{moduleName}} — Craft CMS 5 Module

@.claude/rules/coding-style.md
@.claude/rules/architecture.md
@.claude/rules/git-workflow.md
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
ddev craft up                        # Migrations + project config
ddev composer install                # Install deps (auto-runs craft up)
```

## Module Structure

```
modules/{{moduleHandle}}/
├── Module.php                   # Entry point (bootstrapped in config/app.php)
├── controllers/                 # Web controllers
├── console/controllers/         # CLI commands
├── services/                    # Business logic services
├── models/                      # Data models
├── templates/                   # Module templates (manual root registration)
└── translations/                # Translation files (manual registration)
```

## Module Bootstrapping

Modules require manual registration unlike plugins. Key differences:
- Template root: register via `EVENT_REGISTER_CP_TEMPLATE_ROOTS`
- Translations: register `PhpMessageSource` in `init()`
- Console commands: set `controllerNamespace` before `parent::init()`
- Must be bootstrapped in `config/app.php`

## Documentation

- Module development: https://craftcms.com/docs/5.x/extend/module-guide.html
- Plugin vs module: https://craftcms.com/docs/5.x/extend/
