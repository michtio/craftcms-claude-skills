# Database Isolation

How to make a plugin's Pest suite run against its own database, install what it needs, and not depend on what happens to be lying around. Verified against `markhuot/craft-pest-core` 3.2.2 and `craftcms/cms` 5.10.11.

## Contents

- What craft-pest-core actually does at boot
- Pinning the test database (`tests/bootstrap.php`)
- `phpunit.xml.dist` — the second half of the belt-and-braces
- Installing the plugin under test
- `RefreshesDatabase` — what rolls back and what doesn't
- Invocation paths (safe and unsafe)
- Ambient state: editions, counts, pre-existing fixtures

## What craft-pest-core actually does at boot

`markhuot\craftpest\pest\InstallsCraft` implements Pest's `HandlesArguments`, so it runs **before** PHPUnit processes the XML config. Its `handleArguments()` does, in order:

1. `loadPhpunitXmlEnvironmentVariables()` — parse `getcwd().'/phpunit.xml(.dist)'` and `putenv()` / `$_ENV` / `$_SERVER` every `<php><env>` entry.
2. `requireCraft()` — `require` craft-pest's bootstrap, which builds a `craft\web\Application`, and set a stub controller so plugins can touch `Craft::$app->controller` without erroring.
3. `install()` unless `--skip-install` was passed:
   - `craftInstall()` if `!Craft::$app->getIsInstalled(true)` — runs Craft's `Install` migration, saves modified project-config data, force-reloads plugins, sets the edition from `system.edition`.
   - `craftMigrateAll()` if there are new content migrations.
   - flush the data cache, then `applyExternalChanges()` if project config has pending changes.

Two things follow from this that matter more than anything in the README:

**It boots a web application under the CLI SAPI.** `Craft::$app` is `craft\web\Application`, but there is no real request — no user agent, no client IP. That is what breaks real logins (see `craft-state.md`).

**It never installs the plugin under test.** There is no step that calls `installPlugin()`. Craft gets installed; *your* plugin does not. If the plugin's tables and settings exist at all, it's because either (a) the database already had them, or (b) the plugin appears in a project config that `applyExternalChanges()` applied. Neither is something a plugin repo should rely on.

## Pinning the test database (`tests/bootstrap.php`)

Craft resolves its database from `CRAFT_DB_*` env vars via `App::env()`, which reads `$_SERVER` first, then `$_ENV`, then `getenv()`. So the pin must be set in **all three**, and it must happen **before Craft boots**.

```php
<?php
// tests/bootstrap.php

require_once dirname(__DIR__) . '/vendor/autoload.php';

// Pin the test database BEFORE Craft boots. $_SERVER first: App::env() reads it
// ahead of $_ENV/getenv(), and DDEV exports CRAFT_DB_* into $_SERVER, so setting
// only putenv() leaves the DDEV value winning.
$pins = [
    'CRAFT_DB_DATABASE' => 'db_test',
];

foreach ($pins as $name => $value) {
    $_SERVER[$name] = $value;
    $_ENV[$name] = $value;
    putenv("{$name}={$value}");
}
```

Point Pest at it with `bootstrap="tests/bootstrap.php"` in `phpunit.xml.dist`.

