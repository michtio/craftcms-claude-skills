# Database Isolation

How to make a plugin's Pest suite run against its own database, install what it needs, and not depend on what happens to be lying around. Verified against `markhuot/craft-pest-core` 3.2.2 and `craftcms/cms` 5.10.12.

## Contents

- What craft-pest-core actually does at boot
- Pinning the test database (`tests/bootstrap.php`)
- Pin the process timezone *after* the app is created
- `phpunit.xml.dist` — the second half of the belt-and-braces (force the DB name, default the coordinates)
- One MySQL server, many suites: pin `CRAFT_ENVIRONMENT` too
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

**Then make the guard fail closed.** Pins can be bypassed (a new invocation path, a CI runner with different env precedence, a refactored bootstrap), and the failure mode is silent writes to a live install — one real suite had been quietly writing to a development database *and running `migrate/up` through the tool under test*. Add a hard assertion to `tests/bootstrap.php` after the pins, before anything else runs:

```php
// Fail closed: refuse to run against anything but the test database.
// THROW — do not exit(1). See below.
$db = App::env('CRAFT_DB_DATABASE');
if ($db !== 'db_test') {
    throw new RuntimeException("Tests resolved database '{$db}', expected 'db_test'.");
}
```

A wrong database is now a loud one-line failure instead of a polluted install discovered weeks later. Keep the check on the *resolved* value (`App::env()`), not on what you just pinned — the point is to catch the paths where the pin didn't take.

**The guard must throw, not `exit(1)`.** Under Pest, the process's exit status is decided by Pest's own shutdown handling — an `exit(1)` in the bootstrap prints the refusal and then hands the shell **0**. That is a guard that fails open exactly where it matters (CI), which is worse than no guard because it reads as protection. A thrown `RuntimeException` makes PHPUnit report "Error in bootstrap script" and exit non-zero.

Then prove the guard isn't vacuous: point the pin at a bogus database name, run the suite, and check `echo $?` is non-zero. A guard nobody has watched fire is a comment, not a guard.

## Pin the process timezone *after* the app is created

Creating the Craft app sets the PHP process timezone from the install's config, and on a fresh install that value is **not** UTC.

The chain: `ApplicationTrait::_setTimeZone()` runs during init and resolves

```php
$timeZone = $this->getConfig()->getGeneral()->timezone ?? $this->getProjectConfig()->get('system.timeZone');
// ...
$this->setTimeZone(App::parseEnv($timeZone));   // → Yii's Application::setTimeZone()
```

and Yii's `Application::setTimeZone()` is literally `date_default_timezone_set($value)`. Craft's own install migration seeds `'timeZone' => 'America/Los_Angeles'` (`craft\migrations\Install`), so a test database installed from scratch hands your process a UTC-8/-7 clock.

Every `DateTime` built after that point is constructed in that zone. Craft stores datetimes in UTC, so values round-trip through saved element attributes shifted by the full offset. The symptom is rarely "timezone" — it presents as intermittent, environment-dependent expiry logic: a token seeded as expired reads as still valid, or a "not yet due" fixture reads as overdue, depending on which side of the offset the test data sits.

Pin UTC **after** app creation, so your pin wins rather than being overwritten:

```php
// tests/bootstrap.php — after the app is created, not before

$app = require dirname(__DIR__) . '/vendor/craftcms/cms/bootstrap/console.php';

// Craft's init just called date_default_timezone_set() from system.timeZone,
// which is America/Los_Angeles on a fresh install. Re-pin so DateTimes built in
// tests match the UTC that Craft stores.
date_default_timezone_set('UTC');
```

Craft core does the same thing in its own example test-suite bootstrap (`src/test/internal/example-test-suite/tests/_bootstrap.php`), which opens with both `ini_set('date.timezone', 'UTC')` and `date_default_timezone_set('UTC')` — so this is core's convention, not a workaround.

