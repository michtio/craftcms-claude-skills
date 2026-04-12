# Tooling — ECS, PHPStan, Scaffolding, Commits

## ECS Configuration

```php
<?php

declare(strict_types=1);

use craft\ecs\SetList;
use Symplify\EasyCodingStandard\Config\ECSConfig;

return static function(ECSConfig $ecsConfig): void {
    $ecsConfig->parallel();
    $ecsConfig->paths([
        __DIR__ . '/src',
        __FILE__,
    ]);
    $ecsConfig->sets([SetList::CRAFT_CMS_4]);
};
```

Note: `ecs.php` uses `declare(strict_types=1)` because it's standalone config. Plugin source files do not.

## PHPStan Configuration

```neon
includes:
    - vendor/craftcms/phpstan/phpstan.neon
    - phpstan-baseline.neon

parameters:
    level: 5
    paths:
        - src
    treatPhpDocTypesAsCertain: false
    tmpDir: %currentWorkingDirectory%/tmp/phpstan
```

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

## Commit Messages

Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs:`, `test:`, `chore:`.

`--amend` for fixes to the most recent unpushed commit. New commit once pushed.

Single-line: `git add path/to/files && git commit -m "type(scope): description"`.
