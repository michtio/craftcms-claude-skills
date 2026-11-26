---
name: craft-pest
description: "Testing Craft CMS 5 plugins and modules with Pest: test isolation, database safety, and the markhuot/craft-pest-core harness. ALWAYS load when writing, running, fixing, or reviewing tests for a Craft plugin or module, and whenever a suite touches a real Craft install. Covers opt-in rollback, tests/Pest.php + tests/bootstrap.php wiring, phpunit.xml.dist <env> pins (DB name, table prefix, connection, CRAFT_ENVIRONMENT against server-scoped locks), why --configuration= defeats isolation, fail-closed DB guards, installing the plugin under test, timezone pinning, per-test site fixtures, idempotent Install migrations, stale service caches, audit sinks, queue stubs, factories, HTTP/DB assertions, CI jobs."
when_to_use: "Triggers on: Pest, pestphp, craft-pest-core, RefreshesDatabase, InstallsCraft, vendor/bin/pest, composer test, ddev craft pest, db_test, CRAFT_DB_DATABASE, BusyResourceException, GET_LOCK, Entry::factory(), assertDatabaseHas, createIndexIfMissing, UserPermissions::reset(), TestCaseAlreadyInUse, cookieValidationKey with --filter, 'too many keys', 'tests pollute the database', 'passes alone but fails in the suite', 'two suites deadlock', 'datetimes off by hours in tests', flaky order-dependent test, no CI Pest job. Do NOT trigger for front-end/JS testing or PHP style analysis."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Testing Craft CMS Plugins with Pest

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Reference for testing Craft CMS 5 plugins and modules with Pest, primarily via `markhuot/craft-pest-core`.

The dominant failure mode in Craft plugin testing is not a wrong assertion — it's a suite that **writes to a database it shouldn't**, or that **passes only because of ambient state** on the developer's install. Both are silent. Both look like a green suite. This skill leads with isolation for that reason: get the harness right first, then write tests.

**Verified against `markhuot/craft-pest-core` 3.2.2 and `craftcms/cms` 5.10.12 (August 2026).** Where a claim names a class or method, it was read in that package's source. craft-pest's own README and docs are not authoritative on these points — several of the behaviors below are unstated there.

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
| Fail-closed DB guard that **throws** (never `exit(1)`) | `tests/bootstrap.php` | `exit(1)` hands the shell 0 under Pest — guard fails open on CI |
| `CRAFT_ENVIRONMENT` pinned uniquely per plugin | `phpunit.xml.dist` | Suites share server-scoped `GET_LOCK` names — `BusyResourceException`/deadlocks even across separate databases |
| `date_default_timezone_set('UTC')` **after** app creation | `tests/bootstrap.php` | Datetimes shift by the install's UTC offset |
| Same pins present as `<env>` entries | `phpunit.xml.dist` | Correct-invocation path has no pins |
| DB name + table prefix forced; coordinates `default="true"` | `phpunit.xml.dist` | A forced local hostname breaks CI runners |
| `Install::safeUp()` guarded with `createIndexIfMissing()` / `Db::findForeignKey()` | `src/migrations/Install.php` | Duplicate keys accumulate to MySQL's 64-per-table cap |
| Sites created per-test and deleted in `afterEach()` | tests, `tests/Pest.php` | Durable sites mutate the shared test database |
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
- "Expiry/date assertions fail intermittently, or datetimes come back hours off" → `isolation.md` (Pin the process timezone)
- "Suite connects fine locally but can't reach the database on CI" → `isolation.md` (Force the database name, default everything else) + `ci.md`
- "Install fails with too many keys / duplicate indexes piling up" → `shared-state.md` (Install migrations must be idempotent)
- "Set up a multi-site test / my test site's queries ignore siteId" → `craft-state.md` (Site fixtures) + the `craftcms` skill's `architecture.md`
- "My fixture-cleanup sweep isn't deleting anything / fixtures leak into a shared install" → `craft-state.md` (Prefix-matching sweeps)
- "Test passes alone but fails in the suite / service returns stale data" → `craft-state.md` (Service caches go stale when craft-pest swaps components)
- "Wire tests into CI" → `ci.md`
- "Make the bootstrap refuse to run against the wrong database" → `isolation.md` (fail-closed guard — throw, never `exit(1)`)
- "Two suites deadlock when run in parallel / `BusyResourceException` on a fresh empty database" → `isolation.md` (pin `CRAFT_ENVIRONMENT`)
- "Does this suite even run in CI?" → `ci.md` (sweep all workflows, not just `tests.yaml`)
- "`--filter` run fails on cookieValidationKey but the full suite passes" → `isolation.md` (--filter subsets)
- "Refactor a large untested controller/service" → `patterns.md` (Pin behaviour before refactoring)
- "The fix requires changing an existing test / is my new test actually testing anything?" → `patterns.md` (A test can encode the bug; Prove a fix by breaking it)
- "`TestCaseAlreadyInUse` from my uses() rules / per-directory TestCases" → `patterns.md` (uses() rules)
- "CP controller test fails on sites, URLs, or asset directories" → `craft-state.md` (CP-surface controller tests)

| Reference | Scope |
|-----------|-------|
| `references/isolation.md` | Database isolation: `tests/bootstrap.php`, process timezone, `phpunit.xml.dist` (force the DB name, default the connection coordinates), `RefreshesDatabase`, `InstallsCraft` boot vs plugin install, invocation paths, ambient-state assumptions (editions, counts, pre-existing fixtures) |
| `references/craft-state.md` | Craft internals that bite in tests: permission-tree memoization, login/session gates, UTC fixture timestamps, muting audit/event surfaces, per-test site fixtures, component swapping and stale service caches, queue stubs, project-config writes |
| `references/patterns.md` | Writing the tests: Pest vs Codeception, pure unit tests, what a green suite does not prove, factories, HTTP, queue, database assertions, multi-site, mocking Craft services, console commands, events, file/test conventions |
| `references/shared-state.md` | Suites that run against a shared or long-lived install: restore-what-you-found, `Install.php` vs migration drift in the test DB, idempotent `Install` migrations, self-seeding, request-IP fixtures |
| `references/ci.md` | CI wiring: `check-cs` not `fix-cs`, a real Pest job, invocation from the plugin root, fresh-database verification |

## Further Pitfalls (detail in `patterns.md`)

- **Codeception vs Pest**: use Pest + craft-pest-core for new plugin work, Codeception only for Craft core or an existing Codeception suite; pure-logic tests extend `PHPUnit\Framework\TestCase` without booting Craft. See `patterns.md` (Two harnesses; Pure unit tests).
- **A green suite is not proof**: service-layer tests never see the HTTP layer, a seeded dev install is not authoritative, a console harness is not a browser, one long-lived process is not a sequence of requests, and a suite not in CI rots. See `patterns.md` (What a green suite does not prove).
