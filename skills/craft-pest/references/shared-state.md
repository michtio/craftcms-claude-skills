# Suites That Run Against a Shared or Long-Lived Install

Isolating the database (see `isolation.md`) removes most of this class of problem. But a test database still *persists between runs*, and some suites deliberately run against a playground install people also use for manual QA. Both situations leak state, and the failures show up far from the cause.

## Contents

- Restore what you found — never hardcode the default
- Schema drift: `Install.php` vs migrations in the test database
- Self-seeding: local database ≠ CI
- Request-IP fixtures: overwrite the header *and* reset the memo
- Console-created users may require a password reset

## Restore what you found — never hardcode the default

A teardown that resets a project-config value to *Craft's* default is only correct if the default is what the install actually had. Usually it isn't. A real suite reset `users.allowPublicRegistration` to `false` in `afterEach` on every run, silently flipping the setting off and sabotaging manual QA that depended on it being on.

Capture the original in `beforeEach`, restore that exact value:

```php
beforeEach(function () {
    $this->originalAllowPublicRegistration =
        Craft::$app->getProjectConfig()->get('users.allowPublicRegistration');
});

afterEach(function () {
    // Restore what we found, not a hardcoded default.
    setProjectConfigValue(
        'users.allowPublicRegistration',
        (bool) $this->originalAllowPublicRegistration,
    );
});
```

Tests that need a specific state should set it explicitly rather than depending on ambient state — then the restore is a safety net, not a correctness requirement. Use the only-when-different guard from `craft-state.md` so the restore itself doesn't churn `configVersion`.

## Schema drift: `Install.php` vs migrations in the test database

A bootstrap that installs the plugin once and short-circuits afterwards is the right trade-off — slow first run, cheap re-runs:

```php
if (!$plugins->isPluginInstalled('my-plugin')) {
    $plugins->installPlugin('my-plugin');   // runs Install.php::safeUp()
}
```

The consequence: **once the test database has the plugin installed, `Install.php::safeUp()` never runs against it again.** Later edits to `Install.php` — new tables, renamed columns, primary-key rewrites — don't land. A test touching the new shape passes against a stale schema until someone drops the table.

Migrations under `src/migrations/m*.php` *do* propagate, because `MigrationManager` tracks applied state in the `migrations` table and runs only what's missing. So the symptom is asymmetric and easy to misread: changes shipped as a numbered migration reach the test DB; changes that **only** update `Install.php` (typical when iterating on a brand-new plugin — "no users yet, I'll just edit the fresh-install shape") silently don't.

**The durable fix is migration-driven.** Every schema change ships as a dated migration that handles both fresh installs and existing ones (`if (!$this->db->tableExists($table)) { … }`), and `Install.php` gets the same edit in lockstep as the canonical fresh shape. The test database picks up the migration on the next boot. This is the same mechanism your downstream users need — existing installs run the migration on `craft up` — so the test-DB drift problem and the user-upgrade problem have one solution.

**Verification after a schema change:** drop and recreate the test database, then run the suite. If a test passes against an already-installed test DB but fails against a fresh one, `Install.php` and the migration have drifted — either the migration is missing an idempotent `createTable`, or `Install.php` is missing a change only the migration carries.

```bash
ddev mysql -e 'DROP DATABASE db_test; CREATE DATABASE db_test;'
ddev exec --dir /var/www/html/vendor/acme/my-plugin vendor/bin/pest
```

**Anti-pattern: dropping the test database on every run.** Slow (full Craft + plugin install each time), breaks parallel workers, and it paves over the actual drift instead of surfacing it.

## Self-seeding: local database ≠ CI

A test that depends on rows which merely *happen to exist* locally passes locally and fails on CI, where the test database starts empty — typically an integrity-constraint violation when a foreign key points at a parent row that isn't there.

**Seed every row a test depends on inside the test, including FK-referenced parents.** Under `RefreshesDatabase` the seeding is undone automatically, so it's safe to repeat.

For a row under a unique constraint that exists locally but not on CI, delete-then-insert stays portable — the delete is a no-op on the empty CI database and clears the colliding row locally:

```php
Db::delete(Table::FOO, ['handle' => 'bar']);   // no-op on a clean CI database
Db::insert(Table::FOO, ['handle' => 'bar', /* ... */]);
```

**Operational rule:** a green local run is not authoritative for a plugin whose local database carries seed data. Confirm on CI, or against a freshly recreated test database.

## Request-IP fixtures: overwrite the header *and* reset the memo

craft-pest's fake web request carries `X-Forwarded-For: 127.0.0.1`. `craft\web\Request::getUserIP()` checks forwarded headers first (`X-Forwarded-For` is in `Request::$ipHeaders`), then memoizes the answer in the private `$_ipAddress` property and returns that cached value forever after.

So planting a test IP needs **both** the header overwrite and a reset of the memo — a header change alone is ignored once the value has been read once:

```php
$request = Craft::$app->getRequest();

// 1. Overwrite the forwarded header (checked before REMOTE_ADDR).
$request->getHeaders()->set('X-Forwarded-For', '203.0.113.7');

// 2. Reset the private memo so getUserIP() recomputes.
$ref = new ReflectionProperty(\craft\web\Request::class, '_ipAddress');
$ref->setAccessible(true);
$ref->setValue($request, null);

expect($request->getUserIP())->toBe('203.0.113.7');

// Restore both afterward so the next test starts clean.
```

## Console-created users may require a password reset

Users created with `craft users/create` may land with `passwordResetRequired` set, which blocks a normal login and confuses manual testing on a playground install. Clear the flag on fixtures created that way:

```php
$user->passwordResetRequired = false;
Craft::$app->getElements()->saveElement($user);
```

Note this is only the *login-blocking* half. `passwordResetRequired` is checked during authentication, not on every request, so setting it doesn't log anyone out — see the `craftcms` skill's `sessions-and-auth.md`.
