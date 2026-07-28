---
name: craft-pest
description: "Testing Craft CMS 5 plugins and modules with Pest — test isolation, database safety, and the markhuot/craft-pest-core harness. ALWAYS load when writing, running, fixing, or reviewing tests for a Craft plugin or module, and whenever a test suite touches a real Craft install. Covers: markhuot/craft-pest-core (TestCase, RefreshesDatabase, InstallsCraft, factories, HTTP/queue/DB assertions), transaction rollback and why it is opt-in, tests/Pest.php and tests/bootstrap.php wiring, phpunit.xml.dist <env> pins, pinning CRAFT_DB_DATABASE to a test database (db_test), why --configuration= silently defeats DB isolation, installing the plugin under test, muting audit/event sinks, stubbing the queue, permission-tree memoization (UserPermissions::reset()), simulating logins in a console-driven harness, UTC fixture timestamps, pinning the CMS edition, scoping count assertions, and CI test jobs. Triggers on: Pest, pestphp, craft-pest, craft-pest-core, markhuot, RefreshesDatabase, InstallsCraft, uses(TestCase::class), tests/Pest.php, phpunit.xml.dist, phpunit.xml, vendor/bin/pest, composer test, ddev craft pest, test isolation, test database, db_test, CRAFT_DB_DATABASE, factories, Entry::factory(), assertDatabaseHas, plugin test suite, integration tests, fixtures, transaction rollback, beforeEach/afterEach, 'tests pass locally but pollute the database', 'tests created thousands of entries', 'tests wrote real audit rows', 'suite passes on dev but fails in isolation', orphaned test data, flaky order-dependent test, CI test job, no Pest job in the workflow, tests exist but never run in CI, suite isn't CI-enforced, fix-cs vs check-cs in CI, reviewing a plugin's code-analysis.yaml for a missing test step. Do NOT trigger for front-end/JS testing (Playwright, Vitest), or for PHP style/static analysis (craft-php-guidelines)."
---

# Testing Craft CMS Plugins with Pest

Reference for testing Craft CMS 5 plugins and modules with Pest, primarily via `markhuot/craft-pest-core`.

The dominant failure mode in Craft plugin testing is not a wrong assertion — it's a suite that **writes to a database it shouldn't**, or that **passes only because of ambient state** on the developer's install. Both are silent. Both look like a green suite. This skill leads with isolation for that reason: get the harness right first, then write tests.

**Verified against `markhuot/craft-pest-core` 3.2.2 and `craftcms/cms` 5.10.11 (July 2026).** Where a claim names a class or method, it was read in that package's source. craft-pest's own README and docs are not authoritative on these points — several of the behaviors below are unstated there.

## Companion Skills — Load When Needed

- **`craftcms`** — Plugin/module architecture, elements, controllers, events, project config. Load when the code under test is being written or changed, not just exercised.
- **`craft-php-guidelines`** — PHP standards for the test files themselves (PHPDocs, naming, ECS).
- **`ddev`** — Every command runs through DDEV. Load for the correct invocation of a plugin's own suite inside a host project (`ddev exec --dir …`).

## Documentation

