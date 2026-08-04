# Craft Internals That Bite in Tests

Craft behaviors that are correct in production and surprising in a test process. Each entry names the mechanism, because the workaround only makes sense once you know why the naive approach fails. Verified against `craftcms/cms` 5.10.11 and `markhuot/craft-pest-core` 3.2.2.

## Contents

- Permission-tree memoization (`UserPermissions::reset()`)
- Simulating a login in a console-driven harness
- CP-surface controller tests: three orthogonal pins
- Fixture timestamps: MySQL session clock vs Craft's UTC
- Muting audit/event surfaces — all of them
- Site fixtures are per-test, never bootstrap-created
- Service caches go stale when craft-pest swaps components
- Queue stubs
- Project-config writes inside a rolled-back transaction

## Permission-tree memoization (`UserPermissions::reset()`)

`UserPermissions::getAllPermissions()` builds the whole permission tree once and memoizes it in a private `$_allPermissions` property for the life of the process. In a web request that's free; in a test process it means the tree is frozen at whatever the *first* call saw.

That matters because of what `saveGroupPermissions()` does with it:

```
saveGroupPermissions($groupId, $permissions)
  → _filterOrphanedPermissions($permissions)
      → foreach (getAllPermissions() as $group)      ← the memoized tree
          → _findSelectedPermissions(...)            ← keeps only handles found in it
```

Any handle **not present in the memoized tree is silently dropped** — no exception, no warning, no error on the returned `true`.

So a suite that creates a section (or volume, category group, or anything else whose permissions are generated per-entity) mid-run and then grants the resulting scoped permission will find the grant vanished, because the tree was memoized before the section existed. It's order-dependent: the test passes in isolation and fails when a test that touches permissions runs first.

```php
// Create the entity whose permissions are dynamically generated…
$section = createTestSection();

// …then drop the memo so the new handles are visible to the filter.
Craft::$app->getUserPermissions()->reset();

Craft::$app->getUserPermissions()->saveGroupPermissions($group->id, [
    "viewentries:{$section->uid}",
]);
```

The same `reset()` is needed after your own plugin registers permissions derived from data created in the test.

Related, and a bug source in its own right: `_findSelectedPermissions()` only recurses into a nested permission when its **parent** is also selected, so nested handles submitted without their ancestors are dropped too. That's a production behavior, not a test artifact — see the `craftcms` skill's `permissions.md`.

## Simulating a login in a console-driven harness

A real `loginByUserId()` round-trip does not work under craft-pest. The chain:

```
User::loginByUserId($id) → login($user) → beforeLogin()
  → _validateUserAgentAndIp()
      → returns true only if requireUserAgentAndIpForSession is false,
        or both getUserAgent() and getUserIP() are non-null
```

craft-pest boots a `craft\web\Application` under the CLI SAPI, so there is no user agent and no client IP, `requireUserAgentAndIpForSession` defaults to `true`, and `beforeLogin()` returns `false` with a `Craft::warning()`. Yii's `login()` then returns `!getIsGuest()` — still `false` for a guest — so the login simply doesn't happen.

Two workable approaches:

**For HTTP-shaped tests, use craft-pest's own acting-as helpers.** `$this->actingAsAdmin()` / `$this->actingAs($user)` set up the identity for the request builders without going through the UA/IP gate. This is the right tool for testing controllers, permissions on routes, and response codes:

```php
it('forbids non-permission-holders', function () {
    $this->actingAs(User::factory()->create())
        ->get('/admin/my-plugin/settings')
        ->assertForbidden();
});
```

**For service-layer tests that must observe login side effects,** stage the state and trigger the event directly rather than fighting the gate:

```php
use craft\elements\User as UserElement;
use craft\web\User as UserSession;
use yii\web\UserEvent;

// Stage: the plugin's listener expects an identity to be resolvable.
$user = UserElement::factory()->create();

// Trigger the seam the plugin actually listens on.
Craft::$app->getUser()->trigger(UserSession::EVENT_AFTER_LOGIN, new UserEvent([
    'identity' => $user,
]));

expect($service->getLoginRecordFor($user->id))->not->toBeNull();
```

Then verify the *wiring* (that the listener is registered at all) with an HTTP test or code review — an event-trigger test proves the handler works, not that it's attached.

Setting `requireUserAgentAndIpForSession => false` in the test config is a third option, but it changes the behavior under test and only helps if nothing else in the chain needs a real request. Prefer the two above.

## CP-surface controller tests: three orthogonal pins

