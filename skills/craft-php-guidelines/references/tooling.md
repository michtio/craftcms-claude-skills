# Tooling — ECS, PHPStan, Scaffolding, Commits

## ECS Configuration

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

Note: `ecs.php` uses `declare(strict_types=1)` because it's standalone config. Plugin source files do not.

There is no `CRAFT_CMS_5` set — `SetList::CRAFT_CMS_4` is the correct, current set for Craft 5 projects.

## PHPStan Configuration

```neon
includes:
    - vendor/craftcms/phpstan/phpstan.neon
    - phpstan-baseline.neon

parameters:
    level: 5                          # level 5 is the Craft community baseline
    paths: [src]
    treatPhpDocTypesAsCertain: false   # PHPDoc types are hints, not guarantees
    tmpDir: %currentWorkingDirectory%/tmp/phpstan
    ignoreErrors:
        - '#PHPDoc tag @mixin contains invalid type#'
        - '#^Dead catch#'
```

### PHPStan and Craft::$app

`Craft::$app` inherits its static type from Yii: `\yii\console\Application|\yii\web\Application`. That union doesn't expose Craft-specific methods (`getConfig()`, `getView()`, `getElements()`, `getEntries()`, `getProjectConfig()`, `getRequest()`, etc.) which live on `craft\base\ApplicationTrait`. Calling `Craft::$app->getConfig()` works at runtime but PHPStan errors with `Call to an undefined method`.

Narrow with a typed local. This is the pattern Craft core uses (CP controllers, dashboard widgets, debug panels):

```php
// CP-only paths (controllers, settings, CP templates)
/** @var \craft\web\Application $app */
$app = Craft::$app;
$app->getConfig()->getConfigFromFile('my-plugin');

// Console-only paths (console controllers, queue jobs)
/** @var \craft\console\Application $app */
$app = Craft::$app;
$app->getRequest()->getParams();
```

For code that runs on both web and console where you only need `ApplicationTrait` methods:

```php
/** @var \craft\web\Application|\craft\console\Application $app */
$app = Craft::$app;
$app->getElements()->saveElement($element);
```

Don't use `@phpstan-ignore-line` to silence these. The typed local is the documented pattern. Reserve ignores for genuine library-typing gaps that can't be resolved with a cast.

## Scaffolding

The following component types have generator support via `craftcms/generator`. Always scaffold with the generator instead of creating manually:

```bash
ddev craft make element-type --with-docblocks
ddev craft make field-type --with-docblocks
ddev craft make controller --with-docblocks
ddev craft make command --with-docblocks
ddev craft make service --with-docblocks
ddev craft make model --with-docblocks
ddev craft make record --with-docblocks
ddev craft make queue-job --with-docblocks
ddev craft make validator --with-docblocks
ddev craft make widget-type --with-docblocks
ddev craft make utility --with-docblocks
ddev craft make behavior --with-docblocks
ddev craft make asset-bundle --with-docblocks
ddev craft make twig-extension --with-docblocks
ddev craft make element-action --with-docblocks
ddev craft make element-condition-rule --with-docblocks
ddev craft make element-exporter --with-docblocks
ddev craft make filesystem-type --with-docblocks
ddev craft make gql-directive --with-docblocks
```

Always use `--with-docblocks`. Then customize: add section headers, `@author`, `@since`, `@throws` chains, and project naming conventions.

The following component types have **no generator** — create manually following the naming conventions and PHPDoc standards: traits, helpers, error/exception classes, event classes, enums, variable classes, table constant classes (`db/Table.php`), and translation files.

Full generator reference: https://craftcms.com/docs/5.x/extend/generator.html

## Composer Hygiene for Plugin Repos

A plugin repo has to resolve on a machine that is not yours. Four rules cover the ways that breaks.

### Never ship `../*` path repositories

```json
{
    "repositories": [
        { "type": "path", "url": "../*" }
    ]
}
```

This resolves only where that relative layout happens to exist — your disk. Anyone cloning the repo, and every CI runner, gets an unresolvable dependency. It's a convenience that leaks the author's directory structure into the package's public contract.

**Unpublished sibling dependencies get a `vcs` entry instead**, which resolves anywhere the repo is reachable:

```json
{
    "repositories": [
        { "type": "vcs", "url": "https://github.com/acme/craft-shared-lib" }
    ],
    "require": {
        "acme/craft-shared-lib": "^1.0"
    }
}
```

**Packagist dependencies need no `repositories` entry at all.** Adding one is noise that can shadow the real source.

Path repos are still fine for **local development** — just keep them out of the committed manifest. Put them in a git-ignored `composer.local.json`, or use a globally configured path repo, or configure the *host project* (not the plugin) with the path repo. See the `ddev` skill for the volume-mount requirement that makes path repos work inside containers. For path-repository *semantics* — canonical resolution (Packagist versions dropped from the pool), no `exclude` on wildcards, `extra.branch-alias`, duplicate package names masking unsatisfiable constraints — see the `craft-plugin-release` skill's `references/path-repositories.md`.

### `suggest` is prose, not a dependency

When auditing what a plugin actually depends on, only `require` and `require-dev` create resolution edges. A `suggest` entry is a display string — Composer never resolves, installs, or version-checks it. Don't count `suggest` entries as dependencies when scanning for real coupling, and don't rely on one to make a peer package present.

### `composer.lock` stays gitignored for plugins

A plugin is a library: the consuming project pins versions, so a committed lock file is at best ignored and at worst misleading about what the plugin supports. Applications commit their lock; libraries don't.

```gitignore
composer.lock
```

The consequence to expect: every CI run resolves fresh, which is exactly what surfaces a broken `repositories` entry — a feature, not a cost.

### Prove standalone resolvability

The check that actually catches these problems, because it removes your machine's state from the equation:

```bash
# 1. Confirm no global repositories are silently supplying dependencies.
#    Expect empty output (or "[]"). A global path repo here makes a broken
#    manifest look fine locally and fail everywhere else.
composer config --global repositories

# 2. Resolve from scratch with no lock file.
rm -f composer.lock
composer update --dry-run
```

Step 1 is the one people skip, and it's the one that explains the "works on my machine" cases. If a global path repo exists, either remove it or run the dry-run in a container to get a clean environment.

### Remove per-repo CI workarounds once the `vcs` entry exists

Repos that shipped `../*` path repos usually grew a CI step to compensate — a `composer config repositories.x vcs …` line injected before install, or a checkout of the sibling into a synthesized path. Once the manifest carries a proper `vcs` entry, those steps are dead weight that hides the real configuration and drifts from it:

```yaml
# DELETE once composer.json has the vcs repository entry
- name: Configure sibling repo
  run: composer config repositories.shared-lib vcs https://github.com/acme/craft-shared-lib
```

Leaving it means CI is testing a different manifest than the one users get — which is how a broken `repositories` block stays green for months.

## Commit Messages

Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs:`, `test:`, `chore:`.

`--amend` for fixes to the most recent unpushed commit. New commit once pushed.

Single-line: `git add path/to/files && git commit -m "type(scope): description"`.
