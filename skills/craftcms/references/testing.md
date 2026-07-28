# Testing — Pointer

**Pest and `markhuot/craft-pest-core` testing lives in the dedicated `craft-pest` skill.** Load it for anything test-related: harness setup, database isolation, factories, HTTP/queue/DB assertions, mocking, console and event tests, shared-install hygiene, and CI test jobs.

That skill is the single source of truth so the same facts don't drift across two files. Its entry points:

| Task | `craft-pest` reference |
|------|------------------------|
| Set up Pest for a plugin; stop tests writing to the dev database | `references/isolation.md` |
| Permission memoization, login simulation, UTC fixtures, muting event sinks, queue stubs | `references/craft-state.md` |
| Factories, HTTP, queue, DB assertions, multi-site, mocking, console, events | `references/patterns.md` |
| Shared playground installs, `Install.php` vs migration drift, self-seeding | `references/shared-state.md` |
| CI test job wiring (`check-cs` not `fix-cs`, running from the plugin root) | `references/ci.md` |

Two things from that skill are worth knowing before you write any test, because they cause data loss rather than test failures:

1. **craft-pest-core's rollback is opt-in.** `TestCase` boots Craft but does not open a transaction — only the separate `RefreshesDatabase` trait does. Bind both in `tests/Pest.php`.
2. **Its env-override mechanism is cwd-bound.** `InstallsCraft::loadPhpunitXmlEnvironmentVariables()` reads only `getcwd().'/phpunit.xml(.dist)'` and ignores `--configuration=`, so running a plugin suite from a shared project root silently discards the plugin's own database pins and runs against the live database.

## Codeception (Craft's native harness)

Craft core itself is tested with Codeception, and it remains the right choice when you're contributing to core or extending an existing Codeception suite. Otherwise prefer Pest.

- Docs: https://craftcms.com/docs/5.x/extend/testing.html
- Base class: `craft\test\TestCase`
- Run: `ddev craft test/test`

```php
// Fixtures — always merge the parent's, or you silently drop them
public function _fixtures(): array
{
    return array_merge(parent::_fixtures(), [
        'sites' => ['class' => SitesFixture::class],
    ]);
}
```

```php
// Queue assertion
$this->tester->assertPushedToQueue('Syncing items for category 42');

// Mocking Craft components
$this->tester->mockCraftMethods('request', [
    'getPathInfo' => 'api/v1/items',
    'getIsActionRequest' => false,
]);
```

`consoleCommand()` works the same as in craft-pest.

**Don't mix the two harnesses.** `craft\test\TestSetup::configureCraft()` transitively autoloads `craft\test\Craft`, which extends `Codeception\Module\Yii2` — calling it from a Pest-only project is a fatal class-not-found error.
