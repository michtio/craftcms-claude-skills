# Quality -- ECS, PHPStan, Rector, CI/CD

Static analysis, code style enforcement, and continuous integration patterns for Craft CMS 5 plugins and modules.

## Documentation

- Coding guidelines: https://craftcms.com/docs/5.x/extend/coding-guidelines.html
- Generator: https://craftcms.com/docs/5.x/extend/generator.html
- craftcms/ecs: https://github.com/craftcms/ecs
- craftcms/phpstan: https://github.com/craftcms/phpstan
- craftcms/rector: https://github.com/craftcms/rector
- Craft Pest: https://craft-pest.com

## Contents

- [Common Pitfalls](#common-pitfalls)
- [ECS Deep Dive](#ecs-deep-dive)
- [PHPStan Levels Reference](#phpstan-levels-reference)
- [craftcms/phpstan Package](#craftcmsphpstan-package)
- [PHPStan Configuration](#phpstan-configuration)
- [Common PHPStan Errors](#common-phpstan-errors)
- [Baseline Management](#baseline-management)
- [Rector](#rector)
- [CI/CD Integration](#cicd-integration)
- [Pre-Commit Hooks](#pre-commit-hooks)
- [Testing](#testing)
- [Code Review Checklist](#code-review-checklist)

## Common Pitfalls

- Running `fix-cs` project-wide without explicit approval -- can touch hundreds of files across vendor code, unrelated modules, and generated files. Always scope to changed files or specific directories.
- Adding new code errors to the PHPStan baseline instead of fixing them -- the baseline is for legacy code only. New code ships clean.
- Skipping ECS on generated/scaffolded code -- Craft's generators (`ddev craft make`) don't always match your project's style rules. Run `check-cs` on every new file.
- Not matching PHPStan level to team capability -- jumping to level 8 on a team unfamiliar with static analysis creates frustration. Start at 5 (recommended for Craft plugins), raise incrementally.
- Using `@phpstan-ignore-next-line` without a comment explaining why -- makes it impossible to revisit later.
- Not running `ddev composer check-cs` AND `ddev composer phpstan` before every commit.
- Pest test names that don't describe the behavior -- `it('works')` tells nothing.

## ECS Deep Dive

### What craftcms/ecs provides

The `craftcms/ecs` package ships a pre-configured ECS rule set aligned with Craft's coding guidelines: section header spacing, PHPDoc formatting, import ordering, brace style.

Install: `ddev composer require --dev craftcms/ecs`

### Configuration file structure

ECS is configured via `ecs.php` at the project root. The file defines rule sets, skip patterns, and paths to check.

```php
<?php

declare(strict_types=1);

use craft\ecs\SetList;
use Symplify\EasyCodingStandard\Config\ECSConfig;

return ECSConfig::configure()
    ->withPaths([__DIR__ . '/src', __DIR__ . '/tests'])
    ->withSets([SetList::CRAFT_CMS_4])
    ->withSkip([
        // PhpCsFixer\Fixer\Operator\NotOperatorWithSuccessorSpaceFixer::class,
    ]);
```

### Running ECS

Check for violations (read-only):

```bash
ddev composer check-cs
```

Auto-fix violations (writes files):

```bash
ddev composer fix-cs
```

Scope fix to specific files (safe for individual changes):

```bash
ddev exec vendor/bin/ecs check src/services/Items.php --fix
ddev exec vendor/bin/ecs check src/controllers/ --fix
```

Never run `fix-cs` project-wide without explicit approval. Scope to changed files only.

### Common ECS violations in Craft context

| Violation | Fix |
|-----------|-----|
| Missing blank line before return | Add blank line before `return` statement |
| Imports not alphabetized | Reorder `use` statements alphabetically |
| PHPDoc missing `@param` type | Add type annotation to all parameters |
| Trailing comma missing in multiline | Add trailing comma after last array/parameter entry |
| No space after cast | Add space: `(int) $value` not `(int)$value` |
| Blank line after opening brace | Remove blank line after `{` in class/method |
| Multiple blank lines | Collapse to single blank line |
| Missing `void` return type | Add `: void` to methods that return nothing |
| Yoda comparison style | Craft uses Yoda: `null === $value` not `$value === null` |

### Customizing rules

Skip rules or configure them per-project in `ecs.php`:

```php
->withSkip([
    PhpCsFixer\Fixer\Phpdoc\PhpdocAlignFixer::class,
    __DIR__ . '/src/migrations/Install.php',
])
->withConfiguredRule(
    PhpCsFixer\Fixer\Phpdoc\PhpdocOrderFixer::class,
    ['order' => ['param', 'return', 'throws']],
)
```

## PHPStan Levels Reference

| Level | What it checks |
|-------|---------------|
| 0 | Basic checks: unknown classes, functions, methods called on objects |
| 1 | Possibly undefined variables, unknown magic methods, unknown properties on `$this` |
| 2 | Unknown methods on union types (`$foo` could be `A\|B`, method must exist on both) |
| 3 | Return types checked against declared return type |
| 4 | Basic dead code detection (always-true/false conditions) |
| 5 | Argument types checked on method/function calls **(recommended for Craft plugins)** |
| 6 | Missing typehints reported (properties, parameters, return types) |
| 7 | Union types fully enforced, partial matches flagged |
| 8 | Nullable types strictly enforced, method calls on possibly-null values flagged |
| 9 | Mixed type strictness -- operations on `mixed` flagged unless narrowed |

**Recommendation:** Start at level 5 for new plugins. It catches real bugs (wrong argument types) without drowning you in missing-typehint noise. Raise to 6-8 as the codebase matures.

## craftcms/phpstan Package

Without `craftcms/phpstan`, PHPStan cannot understand Craft's service locator, element queries, or component accessors.

What it provides:
- **Type stubs** for `Craft::$app->getXxx()` service accessors
- **Element query return types** -- `Entry::find()->one()` returns `?Entry`, not `mixed`
- **Config component awareness** -- `Craft::$app->getConfig()->getGeneral()` returns `GeneralConfig`
- **Plugin instance types** -- `MyPlugin::getInstance()` return type resolution

Install: `ddev composer require --dev craftcms/phpstan:dev-main`

Include in `phpstan.neon` (before your baseline):

```neon
includes:
    - vendor/craftcms/phpstan/phpstan.neon
```

## PHPStan Configuration

### phpstan.neon example

```neon
includes:
    - vendor/craftcms/phpstan/phpstan.neon
    - phpstan-baseline.neon

parameters:
    level: 5                          # See levels table above
    paths: [src]
    treatPhpDocTypesAsCertain: false   # PHPDoc types are hints, not guarantees
    tmpDir: %currentWorkingDirectory%/tmp/phpstan
    ignoreErrors:
        - '#PHPDoc tag @mixin contains invalid type#'
        - '#^Dead catch#'
```

Run: `ddev composer phpstan`

### Common fix patterns

**ActiveQuery returns `array`:**
```php
/** @var MyRecord[] $records */
$records = MyRecord::find()->where(['categoryId' => $id])->all();
```

**Element query returns `ElementQueryInterface`:**
```php
/** @var MyQuery $query */
$query = MyElement::find();
```

**Yii2 component access:**
```php
/** @var MyPlugin $plugin */
$plugin = MyPlugin::getInstance();
```

**`$sourceElements` type narrowing in eager loading:**
```php
/** @var MyElement[] $sourceElements */
foreach ($sourceElements as $element) {
    // PHPStan now knows custom properties
}
```

### `@phpstan-ignore-next-line`

Use sparingly, always with explanation:

```php
/** @phpstan-ignore-next-line Craft's event system uses mixed types */
$event->types[] = MyElement::class;
```

## Common PHPStan Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Method X not found on Element | Missing `@method` annotation on element class | Add `@method` to class PHPDoc |
| Cannot call method on null | `Craft::$app->getXxx()` nullable return | Add null check or `@var` annotation |
| Parameter expects string, int given | `$request->getBodyParam()` returns `mixed` | Cast: `(int) $request->getBodyParam('id')` or validate |
| Property has no type declaration | Missing typed property | Add typed property: `public string $handle = '';` |
| Dead catch -- Exception never thrown | Overly broad catch block | Narrow to specific exception class |
| Access to undefined property | Custom element properties not declared | Add typed properties to element class |
| Access to undefined property $queue | Queue runner injects `$this->queue` dynamically | Add `@property \yii\queue\Queue $queue` to class docblock |
| Access to an undefined property via __get() | Using `$plugin->settings` or `$app->view` magic access | Use explicit getters: `$plugin->getSettings()`, `$app->getView()`. PHPStan can't resolve `__get()` calls. |
| Return type has no value type | Generic types like `array` without `@return` | Use `@return array<string, mixed>` in PHPDoc |
| Method should return X but returns Y | Mismatched declared vs actual return type | Fix return type or method logic |
| Comparison always evaluates to true | Redundant null check on non-nullable | Remove the check, or fix the type annotation |
| Unsafe usage of new static() | Called in non-final class | Mark class `final` or use `@template` annotation |

## Baseline Management

### Purpose

The baseline captures existing PHPStan errors so they don't block CI. New code must be clean -- baseline is for legacy code only.

### Generate baseline

```bash
ddev exec vendor/bin/phpstan analyse --generate-baseline
```

This creates `phpstan-baseline.neon`. Include it in `phpstan.neon` after the craftcms/phpstan include.

### Review and enforcement

Diff the baseline file during code review. Watch for:
- **Growing error count** -- someone added errors instead of fixing them
- **New file paths** -- new code should never appear in the baseline
- **Bulk-fixable patterns** -- missing return types, etc.

CI rule: if `grep -c 'message:' phpstan-baseline.neon` grows, the PR should not merge.

### Chipping away

Periodically fix errors, verify with `ddev composer phpstan`, then regenerate:

```bash
ddev exec vendor/bin/phpstan analyse --generate-baseline
```

## Rector

Rector automates PHP refactoring -- upgrading syntax, renaming methods, adjusting type hints. The `craftcms/rector` package provides Craft CMS-specific upgrade rules (e.g., Craft 4 to 5 migration).

Install: `ddev composer require --dev craftcms/rector:dev-main`

Always dry-run first, then apply after review:

```bash
ddev exec vendor/bin/rector process src --dry-run
ddev exec vendor/bin/rector process src
```

### Configuration (rector.php)

```php
<?php

declare(strict_types=1);

use craft\rector\SetList;
use Rector\Config\RectorConfig;

return RectorConfig::configure()
    ->withPaths([__DIR__ . '/src'])
    ->withSets([SetList::CRAFT_CMS_50]);
```

Craft-specific rules rename deprecated methods, update event class references, adjust element query signatures, and convert old permission strings. Always run ECS and PHPStan after Rector -- automated refactoring can introduce style violations.

## CI/CD Integration

### GitHub Actions workflow

Run checks in order: ECS first (fastest), PHPStan second, tests last (slowest).

```yaml
name: Quality
on:
  pull_request:
    branches: [main, develop]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: '8.2'
          extensions: mbstring, intl, pdo_mysql
          coverage: none
      - uses: actions/cache@v4
        with:
          path: vendor
          key: composer-${{ hashFiles('composer.lock') }}
      - uses: actions/cache@v4
        with:
          path: tmp/phpstan
          key: phpstan-${{ github.sha }}
          restore-keys: phpstan-
      - run: composer install --no-interaction --prefer-dist
      - run: vendor/bin/ecs check
      - run: vendor/bin/phpstan analyse
      - run: vendor/bin/pest
```

### Order rationale

1. **ECS** (seconds) -- fails fast on formatting, cheapest to fix
2. **PHPStan** (10-30s) -- catches type errors before expensive test runs
3. **Pest** (varies) -- integration tests last, only if static checks pass

### Caching

- **Composer vendor** -- keyed by `composer.lock` hash
- **PHPStan result cache** -- keyed by commit SHA with branch prefix fallback

### Parallel jobs for larger projects

Split ECS and PHPStan into separate jobs, gate tests with `needs: [ecs, phpstan]`.

## Pre-Commit Hooks

Run ECS on staged PHP files before every commit. Create `.git/hooks/pre-commit` (and `chmod +x` it):

```bash
#!/bin/sh

STAGED_PHP=$(git diff --cached --name-only --diff-filter=ACM | grep '\.php$')
[ -z "$STAGED_PHP" ] && exit 0

echo "Running ECS on staged PHP files..."
# Use 'ddev exec vendor/bin/ecs' in DDEV environments,
# or 'vendor/bin/ecs' for CI / non-DDEV setups
echo "$STAGED_PHP" | xargs ddev exec vendor/bin/ecs check

if [ $? -ne 0 ]; then
    echo "ECS failed. Run 'ddev composer fix-cs' to auto-fix, then re-stage."
    exit 1
fi
```

For projects with a Node toolchain, use husky + lint-staged instead:

```json
{
  "lint-staged": {
    "*.php": "ddev exec vendor/bin/ecs check"
  }
}
```

## Testing

For comprehensive test patterns -- Pest setup, element factories, HTTP testing, queue assertions, database assertions, multi-site testing, mocking, console commands, and event testing -- see `testing.md`.

Quick reference:

```json
{
    "require-dev": {
        "markhuot/craft-pest": "^3.0"
    }
}
```

Run: `ddev craft pest/test`

## Code Review Checklist

For the full PHP coding standards, see the `craft-php-guidelines` skill. Key checks before every commit:

1. `ddev composer check-cs` passes
2. `ddev composer phpstan` passes
3. Tests green
4. PHPDocs complete -- classes, methods, properties, `@throws` chains
5. Section headers present with `=========` separators
6. Imports alphabetical and grouped
7. Permissions on all controller actions
8. `requirePostRequest()` on mutating actions
9. `addSelect()` convention in `beforePrepare()` (additive across extensions)
10. Events fired for extensibility
11. MemoizableArray cache invalidated on data changes
12. No N+1 queries -- eager loading used where needed
13. Large operations pushed to queue
14. Conventional commit message prepared