Setting it *before* app creation (or in `php.ini`) is not sufficient on its own: init overwrites it. If you'd rather fix it at the source, set `timezone` in the test `config/general.php` or pin `system.timeZone` to UTC in the project config the test database installs from — then the value init applies is already UTC. Doing both is harmless.

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
        <!-- Force ONLY what local dev gets wrong: the database name and the
             table prefix. Everything else stays default-only so a CI job's own
             MySQL service env flows through. -->
        <env name="CRAFT_DB_DATABASE" value="db_test"/>
        <env name="CRAFT_DB_TABLE_PREFIX" value=""/>

        <!-- Defaults, not overrides: `default="true"` applies the value only when
             the variable isn't already set in the environment. -->
        <env name="CRAFT_DB_DRIVER" value="mysql" default="true"/>
        <env name="CRAFT_DB_SERVER" value="db" default="true"/>
        <env name="CRAFT_DB_PORT" value="3306" default="true"/>
        <env name="CRAFT_DB_USER" value="db" default="true"/>
        <env name="CRAFT_DB_PASSWORD" value="db" default="true"/>

        <env name="QUEUE_DRIVER" value="sync"/>
        <env name="CRAFT_INSTALL_EMAIL" value="test@example.com"/>
        <env name="CRAFT_INSTALL_PASSWORD" value="secret"/>
        <env name="CRAFT_INSTALL_SITEURL" value="http://localhost:8080"/>
    </php>