Service-layer tests pass; then the first test that exercises a **CP controller action** fails with a cryptic error about sites, URLs, or asset directories. Under a console-bootstrap harness (custom Pest setups especially), three independent defaults are wrong for the CP surface, and any controller that (a) requires an elevated session, (b) calls `Cp::*` / `UrlHelper` CP URL helpers, or (c) triggers `View::registerJs()` (which auto-registers `JqueryAsset` at `POS_READY`) needs all three pinned:

1. **User component `idParam`** — `Sites::getCurrentSite()` reads `User->idParam` directly, even on `craft\console\User`. Without a value the site lookup fails. In a User stub: expose a pinned `idParam` (e.g. `'__'`).
2. **Request: CP flag + host info** — `UrlHelper::actionUrl()` / `Cp::cpUrl()` need `getIsCpRequest()` to answer *and* `getHostInfo()` to resolve. In a Request stub's `init()`: `$this->setHostInfo('https://test.test')`, wire up `generalConfig`, and expose a `getIsCpRequest()` override that **defaults to false** so front-end controller tests keep working, flipped per-test for CP ones.
3. **`assetManager.basePath`** — registering JS at `POS_READY` publishes `JqueryAsset` to disk; without a writable base path it dies with "directory does not exist". In the test app config: `'assetManager' => ['basePath' => __DIR__ . '/../storage/runtime/assets']`, and create the directory.

Each pin is one line; the cost is the chase. Keep the pins in the shared test-infrastructure files (`tests/Support/*Stub.php`, the test app config) — never in individual test files. (Under craft-pest-core the request builders handle much of this; the pins matter when you've built your own bootstrap or stubs.)

## Fixture timestamps: MySQL session clock vs Craft's UTC

Craft stores and compares datetimes in **UTC**. A MySQL connection's `NOW()` returns the *session* time zone's clock, which on a developer machine or a container configured for a local zone can be hours ahead.

So a fixture row inserted with raw SQL intended to be "already expired":

```sql
-- WRONG: under a UTC+2 session clock this is 2 hours in Craft's future
INSERT INTO {{%myplugin_tokens}} (token, dateExpired) VALUES ('abc', NOW());
```

…is not expired as far as Craft's UTC comparison is concerned, and the test that asserts "expired tokens are rejected" fails, or worse, the test asserting the opposite passes for the wrong reason.

Use `UTC_TIMESTAMP()` in raw fixture SQL:

```sql
INSERT INTO {{%myplugin_tokens}} (token, dateExpired)
VALUES ('abc', DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 HOUR));
```

Better still, build fixtures through Craft so the conversion is Craft's problem — `Db::insert()` with a `DateTimeHelper`-produced value, or `Db::prepareDateForDb()`. Reach for raw SQL only when you're deliberately bypassing the model layer, and then remember the clock.

## Muting audit/event surfaces — all of them

A plugin that emits audit or activity events often has **more than one** surface doing it, and they're structurally independent:

- its own sink registry (`Audit::setSinks([])`-style), and
- a lifecycle event (`EVENT_AFTER_RECORD` or similar) that a *separate* bridge plugin listens on and forwards to a bus, which fans out to its own consumers.

Muting only the documented sink array leaves the bridge → bus → consumer path live, so tests write real audit rows into a real table — usually noticed weeks later as unexplained volume, not as a test failure.

Mute **every** surface, from one shared helper, so no call site can get it half-right:

```php
// tests/Pest.php

/**
 * Silences every audit surface: the plugin's own sink registry and any
 * bridge/bus path an optional integration may have attached.
 *
 * Guarded by class_exists() so the suite still runs when the optional
 * integration isn't installed.
 */
function muteAuditSurfaces(): void
{
    // 1. The plugin's own sink registry.
    \acme\auditkit\services\Audit::setSinks([]);

    // 2. The bus a bridge plugin forwards into — optional dependency.
    if (class_exists(\acme\auditbus\AuditBus::class)) {
        \acme\auditbus\AuditBus::getInstance()->getBus()->setSinks([]);
    }
}
```

Call it from a single `beforeEach()` in `tests/Pest.php` rather than per-file — a suite where 9 of 10 files remember is a suite that writes audit rows.

If you own the emitting plugin, this is also a documentation obligation: a second event surface that isn't in the README's events section produces consumer bugs. See the `craftcms` skill's `events.md` (Cross-plugin event contracts).

## Site fixtures are per-test, never bootstrap-created

It is tempting to create the extra sites a multi-site suite needs once, at bootstrap, and reuse them. Don't: a site created at bootstrap is **durable**. It's project-config-backed, so it survives the per-test transaction rollback and permanently mutates the test database. Two consequences follow, and the second is the one that bites:

- The suite stops being reproducible. Run 1 creates the site; runs 2..n silently exercise a *different* schema than a fresh checkout does.
- CI, which starts from an empty database every time, is the only place that ever runs the real fresh-DB path — so the suite goes green locally for weeks and fails the moment CI's ordering differs.

Create sites inside the test that needs them, and delete them explicitly in a global `afterEach()`:

```php
// tests/Pest.php
afterEach(function () {
    $sites = Craft::$app->getSites();

    foreach ($sites->getAllSites(true) as $site) {
        if (!str_starts_with($site->handle, 'test')) {
            continue;
        }

        $sites->deleteSite($site);
    }

    // Core leaves these stale — see the craftcms skill's architecture.md.
    $sites->refreshSites();
    Craft::$app->getIsMultiSite(true, true);
});
```

**Prefix-matching sweeps: use the raw condition form, and assert the sweep matches.** The cleanup above filters in PHP (`str_starts_with`), which is safe. The moment you push the prefix match into an *element query*, there's a trap that makes cleanup silently stop working:

```php
// WRONG — matches nothing, permanently, with no error.
// Param setters take values, not conditions: QueryParam::parse() only knows
// and/or/not, so this compiles to `title IN ('like', 'test-%')`.
$stale = Entry::find()->title(['like', 'test-%'])->all();

// Right — raw Yii condition against the real column. Trailing `false` keeps
// your own % intact instead of letting Yii escape and re-wrap it.
$stale = Entry::find()
    ->andWhere(['like', 'elements_sites.title', 'test-%', false])
    ->all();
```

The mechanism is in the `craftcms` skill's `architecture.md` (Element-query param setters don't take Yii operator tuples). What matters here is the failure shape: a broken sweep returns an empty array, deletes nothing, throws nothing, and leaves the suite green — so fixtures accumulate in a shared install indefinitely and the first symptom is unrelated tests failing weeks later on data nobody remembers creating.

