# Testing Craft CMS Plugins

## Contents

- Common Pitfalls
- Two Testing Approaches
- Pest Setup (Recommended for Plugins)
- Element Factories
- HTTP Testing
- Queue Testing
- Database Assertions
- Multi-Site Testing
- Mocking Craft Services
- Console Command Testing
- Event Testing

## Documentation

- Craft Pest: https://craft-pest.com
- Pest PHP: https://pestphp.com/docs/installation
- Codeception: https://craftcms.com/docs/5.x/extend/testing.html

## Common Pitfalls

- Extending `craft\test\TestCase` for pure unit tests -- extend `PHPUnit\Framework\TestCase` directly when you don't need the Craft app booted.
- Forgetting `site('*')` in test queries -- elements on non-primary sites are invisible. Tests run in primary site context by default.
- Not calling `parent::_fixtures()` when extending test classes -- silently drops the parent's fixtures.
- Testing against element IDs that differ across environments -- use handles, UIDs, or factory-created elements.
- Missing `autoload-dev` in `composer.json` for the test namespace -- Pest/PHPUnit can't find test helpers.
- Running Pest on the host instead of through DDEV -- use `ddev craft pest/test` or `ddev exec "cd /var/www/html && vendor/bin/pest"`.
- Not refreshing sites after fixture changes -- call `Craft::$app->getSites()->refreshSites()` or cached data goes stale.

## Two Testing Approaches

| Aspect | Codeception (Native) | Pest (Community) |
|--------|---------------------|------------------|
| Base class | `craft\test\TestCase` | `PHPUnit\Framework\TestCase` or craft-pest |
| Run command | `ddev craft test/test` | `ddev craft pest/test` |
| Element factories | Fixture classes + data files | `Entry::factory()->create()` |
| HTTP testing | `FunctionalTester` (`$I`) | `->get('/path')->assertOk()` |
| Queue assertions | `$this->tester->assertPushedToQueue()` | `expect(queue)->toHavePushed(Job::class)` |

Use Pest for new plugin projects. Use Codeception when contributing to Craft core or extending an existing Codeception suite.

## Pest Setup (Recommended for Plugins)

### With markhuot/craft-pest

```bash
ddev composer require --dev markhuot/craft-pest:^3.0
```

Create `tests/Pest.php` with shared helpers. craft-pest handles Craft bootstrap automatically:

```php
function createAdmin(): \craft\elements\User
{
    return \craft\elements\User::factory()->admin()->create();
}
```

Run: `ddev craft pest/test` or `ddev craft pest/test --filter="settings"`

### Standalone Pest (without craft-pest)

For pure unit tests that don't need Craft booted:

```bash
ddev composer require --dev pestphp/pest:^3.0 --with-all-dependencies
ddev exec "cd /var/www/html && vendor/bin/pest --init"
```

Add `autoload-dev` to `composer.json`:

```json
{
    "autoload-dev": {
        "psr-4": { "mynamespace\\myplugin\\tests\\": "tests/" }
    }
}
```

Configure `phpunit.xml.dist` with `bootstrap="vendor/autoload.php"`, a `Unit` test suite pointing at `tests/Unit`, and a source include for `src`.

### Test File Conventions

- Mirror source paths: `src/services/Items.php` -> `tests/Unit/Services/ItemsTest.php`.
- Descriptive `it()` names: `it('prevents duplicate bulk operations')`, not `it('works')`.
- `describe()` blocks group by feature. Section headers between blocks in longer files.
- One assertion per test where practical.

```php
// =========================================================================
// Item creation
// =========================================================================

describe('item creation', function () {
    it('assigns a UUID on save', function () { /* ... */ });
    it('rejects duplicate handles', function () { /* ... */ });
});
```

## Element Factories

### craft-pest Factories

```php
$entry = Entry::factory()->section('blog')->type('post')
    ->title('Test Post')->set('customField', 'value')->create();
$admin = User::factory()->admin()->create();
$editor = User::factory()->group('editors')->create();
$entries = Entry::factory()->section('blog')->count(5)->create();
```

### Manual Element Creation (without craft-pest)

```php
$section = Craft::$app->getEntries()->getSectionByHandle('blog');
$entry = new Entry();
$entry->sectionId = $section->id;
$entry->typeId = $section->getEntryTypes()[0]->id;
$entry->title = 'Test Entry';
Craft::$app->getElements()->saveElement($entry);
```

### Static Fixture Builders (for pure unit tests)

Build fixture data as Collections for tests that don't touch the database:

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

## HTTP Testing

### GET Requests

```php
it('renders settings page for admins', function () {
    $this->actingAsAdmin()
        ->get('/admin/my-plugin/settings')
        ->assertOk()
        ->assertSee('Plugin Settings');
});

it('forbids non-admin access', function () {
    $this->actingAs(User::factory()->create())
        ->get('/admin/my-plugin/settings')
        ->assertForbidden();
});
```

### POST Actions