Why this file *and* the XML `<env>` entries: the bootstrap works regardless of how the suite is invoked (it's a plain `require`), while the `<env>` entries are what `InstallsCraft` reads on the correct-invocation path. Belt and braces — either one alone leaves a hole.

**Create the database first.** Nothing in this chain creates it: `ddev mysql -e 'CREATE DATABASE IF NOT EXISTS db_test'`.

## `phpunit.xml.dist` — the second half

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="tests/bootstrap.php"
         colors="true">
    <testsuites>
        <testsuite name="Plugin">
            <directory>tests</directory>
        </testsuite>
    </testsuites>
    <source>
        <include>
            <directory>src</directory>
        </include>
    </source>
    <php>
        <env name="CRAFT_DB_DATABASE" value="db_test"/>
        <env name="QUEUE_DRIVER" value="sync"/>
        <env name="CRAFT_INSTALL_EMAIL" value="test@example.com"/>
        <env name="CRAFT_INSTALL_PASSWORD" value="secret"/>
        <env name="CRAFT_INSTALL_SITEURL" value="http://localhost:8080"/>
    </php>
</phpunit>
```

Notes on the `<env>` entries:

- `InstallsCraft` `putenv()`s these **overriding** existing values, which is what makes the DB pin effective on the correct-invocation path.
- `CRAFT_INSTALL_*` feed `craftInstall()` (`InstallsCraft::craftInstall()` reads `CRAFT_INSTALL_USERNAME` / `_EMAIL` / `_PASSWORD` / `_SITENAME` / `_SITEURL` / `_LANGUAGE`, each with a fallback) — set them so a fresh test database installs deterministically instead of with `user@example.com` / `secret`.
- `QUEUE_DRIVER=sync` matters if you use craft-pest's queue assertions: its `Queues` trait runs the queue in `assertPostConditions()` **only** when the component is a `yii\queue\sync\Queue`. See `craft-state.md` for why you don't want the real queue either way.
- PHPUnit's own `force="true"` attribute is **not** a substitute — it doesn't overwrite `$_SERVER`, and `App::env()` reads `$_SERVER` first. That's the trap the `tests/bootstrap.php` pins exist to close.

## Installing the plugin under test

Because `InstallsCraft` won't do it, the bootstrap must — after Craft is booted, before tests run. The practical place is a Pest lifecycle hook or the tail of a custom bootstrap that boots Craft itself. Install dependency plugins first; a plugin whose `Install.php` references another plugin's tables will fail otherwise.

```php
// tests/Pest.php (or the tail of a custom bootstrap)
use markhuot\craftpest\test\RefreshesDatabase;
use markhuot\craftpest\test\TestCase;

uses(TestCase::class, RefreshesDatabase::class)->in(__DIR__);

// Install dependencies first, then the plugin under test. Idempotent: safe to
// run on every boot, and required on a fresh test database.
$plugins = Craft::$app->getPlugins();

foreach (['some-dependency', 'my-plugin'] as $handle) {
    if (!$plugins->isPluginInstalled($handle)) {
        $plugins->installPlugin($handle);
    }
}
```

Two consequences worth knowing:

- **`installPlugin()` runs `Install.php::safeUp()` exactly once per test-database lifetime.** Later edits to `Install.php` never re-apply. Ship schema changes as numbered migrations (whose applied state lives in the `migrations` table) so they reach the test DB. See `shared-state.md` (Schema drift).
- **`installPlugin()` writes to project config**, so it must happen outside a rolled-back transaction — at bootstrap, not in `beforeEach()`.

## `RefreshesDatabase` — what rolls back and what doesn't

`setUpRefreshesDatabase()` calls `beginTransaction()`; `tearDownRefreshesDatabase()` rolls back, then rolls back auto-committed models, then detaches its listeners. Also rolled back: `Craft::$app->info->configVersion`, which the trait restores to its pre-test value.

What it does **not** cleanly cover:

- **DDL.** MySQL implicitly commits on `ALTER TABLE`. The trait watches for this via the factory store events — if Yii thinks it's in a transaction but PDO isn't, it records the model in `$autoCommittedModels` and starts a fresh transaction. On teardown it can only clean up `craft\base\Field` instances; anything else throws `Found orphaned model [...] that was not cleaned up in a transaction`. Practical rule: create fields before elements, and don't do schema work inside a test.
- **Project-config writes.** They bump the in-memory memoized `configVersion` while the rollback discards the row that would match it, desyncing the two. Later writes then throw `BusyResourceException` / `StaleResourceException` — a cascade whose root cause is several tests upstream. See `craft-state.md` (Project-config writes).
- **Anything outside the database.** Files written to storage, caches (unless you flush them), external HTTP calls.

## Invocation paths

| Invocation | `getcwd()` | `<env>` pins loaded? | Verdict |
|------------|-----------|----------------------|---------|
| `vendor/bin/pest` from the plugin root | plugin root | yes | Safe |
| `composer test` from the plugin root | plugin root | yes | Safe |
| `ddev exec --dir /var/www/html/vendor/acme/my-plugin vendor/bin/pest` | plugin root | yes | Safe |
| `ddev craft pest -- --configuration=vendor/acme/my-plugin/phpunit.xml.dist` | project root | **no** | Unsafe |
| `vendor/bin/pest -c path/to/plugin/phpunit.xml.dist` from a project root | project root | **no** | Unsafe |

The unsafe rows still *run* — PHPUnit reads the config for discovery. They just run against whatever database the project's own environment resolves to. Encode the safe form in `composer.json` so nobody has to remember:

```json
{
    "scripts": {
        "test": "pest"
    }
}
```

## Ambient state: what a shared install quietly supplies

A suite developed against a populated dev install accumulates assumptions it never states. They all present the same way: green locally, red under real isolation.

### Pin the edition explicitly

`Craft::$app->setEdition()` writes `system.edition` to project config and sets `$this->edition`, so under `RefreshesDatabase` it rolls back with the transaction. Pin it in `beforeEach()` for anything edition-sensitive rather than inheriting whatever the dev install happens to be:

```php
use craft\enums\CmsEdition;

beforeEach(function () {
    Craft::$app->setEdition(CmsEdition::Pro);
});
```

Two common edition traps: **Solo silently caps user creation at one** (`User::beforeSave()` vetoes further saves without throwing, so a factory creating a second user fails silently), and **`UserPermissions::saveGroupPermissions()` calls `requireEdition(CmsEdition::Team)`** — a permission test dies on Solo.

### Scope every count assertion

An unfiltered `COUNT(*)` is an assertion about the whole database, not about your test.

```php
// Brittle — passes only on a database with exactly this much data
expect($service->getAll())->toHaveCount(3);

// Portable — asserts on what this test created
$handles = collect($created)->pluck('handle')->all();
expect($service->getAll())->toContain(...)
    ->and(collect($service->getAll())->whereIn('handle', $handles))->toHaveCount(3);
```

Same rule for `assertDatabaseCount()` — always pass a filtering condition that matches only test-created rows.

### Assert only on data the test created

Don't reach for a section, user group, field, or entry that "is always there." Create it in the test (the transaction cleans it up) or seed it explicitly. A row that exists on your machine and not on CI produces an integrity-constraint violation, not a helpful failure. See `shared-state.md` (Self-seeding) for the delete-then-insert pattern that stays portable under unique constraints.