Because a no-op sweep is indistinguishable from a clean one, **assert at least once that the sweep finds what it should**:

```php
it('cleans up its own fixtures', function () {
    Entry::factory()->section('blog')->title('test-alpha')->create();

    $matched = Entry::find()
        ->andWhere(['like', 'elements_sites.title', 'test-%', false])
        ->all();

    // Guards the query itself, not just the deletion.
    expect($matched)->not->toBeEmpty();
});
```

One test like this per sweep pattern is enough — it converts a silent no-op into a red build.

**Why explicit deletion rather than trusting the rollback.** Pest's `afterEach` runs *before* the `RefreshesDatabase` rollback, so you get a clean window to undo project-config-backed state while the transaction is still open. The ordering is in `Pest\Concerns\Testable::tearDown()` (verified against `pestphp/pest` 2.36.1):

```php
protected function tearDown(): void
{
    $afterEach = TestSuite::getInstance()->afterEach->get(self::$__filename);
    // ...
    try {
        $this->__callClosure($afterEach, func_get_args());
    } finally {
        parent::tearDown();          // ← craft-pest's TestCase::tearDown() → rollback
        // ...
    }
}
```

`parent::tearDown()` is craft-pest's `TestCase::tearDown()`, which calls `callTraits('tearDown')` and therefore `tearDownRefreshesDatabase()`. So: your `afterEach` first, rollback second. Relying on the rollback alone is what leaves sites behind — project-config writes don't cleanly reverse with it (see `isolation.md`, "What it does not cleanly cover").

**Two core caches must be refreshed when sites change mid-process**, and they're the reason a site fixture appears to half-work: `Sites::refreshSites()` does *not* invalidate the `getIsMultiSite()` variant that `ElementQuery` reads, and `deleteSite()`'s project-config prune is invisible to the `Entries`/`Categories` services' memoized models. Both are Craft-core behaviors, documented with the mechanism in the **`craftcms`** skill's `architecture.md` → "Creating or deleting sites at runtime". Skipping the `getIsMultiSite(true, true)` call is why a freshly-created test site produces element queries that don't filter by site.

## Service caches go stale when craft-pest swaps components

craft-pest's fake requests replace application components mid-suite. `RequestHandler::registerWithCraft()` does:

```php
$this->app->set('request', $request);
$this->app->set('response', $response);

$this->app->setComponents([
    'request' => $request,
    'response' => $response,
    // "We'll help out by resetting a few components (causing them to
    //  recalculate their internal state)." — craft-pest's own comment
    'urlManager' => [
        'class' => UrlManager::class,
        'enablePrettyUrl' => true,
        'ruleConfig' => ['class' => UrlRule::class],
    ],
]);
```

