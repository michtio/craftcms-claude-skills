# Writing the Tests

Factories, HTTP, queue, database assertions, multi-site, mocking, console commands, and events. Assumes the harness is already isolated — if you haven't read `isolation.md`, read it first; a correct assertion against the wrong database is still a bug.

## Contents

- Common pitfalls
- Setup and file conventions
- Pin behaviour before refactoring
- Pure unit tests (no Craft boot)
- Element factories
- HTTP testing
- Queue testing
- Database assertions
- Multi-site testing
- Mocking Craft services
- Console command testing
- Event testing

## Common Pitfalls

- Extending `craft\test\TestCase` for pure unit tests — extend `PHPUnit\Framework\TestCase` directly when you don't need Craft booted.
- Forgetting `site('*')` in test queries — tests run in primary-site context, so elements on other sites are invisible.
- Testing against element IDs that differ across environments — use handles, UIDs, or factory-created elements.
- Missing `autoload-dev` in `composer.json` for the test namespace — Pest can't find test helpers.
- Not refreshing sites after fixture changes — call `Craft::$app->getSites()->refreshSites()` or cached data goes stale.
- Using `craft\test\TestSetup` helpers in a Pest-only setup — `TestSetup::configureCraft()` transitively autoloads `craft\test\Craft`, which extends `Codeception\Module\Yii2`. Without Codeception installed that's a fatal class-not-found. Inline the bootstrap logic instead.
- `Class "Craft" not found` in unit tests — `\Craft` and `\Yii` are global classes outside PSR-4. See "Pure unit tests" below.
- Grepping rendered HTML/JS for a translated multi-word string — Twig's `|e('js')` escaper converts every non-alphanumeric ASCII char *including the space* to a `\uXXXX` sequence, so a multi-word phrase never appears verbatim. Assert on a single token or a raw JS identifier. (The escaping detail lives in the `craft-twig-guidelines` skill.)
- Test names that don't describe behavior — `it('works')` tells nobody anything when it fails at 2am.

## Setup and file conventions

```bash
ddev composer require --dev markhuot/craft-pest-core:^3.0
```

```json
{
    "autoload-dev": {
        "psr-4": { "acme\\myplugin\\tests\\": "tests/" }
    },
    "scripts": {
        "test": "pest"
    }
}
```

Conventions that pay off:

- Mirror source paths: `src/services/Items.php` → `tests/Unit/Services/ItemsTest.php`.
- Descriptive `it()` names: `it('prevents duplicate bulk operations')`.
- `describe()` blocks group by feature; section headers between blocks in longer files.
- One behavior per test where practical.

```php
// =========================================================================
// Item creation
// =========================================================================

describe('item creation', function () {
    it('assigns a UUID on save', function () { /* ... */ });
    it('rejects duplicate handles', function () { /* ... */ });
});
```

### `uses()` rules: first match wins, most-specific first

Pest walks the registered `uses()` rules in **registration order**, and the *first* rule whose path matches a test file sets that file's TestCase — a second matching rule throws `TestCaseAlreadyInUse`. So a blanket rule followed by an override never works:

```php
// FAILS — the blanket rule matches Integration/Migrations/* first,
// then the "override" throws TestCaseAlreadyInUse.
uses(BaseTestCase::class)->in('Integration');
uses(MigrationTestCase::class)->in('Integration/Migrations');
```

Register the most-specific paths first, then enumerate the remaining sub-directories explicitly — no catch-all:

```php
uses(MigrationTestCase::class)->in('Integration/Migrations');
uses(MultiSiteTestCase::class)->in('Integration/MultiSite');
uses(BaseTestCase::class)->in(
    'Integration/Services',
    'Integration/Validators',
    'Integration/Models',
);
```

The enumeration is the price of per-directory TestCases; a new sub-directory that isn't listed simply gets no TestCase, which fails loudly enough to notice.

## Pin behaviour before refactoring