Use `UrlHelper::actionUrl()` to build action URLs:

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

### JSON Responses

```php
it('returns items as JSON', function () {
    Entry::factory()->section('blog')->count(3)->create();

    $this->actingAsAdmin()
        ->get('/admin/my-plugin/api/items')
        ->assertOk()
        ->assertJsonCount(3, 'items');
});
```

## Queue Testing

### With craft-pest

```php
it('pushes sync job', function () {
    MyPlugin::$plugin->getSync()->queueSync(42);

    expect(Craft::$app->getQueue())
        ->toHavePushed(SyncItems::class);
});

it('pushes job with correct properties', function () {
    MyPlugin::$plugin->getSync()->queueSync(42);

    expect(Craft::$app->getQueue())
        ->toHavePushed(SyncItems::class, fn($job) => $job->categoryId === 42);
});
```

### With Codeception

```php
$this->tester->assertPushedToQueue('Syncing items for category 42');
```

### Running Queue Jobs in Tests

```php
it('creates records when sync job runs', function () {
    MyPlugin::$plugin->getSync()->queueSync($categoryId);
    Craft::$app->getQueue()->run();

    $this->assertDatabaseHas('{{%myplugin_items}}', ['categoryId' => $categoryId]);
});
```

## Database Assertions

### With craft-pest

```php
it('persists item', function () {
    MyPlugin::$plugin->getItems()->createItem(['handle' => 'widget']);
    $this->assertDatabaseHas(Table::ITEMS, ['handle' => 'widget']);
});

it('removes item on delete', function () {
    $item = MyPlugin::$plugin->getItems()->createItem(['handle' => 'widget']);
    MyPlugin::$plugin->getItems()->deleteItem($item);
    $this->assertDatabaseMissing(Table::ITEMS, ['handle' => 'widget']);
});
```

### Direct Query Check (standalone)

```php
$exists = (new Query())->from('{{%myplugin_items}}')
    ->where(['handle' => 'widget'])->exists();
expect($exists)->toBeTrue();
```

## Multi-Site Testing

### Site Fixtures (Codeception)

```php
public function _fixtures(): array
{
    return array_merge(parent::_fixtures(), [
        'sites' => ['class' => SitesFixture::class],
    ]);
}
```

With craft-pest, sites from project config are available automatically.

### Querying Specific Sites

```php
// All sites
$entries = Entry::find()->site('*')->section('blog')->all();

// Specific site
$entry = Entry::find()->site('french')->slug('mon-article')->one();
expect($entry->site->handle)->toBe('french');
```

### Refreshing Sites After Changes

Always call `refreshSites()` after creating/modifying sites in tests:

```php
Craft::$app->getSites()->saveSite($site);
Craft::$app->getSites()->refreshSites();
```

## Mocking Craft Services

### mockCraftMethods (Codeception)

```php
$this->tester->mockCraftMethods('request', [
    'getPathInfo' => 'api/v1/items',
    'getIsActionRequest' => false,
    'getIsCpRequest' => false,
]);
```

### PHPUnit Mocks (standalone Pest)

```php
it('calls external API with correct params', function () {
    $client = $this->createMock(ApiClient::class);
    $client->expects($this->once())->method('fetchItems')
        ->with(42)->willReturn(['item-1', 'item-2']);

    $service = new SyncService($client);
    expect($service->syncCategory(42))->toHaveCount(2);
});
```

### Swapping Craft Components

```php
beforeEach(function () {
    Craft::$app->set('mailer', $this->createMock(\craft\mail\Mailer::class));
});

it('sends notification email', function () {
    Craft::$app->getMailer()->expects($this->once())->method('send');
    MyPlugin::$plugin->getNotifications()->sendAlert($item);
});
```

## Console Command Testing

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

Codeception uses the same `consoleCommand()` API.

## Event Testing

### Verifying Events Fire

```php
it('fires event before sync', function () {
    $this->expectEvent(
        Items::class,
        Items::EVENT_BEFORE_SYNC,
        function () {
            MyPlugin::$plugin->getSync()->syncCategory(42);
        },
        ItemSyncEvent::class,
    );
});
```

### Capturing Event Data

```php
it('passes correct data in sync event', function () {
    $firedEvent = null;
    Event::on(Items::class, Items::EVENT_BEFORE_SYNC,
        function (ItemSyncEvent $event) use (&$firedEvent) { $firedEvent = $event; },
    );
    MyPlugin::$plugin->getSync()->syncCategory(42);

    expect($firedEvent)->not->toBeNull()->categoryId->toBe(42);
});
```

### Testing Event Cancellation

```php
it('skips sync when event is cancelled', function () {
    Event::on(Items::class, Items::EVENT_BEFORE_SYNC,
        function (ItemSyncEvent $event) { $event->isValid = false; },
    );
    expect(MyPlugin::$plugin->getSync()->syncCategory(42))->toBeFalse();
    $this->assertDatabaseMissing('{{%myplugin_items}}', ['categoryId' => 42]);
});
```