</phpunit>
```

### Force the database name, default everything else

The split above is what makes one config work on both a developer's machine and a CI runner, and it's worth understanding *why* rather than copying it.

**Force** the two things local dev genuinely gets wrong:

- `CRAFT_DB_DATABASE` — the whole point of the isolation. Local dev supplies the *development* database, and that is the value you must beat.
- `CRAFT_DB_TABLE_PREFIX` — a stale or absent prefix produces "table doesn't exist" errors that look like migration problems. Pin it explicitly to whatever your plugin expects (usually empty).

**Never unconditionally force** connection coordinates — driver, server, port, user, password. Those are correct in each environment already and wrong everywhere else. Hardcoding a local hostname is the specific trap: `<env name="CRAFT_DB_SERVER" value="db"/>` is right inside DDEV (where `db` is the database container) and breaks a GitHub Actions runner, where the service is reachable at `127.0.0.1`. The suite then fails to connect with an error that says nothing about the config that caused it.

If you've reached for an `/etc/hosts` alias in CI to make `db` resolve, that's the signal you've forced a value you should have defaulted. It's a workaround for a self-inflicted problem, not a pattern — remove the force instead.

PHPUnit's `default="true"` attribute is the right tool: the value is applied only when the variable is **not** already present in the environment. So a DDEV shell (which exports `CRAFT_DB_SERVER` etc.) and a CI job (which sets them in the workflow `env:`) both win, while a bare local run still gets something sensible. Compare `force="true"`, which overrides — and note that neither attribute touches `$_SERVER`, which is why the `tests/bootstrap.php` pins exist (see the caveat below).

The corollary on the CI side: the workflow supplies the connection coordinates in its own `env:` block, and they flow through untouched. See `ci.md` (Database service).

Notes on the `<env>` entries:

- `InstallsCraft` `putenv()`s these **overriding** existing values, which is what makes the DB pin effective on the correct-invocation path.
- `CRAFT_INSTALL_*` feed `craftInstall()` (`InstallsCraft::craftInstall()` reads `CRAFT_INSTALL_USERNAME` / `_EMAIL` / `_PASSWORD` / `_SITENAME` / `_SITEURL` / `_LANGUAGE`, each with a fallback) — set them so a fresh test database installs deterministically instead of with `user@example.com` / `secret`.
- `QUEUE_DRIVER=sync` matters if you use craft-pest's queue assertions: its `Queues` trait runs the queue in `assertPostConditions()` **only** when the component is a `yii\queue\sync\Queue`. See `craft-state.md` for why you don't want the real queue either way.
- PHPUnit's own `force="true"` attribute is **not** a substitute — it doesn't overwrite `$_SERVER`, and `App::env()` reads `$_SERVER` first. That's the trap the `tests/bootstrap.php` pins exist to close.

## One MySQL server, many suites: pin `CRAFT_ENVIRONMENT` too

Forcing the database name is **not sufficient** for isolation. Craft's project-config lock lives at the *server* level, so suites in separate databases still collide. The symptoms: two suites running at once fail with `BusyResourceException`, `1213 Deadlock`, or `1412 Table definition has changed` — and giving one suite its own fresh, empty, exclusively-owned database does **not** fix it. It still dies inside `craft\migrations\Install` with `BusyResourceException`, with no other connection visible in `information_schema.processlist`.

The chain (verified in `craftcms/cms` 5.10.12):

- Craft's DB mutex is `App::dbMutexConfig()` → `yii\mutex\MysqlMutex` with `'keyPrefix' => Craft::$app->getEnvId()` (`src/helpers/App.php:1141`).
- `MysqlMutex` acquires `GET_LOCK(SUBSTRING(CONCAT(keyPrefix, sha1(name)), 1, 64), timeout)` — and **MySQL `GET_LOCK` names are scoped to the server, not the database.**
- `getEnvId()` is `id--env` (`ApplicationTrait::getEnvId()`), and craft-pest-core's own bootstrap does `define('CRAFT_ENVIRONMENT', getenv('ENVIRONMENT') ?: 'production')` (`src/bootstrap/bootstrap.php:32`). So every unpinned suite on the machine shares the env id `CraftCMS--production` — and therefore the same lock names, e.g. for `\craft\services\ProjectConfig::MUTEX_NAME` (`'project-config'`).

The fix is one more `<env>` pin, unique per plugin:

```xml
<env name="CRAFT_ENVIRONMENT" value="test-my-plugin"/>
```

Three details that each cost real time:

- **The pin must be `CRAFT_ENVIRONMENT`, never `CRAFT_APP_ID`.** Core reads `CRAFT_ENVIRONMENT` in `bootstrap/bootstrap.php`; core's own `src/config/app.php` hard-codes `'id' => 'CraftCMS'`. The `App::env('CRAFT_APP_ID') ?: 'CraftCMS'` line you may remember belongs to the **craftcms/craft starter project's** `config/app.php` — a plugin repo doesn't have that file, so a `CRAFT_APP_ID` pin is inert.
- **The `<env>` pin beats craft-pest's `define()`.** `InstallsCraft::loadPhpunitXmlEnvironmentVariables()` sets `$_SERVER` before craft-pest's bootstrap runs, and `App::env()` checks `$_SERVER` ahead of defined constants.
- **Pinning it is safe.** `getEnvId()` has exactly three readers in core — the mutex key prefix and the session/web-user state key prefixes — all process-local.

To verify which pin actually takes (or re-verify after a core bump), run the controlled experiment rather than reasoning about precedence: hold the lock by hand in one MySQL session —

```sql
SELECT GET_LOCK(SUBSTRING(CONCAT('CraftCMS--production', SHA1('project-config')), 1, 64), 0);
```

— then run the suite with each candidate pin. The pin that stops the suite from blocking on that held lock is the one that works; a pin the suite blocks *through* is inert.

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

### `--filter` subsets can fail on `cookieValidationKey`

A subset run (`vendor/bin/pest --filter=SomeTest`) can fail with a `cookieValidationKey` configuration error where the full suite passes — a craft-pest harness artefact of which tests boot which request machinery, not a bug in the plugin under test. Workaround: disable cookie validation in `beforeEach` for the affected files, with a comment saying why:

```php
beforeEach(function () {
    // craft-pest artefact: --filter subset runs die on cookieValidationKey
    // without this; the full suite passes either way.
    Craft::$app->getRequest()->enableCookieValidation = false;
});
```

Scope it to the files that need it — don't blanket it across the suite, where it could mask a real cookie-validation regression in code that touches cookies.

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