Before restructuring code that has no tests, write tests **against the unrefactored code first** and make them pass — then refactor against a green wall. This is where load-bearing accidents surface: behaviours nobody documented but callers (or authors' own templates) depend on. One 1,900-line controller refactor added 76 pin tests first, and they caught three real subtleties a "clean" rewrite would have broken:

- A search haystack built by concatenating values (`$key . ' ' . $key2`) — a needle can span two columns, which is **not** equivalent to a per-column `OR LIKE`. The naive "improvement" changes match results.
- `filters[x] = ''` meaning "no filter", not "match rows where x is empty" — an empty-string filter dropped during refactoring silently changes result sets.
- Null branches reachable only via soft-deleted users and `SET NULL` foreign keys — dead-looking code that a data-state most dev installs don't have makes live.

Pin tests assert what the code *does*, not what it should do — write them mechanically from observed behaviour, resist fixing oddities mid-pin (note them, pin them, fix after the refactor with an intentional test change that documents the behaviour change).

## A test can encode the bug

The flip side of pinning: a passing test is evidence the behaviour is *stable*, not that it's *correct*. A real prune test asserted the exact row-deletion behaviour that was dropping live sessions' data — the test was green because it pinned the bug.

When a bug fix requires changing an existing test, that is not automatically a regression or a weakened suite — it can be the fix being pinned. But the two cases are indistinguishable in a diff, so **call it out explicitly in the PR/review**: name the test, state that its old assertion encoded the defect, and say what the new assertion pins instead. An unexplained assertion change in review correctly reads as a red flag; the explanation is what converts it into documentation.

## Prove a fix or guard is not vacuous by breaking it

A test that pins a subtle invariant — an ordering constraint, a fail-closed guard, a race fix — can pass for reasons unrelated to the thing it claims to protect. The standard is to watch it fail:

- **Revert the fix** (locally, uncommitted) and confirm the test goes red. If it stays green, the test isn't exercising the fixed path.
- **For ordering invariants**, swap the two calls and confirm the ordering test fails.
- **For fail-closed guards**, force the bad condition (e.g. point the DB pin at a bogus name — see `isolation.md`) and confirm the process exits non-zero, not just that a message prints.

Report that the step was done ("reverted the fix, test fails; restored, passes") — it's what makes the test trustworthy to the next reader, and it costs a minute.

## Pure unit tests (no Craft boot)

For testing pure logic, skip craft-pest — booting Craft is the expensive, stateful part.

```bash
ddev composer require --dev pestphp/pest:^3.0 --with-all-dependencies
```

Configure `phpunit.xml.dist` with `bootstrap="vendor/autoload.php"` and a `Unit` suite pointing at `tests/Unit`.

`\Craft` and `\Yii` sit outside their packages' PSR-4 maps — Craft's own bootstrap `require`s them explicitly. A unit test that doesn't boot the app must do the same:

```php
// tests/Pest.php
require_once dirname(__DIR__) . '/vendor/yiisoft/yii2/Yii.php';
require_once dirname(__DIR__) . '/vendor/craftcms/cms/src/Craft.php';
```

Without it, any path referencing `Craft::$app` — or a Yii built-in validator (`'in'`, `'integer'`, `'string'` all call `Yii::createObject()`) — fatals with `Class "Craft" not found`.

Once loaded, `Craft::$app` is `null` in that context. Code guarding on `Craft::$app instanceof \craft\web\Application` before logging or touching services correctly skips those paths. That's expected — don't strip the guards to "simplify."

## Element factories

```php
$entry = Entry::factory()->section('blog')->type('post')
    ->title('Test Post')->set('customField', 'value')->create();
$admin = User::factory()->admin()->create();
$editor = User::factory()->group('editors')->create();
$entries = Entry::factory()->section('blog')->count(5)->create();
```

Create `Field::factory()` instances **before** any element factory in the same test — MySQL implicitly commits on `ALTER TABLE`, and `RefreshesDatabase` can only manually roll back field models (see `isolation.md`).

Without craft-pest:

```php
$section = Craft::$app->getEntries()->getSectionByHandle('blog');
$entry = new Entry();
$entry->sectionId = $section->id;
$entry->typeId = $section->getEntryTypes()[0]->id;
$entry->title = 'Test Entry';
Craft::$app->getElements()->saveElement($entry);
```

For tests that don't touch the database, build fixtures as plain collections:

```php
final class TrackingDataFixtures
{
    public static function candidate(array $overrides = []): Collection
    {
        return collect(array_merge([
            'externalId' => 'candidate-001', 'status' => 'active', 'score' => 85,
        ], $overrides));
    }
}

it('filters low-scoring candidates', function () {
    $candidates = TrackingDataFixtures::candidateBatch(5);
    expect($service->filterByMinScore($candidates, 83))->toHaveCount(3);
});
```

## HTTP testing

HTTP tests are the only ones that exercise route resolution, CSRF, reserved query params, and response formats. Anything a controller does that a service can't — test it here.

```php
it('renders settings page for permission holders', function () {
    $this->actingAsAdmin()
        ->get('/admin/my-plugin/settings')
        ->assertOk()
        ->assertSee('Plugin Settings');
});

it('forbids users without the permission', function () {
    $this->actingAs(User::factory()->create())
        ->get('/admin/my-plugin/settings')
        ->assertForbidden();
});
```

POST actions — build the URL with `UrlHelper::actionUrl()`:

```php
it('saves a new item', function () {
    $this->actingAsAdmin()
        ->post(UrlHelper::actionUrl('my-plugin/items/save-item'), [
            'name' => 'Test Item',
            'handle' => 'testItem',
        ])
        ->assertRedirect();
});
```

JSON:

```php
it('returns items as JSON', function () {
    Entry::factory()->section('blog')->count(3)->create();

    $this->actingAsAdmin()
        ->get('/admin/my-plugin/api/items')
        ->assertOk()
        ->assertJsonCount(3, 'items');
});
```

A route test that returns 400 with "Invalid token" when you expected 200 is almost always a **reserved query param** — `token` collides with Craft's `tokenParam` and is rejected in `Application::init()` before your controller runs. See the `craftcms` skill's `controllers.md`.

## Queue testing

```php
it('pushes sync job', function () {
    MyPlugin::getInstance()->getSync()->queueSync(42);

    expect(Craft::$app->getQueue())->toHavePushed(SyncItems::class);
});

it('pushes job with correct properties', function () {
    MyPlugin::getInstance()->getSync()->queueSync(42);

    expect(Craft::$app->getQueue())
        ->toHavePushed(SyncItems::class, fn($job) => $job->categoryId === 42);
});
```

Running jobs:

```php
it('creates records when sync job runs', function () {
    MyPlugin::getInstance()->getSync()->queueSync($categoryId);
    Craft::$app->getQueue()->run();

    $this->assertDatabaseHas('{{%myplugin_items}}', ['categoryId' => $categoryId]);
});
```

`Craft::$app->getQueue()->run()` on a **real** queue drains whatever else is waiting. Only call it against a stub or a `sync` driver — see `craft-state.md` (Queue stubs).

## Database assertions

```php
it('persists item', function () {
    MyPlugin::getInstance()->getItems()->createItem(['handle' => 'widget']);
    $this->assertDatabaseHas(Table::ITEMS, ['handle' => 'widget']);
});

it('removes item on delete', function () {
    $item = MyPlugin::getInstance()->getItems()->createItem(['handle' => 'widget']);
    MyPlugin::getInstance()->getItems()->deleteItem($item);
    $this->assertDatabaseMissing(Table::ITEMS, ['handle' => 'widget']);
});
```

Standalone:

```php
$exists = (new Query())->from('{{%myplugin_items}}')
    ->where(['handle' => 'widget'])->exists();
expect($exists)->toBeTrue();
```

Always give count assertions a filtering condition that matches only test-created rows (`isolation.md` → Scope every count assertion).

## Multi-site testing

```php
// All sites
$entries = Entry::find()->site('*')->section('blog')->all();

// Specific site
$entry = Entry::find()->site('caEn')->slug('annual-report')->one();
expect($entry->site->handle)->toBe('caEn');
```

Always refresh after creating or modifying sites:

```php
Craft::$app->getSites()->saveSite($site);
Craft::$app->getSites()->refreshSites();
```

With craft-pest, sites already in project config are available automatically.

## Mocking Craft services

Inject collaborators where you can — a service that takes its API client as a constructor argument needs no Craft-level mocking:

```php
it('calls external API with correct params', function () {
    $client = $this->createMock(ApiClient::class);
    $client->expects($this->once())->method('fetchItems')
        ->with(42)->willReturn(['item-1', 'item-2']);

    $service = new SyncService($client);
    expect($service->syncCategory(42))->toHaveCount(2);
});
```

When the code reaches for a Craft component, swap the component:

```php
beforeEach(function () {
    Craft::$app->set('mailer', $this->createMock(\craft\mail\Mailer::class));
});

it('sends notification email', function () {
    Craft::$app->getMailer()->expects($this->once())->method('send');
    MyPlugin::getInstance()->getNotifications()->sendAlert($item);
});
```

Component swaps persist for the process, not the transaction — set them in `beforeEach()` so each test starts from a known component graph.

## Console command testing

```php
it('runs sync command successfully', function () {
    $this->consoleCommand('my-plugin/sync/items')
        ->exitCode(0)
        ->run();
});

it('outputs progress to stdout', function () {
    $this->consoleCommand('my-plugin/sync/items')
        ->stdout('Processing')
        ->exitCode(0)
        ->run();
});

it('accepts arguments and options', function () {
    $this->consoleCommand('my-plugin/sync/items', ['42', '--dry-run'])
        ->exitCode(0)
        ->run();
});
```

Console surfaces need their **own** authorization tests — a console controller is not covered by a web controller's permission test, and the two must share one gate. See the `craft-php-guidelines` skill's `authorization-parity.md`.

## Event testing

```php
it('fires event before sync', function () {
    $this->expectEvent(
        Items::class,
        Items::EVENT_BEFORE_SYNC,
        function () {
            MyPlugin::getInstance()->getSync()->syncCategory(42);
        },
        ItemSyncEvent::class,
    );
});
```

Capturing the payload:

```php
it('passes correct data in sync event', function () {
    $firedEvent = null;
    Event::on(Items::class, Items::EVENT_BEFORE_SYNC,
        function (ItemSyncEvent $event) use (&$firedEvent) { $firedEvent = $event; },
    );
    MyPlugin::getInstance()->getSync()->syncCategory(42);

    expect($firedEvent)->not->toBeNull()->categoryId->toBe(42);
});
```

Cancellation:

```php
it('skips sync when event is cancelled', function () {
    Event::on(Items::class, Items::EVENT_BEFORE_SYNC,
        function (ItemSyncEvent $event) { $event->isValid = false; },
    );
    expect(MyPlugin::getInstance()->getSync()->syncCategory(42))->toBeFalse();
    $this->assertDatabaseMissing('{{%myplugin_items}}', ['categoryId' => 42]);
});
```

**Contract-test both directions when two plugins share an event vocabulary.** If your plugin emits events an open vocabulary says are additive, test that a consumer accepts an unknown value; if it consumes, test that an unrecognized value isn't silently dropped. Silent drops in audit-class data are invisible to both suites otherwise — see the `craftcms` skill's `events.md`.