- Craft Pest: https://craft-pest.com
- Pest PHP: https://pestphp.com/docs/installation
- Codeception (Craft's native harness): https://craftcms.com/docs/5.x/extend/testing.html

Use `WebFetch` for specific pages, but prefer reading `vendor/markhuot/craft-pest-core/src/` when the question is "what does it actually do."

## The Two Non-Negotiables

Everything else in this skill is technique. These two are the ones that cause data loss.

### 1. Rollback is opt-in — `TestCase` alone commits everything

`markhuot\craftpest\test\TestCase` boots Craft and mixes in ~15 traits (`ActingAs`, `RequestBuilders`, `DatabaseAssertions`, `Queues`, …). **`RefreshesDatabase` is not one of them.** Only that trait opens a transaction (`setUpRefreshesDatabase()` → `beginTransaction()`) and rolls it back on teardown.

So a `tests/Pest.php` that binds only `TestCase` produces a suite where every factory call, every `saveElement()`, every service write **commits permanently** to whatever database Craft booted against. The tests pass. The database fills up.

```php
// tests/Pest.php — bind BOTH
uses(
    \markhuot\craftpest\test\TestCase::class,
    \markhuot\craftpest\test\RefreshesDatabase::class,
)->in(__DIR__);
```

If a suite genuinely needs committed data (rare — usually a sign the test should be restructured), scope the exception to that one file rather than dropping the trait globally.

### 2. The env override is CWD-bound — never run a plugin suite from a shared project root

`InstallsCraft::loadPhpunitXmlEnvironmentVariables()` (a Pest `HandlesArguments` plugin, so it runs before Craft boots) looks for exactly two paths:

```php
getcwd().'/phpunit.xml'
getcwd().'/phpunit.xml.dist'
```

It does **not** parse a `--configuration=` CLI flag. There is no fallback, no search upward, no argument inspection.

The consequence is the dangerous part. This invocation looks like it isolates the plugin's suite:

```bash
# UNSAFE for craft-pest-core suites
ddev craft pest -- --configuration=vendor/acme/my-plugin/phpunit.xml.dist
```

PHPUnit reads that config for test discovery, so tests are found and run — but `getcwd()` is the *project* root, so the **plugin's `<env>` DB pins are never loaded**. Craft boots against the live development database and, if `RefreshesDatabase` is also missing, writes to it permanently. That combination is how a suite silently creates thousands of orphaned elements in a shared install.

**Rule: run a plugin's suite from the plugin's own root.**

```bash
# From the plugin directory
vendor/bin/pest
composer test

# From a host project, targeting the plugin's own root
ddev exec --dir /var/www/html/vendor/acme/my-plugin vendor/bin/pest
```

Treat the shared-root `--configuration=` invocation as unsafe for any craft-pest-core suite, including in CI. See the `ddev` skill for the container-side invocation.

## Isolation Checklist

Run this against any plugin suite you inherit, write, or review. Each line has failed in practice.

| Check | Where | Failure if missing |
|-------|-------|--------------------|
| `RefreshesDatabase` bound alongside `TestCase` | `tests/Pest.php` | Every write commits permanently |
| `CRAFT_DB_DATABASE` pinned before Craft boots | `tests/bootstrap.php` | Suite runs against the dev database |
| Same pins present as `<env>` entries | `phpunit.xml.dist` | Correct-invocation path has no pins |
| Suite invoked from the plugin's own root | `composer test`, CI, DDEV | `<env>` pins silently ignored |
| Plugin under test explicitly installed | `tests/bootstrap.php` | Works only on an install that already has it |
| Edition pinned explicitly | `beforeEach()` | Passes on Pro, fails on Solo/Team |
| Count assertions scoped to test-created rows | each test | Passes on a seeded install, fails when clean |
| Audit/event sinks muted on **every** surface | shared helper | Tests write real audit rows |
| Queue replaced with a stub | shared helper | Tests drain or grow a real backlog |
| A Pest job actually runs in CI | `.github/workflows/` | The suite decays unnoticed |

## Reference Files

Read the reference file(s) your task needs — each costs input tokens on every turn.

**Task examples:**
- "Set up Pest for a new plugin" → `isolation.md` (bootstrap + phpunit.xml) then `patterns.md`
- "Tests are writing to my dev database / created thousands of entries" → `isolation.md`
- "Suite passes locally but fails on CI or against a fresh test DB" → `isolation.md` (Ambient state) + `shared-state.md`
- "Write a test for a controller action / element factory / queue job" → `patterns.md`
- "Test dynamically-registered permissions" → `craft-state.md` (Permission-tree memoization)
- "Test something that requires a logged-in user" → `craft-state.md` (Simulating a login)
- "Tests wrote real audit rows / fired real webhooks" → `craft-state.md` (Muting event surfaces)
- "Raw SQL fixture isn't treated as expired" → `craft-state.md` (Fixture timestamps)
- "Tests pollute a shared playground install" → `shared-state.md`
- "`Install.php` changes aren't reaching the test database" → `shared-state.md` (Schema drift)
- "Wire tests into CI" → `ci.md`

| Reference | Scope |
|-----------|-------|
| `references/isolation.md` | Database isolation: `tests/bootstrap.php`, `phpunit.xml.dist`, `RefreshesDatabase`, `InstallsCraft` boot vs plugin install, invocation paths, ambient-state assumptions (editions, counts, pre-existing fixtures) |
| `references/craft-state.md` | Craft internals that bite in tests: permission-tree memoization, login/session gates, UTC fixture timestamps, muting audit/event surfaces, queue stubs, project-config writes |
| `references/patterns.md` | Writing the tests: factories, HTTP, queue, database assertions, multi-site, mocking Craft services, console commands, events, file/test conventions |
| `references/shared-state.md` | Suites that run against a shared or long-lived install: restore-what-you-found, `Install.php` vs migration drift in the test DB, self-seeding, request-IP fixtures |
| `references/ci.md` | CI wiring: `check-cs` not `fix-cs`, a real Pest job, invocation from the plugin root, fresh-database verification |

## Two Harnesses (and when Pest isn't the answer)

| Aspect | Codeception (Craft's native) | Pest + craft-pest-core |
|--------|------------------------------|------------------------|
| Base class | `craft\test\TestCase` | `markhuot\craftpest\test\TestCase` |
| Element creation | Fixture classes + data files | `Entry::factory()->create()` |
| HTTP | `FunctionalTester` (`$I`) | `$this->get('/path')->assertOk()` |
| Rollback | Fixture teardown | `RefreshesDatabase` trait (opt-in) |

Use Pest for new plugin work. Use Codeception when contributing to Craft core or extending an existing Codeception suite.

For **pure unit tests** that don't need Craft booted, skip craft-pest entirely and extend `PHPUnit\Framework\TestCase` — booting Craft is the expensive, stateful part, and a test that doesn't need a database shouldn't risk one. See `patterns.md` (Pure unit tests) for the `\Craft` / `\Yii` autoload caveat.

## What a Green Suite Does Not Prove

Worth holding in mind, because each of these has shipped a real bug past a passing test run:

- **Service-layer tests never see the HTTP layer.** Reserved query params, CSRF, route resolution, and response formats only fail on a real request. See the `craftcms` skill's `controllers.md`.
- **A green run on a seeded dev install is not authoritative.** Confirm against a freshly created test database before believing it.
- **A console-driven harness is not a browser.** Sessions, user-agent gates, and impersonation behave differently. See `craft-state.md`.
- **A suite that isn't in CI doesn't exist.** It rots at the speed of the codebase. See `ci.md`.
