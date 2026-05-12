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
| 10 | Even stricter mixed handling, including implicit mixed from missing types (PHPStan 2.0+) |

`--level max` is an alias for the highest level (currently 10).

**Recommendation:** Start at level 5 for new plugins. It catches real bugs (wrong argument types) without drowning you in missing-typehint noise from Craft's loose-typed APIs (largely magic getters on Yii Components). Raise incrementally as the codebase matures — level 8 enforces null-strictness which is genuinely valuable; level 9-10 push into territory where the noise/value ratio gets thin on plugin code. The Craft community baseline is 5.

## craftcms/phpstan Package

Every Craft 5 plugin should use the official PHPStan extension. Without it, PHPStan cannot understand Craft's service locator, element queries, or component accessors — and hand-rolled `scanFiles` / `scanDirectories` pointed at `vendor/craftcms/cms/src` or `vendor/yiisoft/yii2` will silently miss the stubs.

What it ships (verified against [craftcms/phpstan](https://github.com/craftcms/phpstan)):

- **Stubs** for `yii\BaseYii`, `craft\web\Application`, `craft\console\Application`. The `BaseYii.stub` declares `Craft::$app` as the non-nullable union `\craft\web\Application|\craft\console\Application`. Without it, PHPStan at level 5+ flags every `Craft::$app->getView()` / `getRequest()` / `getConfig()` / `getElements()` call as "call on possibly null" or "undefined method on Yii union" — the union those methods live on (`craft\base\ApplicationTrait`) isn't visible without the stub.
- **`scanFiles`** entries for `Craft.php`, `Yii.php`, and Twig's `CoreExtension.php` so static analysis sees those globals/macros.
- **`earlyTerminatingMethodCalls`** for `Craft::dd`, `yii\base\Application::end`, and `yii\base\ErrorHandler::convertExceptionToError` — code after those calls is correctly treated as unreachable.

Install:

```json
"require-dev": {
    "craftcms/phpstan": "dev-main"
}
```

Then `ddev composer update craftcms/phpstan`.

Include in `phpstan.neon` (before your baseline):

```neon
includes:
    - vendor/craftcms/phpstan/phpstan.neon
```

That's the full required wiring. Don't roll your own `scanFiles` / `scanDirectories` pointed at Craft or Yii source — the extension is the canonical reference and removes variance. The failure mode otherwise is a paradox: a hand-rolled config sometimes passes locally (cached PHPStan results, an older `craftcms/cms` in `vendor/`) and then fails on a fresh CI install when newer Craft versions tighten type declarations.

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

### Why `treatPhpDocTypesAsCertain: false`

The `craftcms/phpstan` stubs declare `Craft::$app` as `\craft\web\Application|\craft\console\Application` — a non-nullable union. That assertion holds during normal request handling but is wrong in two situations:

1. **Unit tests that don't bootstrap a full Craft app.** A Pest/PHPUnit test that instantiates a service directly to test a pure-PHP method may run with `Craft::$app === null`.
2. **Very early bootstrap**, before `BaseYii::createApplication()` has run.

If your code carries defensive guards like:

```php
if (!Craft::$app instanceof WebApplication && !Craft::$app instanceof ConsoleApplication) {
    return;
}
```

PHPStan with the stubs flags the second clause as "always false" because the stub asserts `$app` is one of those two types. Setting `treatPhpDocTypesAsCertain: false` tells PHPStan to treat stub-declared types as advisory rather than certain, so the guards remain live code rather than dead branches.

Only set it when you actually carry these guards. If every code path in your plugin runs inside a request and you don't need null-defensive code, leave the setting off and let the stubs do their job.

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

A published Craft 5 plugin typically ships with **two** GitHub Actions workflows in `.github/workflows/`:

1. **`code-analysis.yaml`** — runs ECS, PHPStan, and tests on every PR and push. The quality gate.
2. **`create-release.yml`** — listens for a `repository_dispatch` event from the Craft Console plugin store and creates the GitHub release with the supplied notes. The publish path.

Missing either one ships an unfinished plugin: without `code-analysis`, regressions land silently; without `create-release`, every Craft Console publish leaves you with a git tag but no GitHub release page, and users clicking through release links land on a 404.

### code-analysis.yaml

```yaml
name: Code Analysis

on:
  pull_request: null
  push:
    branches:
      - main          # or develop-v5, develop, whatever your release branch is
  workflow_dispatch:

permissions:
  contents: read

jobs:
  code_analysis:
    name: PHP ${{ matrix.php }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        php: ['8.2', '8.3', '8.4']
    steps:
      - uses: actions/checkout@v4
      - name: Cache Composer dependencies
        uses: actions/cache@v4
        with:
          path: /tmp/composer-cache
          key: ${{ runner.os }}-php-${{ matrix.php }}-${{ hashFiles('**/composer.json') }}
          restore-keys: ${{ runner.os }}-php-${{ matrix.php }}-
      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: ${{ matrix.php }}
          extensions: 'ctype,curl,dom,iconv,intl,json,mbstring,openssl,pcre,pdo,reflection,spl,zip'
          ini-values: post_max_size=256M, max_execution_time=180, memory_limit=512M
          tools: composer:v2
      - name: Install Composer dependencies
        # --no-blocking lets the install proceed despite upstream advisories on
        # Craft's transitive deps (yii2, graphql-php). They're Craft's surface
        # to fix; this plugin can't and shouldn't gate its own CI on them.
        run: composer install --no-interaction --no-ansi --no-progress --no-blocking
      - name: PHPStan
        run: composer phpstan
      - name: Coding Standards
        run: composer check-cs
      - name: Pest
        run: composer test
```

Notes:

- **PHP matrix matters.** Craft 5 supports PHP 8.2–8.4. Test all three; 8.4 surfaces deprecation warnings that 8.2 doesn't, and 8.2 catches accidental use of features that only landed in 8.3/8.4.
- **`--no-blocking` is the canonical flag.** Composer 2.5+ refuses to install packages flagged in the security-advisories registry by default. Craft 5.9.x transitively depends on `yiisoft/yii2 2.0.54` (CVE-2026-39850, fixed in 2.0.55) and `webonyx/graphql-php 14.11.10` (covered by advisories on `<=15.32.2`). Both are upstream concerns Craft will pick up on its next release; a downstream plugin can't fix them. The flag bypasses the block.
- **Legacy flag name.** Older Composer versions used `--no-security-blocking`. Composer's own docs deprecated that in favour of `--no-blocking`. Existing workflows using the old name still work but should be updated.
- **Don't substitute `--no-audit`.** Different flag with different scope: `--no-audit` suppresses the post-install audit *report*, but it doesn't bypass the install-time blocking *policy*. You'll still hit the advisory error.
- **Plugins that don't ship a `composer.lock`** (the common library pattern, since the consuming project pins versions) hit this on every fresh CI run. Plugins that *do* commit a lockfile only hit it when they regenerate.
- **`pull_request: null`** is a deliberate shorthand for "run on all PR events with default config" — equivalent to `pull_request: {}`.

### create-release.yml

When Craft Console (the plugin marketplace) publishes a new version of your plugin, it sends a `repository_dispatch` event with the release metadata. This workflow listens for it and creates the matching GitHub release:

```yaml
name: Create Release
run-name: Create release for ${{ github.event.client_payload.version }}

on:
  repository_dispatch:
    types:
      - craftcms/new-release

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: ncipollo/release-action@v1
        with:
          body: ${{ github.event.client_payload.notes }}
          makeLatest: ${{ github.event.client_payload.latest }}
          name: ${{ github.event.client_payload.version }}
          prerelease: ${{ github.event.client_payload.prerelease }}
          tag: ${{ github.event.client_payload.tag }}
```

What's happening:

- **Trigger:** `repository_dispatch` with the literal event type `craftcms/new-release`. Craft Console fires this when you cut a release through their UI.
- **Payload:** `github.event.client_payload` carries `version`, `notes`, `latest`, `prerelease`, `tag` — all populated from your Craft Console release form (the notes come from the matching CHANGELOG section that Craft parsed).
- **Action:** `ncipollo/release-action@v1` creates the GitHub release with the supplied tag and notes, marking it latest/prerelease according to the payload.
- **Permissions:** the job needs `contents: write` to create releases. The default token's `contents: read` isn't enough.

The release workflow doesn't need a Composer install or test run — the assumption is `code-analysis.yaml` already gated the merged code. The release flow is purely a "wrap the tag in a release object" operation.

### Order rationale (code-analysis)

1. **PHPStan / ECS** (seconds to a minute) — fail fast on type errors and formatting before expensive test runs
2. **Pest** — integration tests last, only if static checks pass

Whether to run ECS or PHPStan first is preference; both fail fast on cheap signals. craft-tailwind runs PHPStan first; the previous version of this doc recommended ECS first. Either is defensible.

### Caching

- **Composer vendor** — keyed by `composer.json` hash (or `composer.lock` if your plugin ships one).
- **PHPStan result cache** — keyed by commit SHA with branch prefix fallback. Optional but cuts repeated-PR runtime substantially. Add a separate `actions/cache@v4` step pointing at `tmp/phpstan` and reference it from `phpstan.neon` via `tmpDir`.

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