Passing a **config array** to `setComponents()` registers a definition rather than an instance, so the next `get()` builds a **brand-new object**. That's deliberate and usually what you want. The hazard is what stays behind on the old one.

Class-level handlers (`Event::on(SomeService::class, ...)`) keep working — they're keyed on the class. But an **instance-level** listener — `Craft::$app->getSomeService()->on(...)`, or anything a plugin attached to a resolved component in `init()` — remains bound to the *original* instance and never fires for the replacement. Meanwhile the replacement's memoized caches start from scratch, or are populated fresh from state a fixture already mutated. Nothing errors; results just depend on whether a fake request happened to run earlier in the file. That's an order-dependent cross-test leak, and it reproduces only in the ordering that created it.

Craft core acknowledges this hazard directly. Its project-config listeners are registered through a `_proxy()` indirection specifically so that "the correct component is called if it happens to get swapped out (**e.g. for a test**)" — the comment is in `ApplicationTrait`.

**The pattern: give any service with process-lifetime memoization an explicit `reset()`,** mirroring core's `UserPermissions::reset()`, and call it from the fixture that mutated the underlying state rather than trusting a listener to fire:

```php
namespace acme\myplugin\services;

class Rules extends Component
{
    private ?MemoizableArray $_rules = null;

    /**
     * Clears the memoized rule set.
     *
     * Mirrors craft\services\UserPermissions::reset(). Call this from any code
     * that mutates the underlying rows in the same process — including test
     * fixtures. Do not rely on an event listener: craft-pest's fake requests
     * can replace component instances, leaving instance-level listeners bound
     * to an object nothing reads any more.
     *
     * @return void
     */
    public function reset(): void
    {
        $this->_rules = null;
    }
}
```

```php
// In the fixture, right after mutating state:
seedRuleRows($rows);
MyPlugin::getInstance()->getRules()->reset();     // direct, not via a listener
```

Two habits that keep this from recurring: register plugin event handlers at **class level** (`Event::on(Rules::class, ...)`) rather than on a resolved instance, and treat "works alone, fails in the suite" as a cache-invalidation question before a logic one.

## Queue stubs

Never let tests touch Craft's real queue. On a shared install it can carry a large backlog, and a test that runs the queue either **drains** jobs that belong to someone else or **grows** it with jobs nobody will run.

`yii\queue\Queue` is abstract, so "a bare Queue" means a test double, not `new Queue()`. Replace the component:

```php
beforeEach(function () {
    // A minimal double: records pushes, executes nothing, touches no storage.
    Craft::$app->set('queue', new class extends \yii\queue\Queue {
        public array $pushed = [];

        protected function pushMessage($payload, $ttr, $delay, $priority): string
        {
            $this->pushed[] = $payload;

            return (string) count($this->pushed);
        }

        public function status($id): int
        {
            return self::STATUS_WAITING;
        }
    });
});
```

Assert on `$queue->pushed`, or use craft-pest's `assertJob()` (its `Queues` trait listens on `Queue::EVENT_BEFORE_EXEC`, and its `assertPostConditions()` runs the queue **only** when the component is a `yii\queue\sync\Queue` — so pin `QUEUE_DRIVER=sync` in `phpunit.xml.dist` if you want that behavior, and never point it at the real db queue).

## Project-config writes inside a rolled-back transaction

`Craft::$app->getProjectConfig()->set(...)` bumps the in-memory memoized `configVersion`; `RefreshesDatabase`'s rollback discards the stored row that would have matched it. The memo and the persisted state desync, and every *later* project-config write in the run throws `craft\errors\BusyResourceException` or `craft\errors\StaleResourceException` (`ProjectConfig::_acquireLock()` throws the first when the `project-config` mutex can't be acquired). The failures surface in unrelated tests downstream.

Guard writes so they only fire when the value actually changes, and centralize the guard:

```php
// tests/Pest.php
function setProjectConfigValue(string $path, mixed $value): void
{
    $projectConfig = Craft::$app->getProjectConfig();

    // Only-when-different: skip the write and the configVersion bump.
    if ($projectConfig->get($path) === $value) {
        return;
    }

    $projectConfig->set($path, $value);
}
```

Do plugin installs and other unavoidable project-config work at **bootstrap**, outside the per-test transaction. And if a test must change a project-config value, restore what it found rather than a hardcoded default — see `shared-state.md`.
