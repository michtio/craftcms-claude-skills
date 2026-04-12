# Quality — PHPStan, Pest, Code Review

## Documentation

- Coding guidelines: https://craftcms.com/docs/5.x/extend/coding-guidelines.html
- Generator: https://craftcms.com/docs/5.x/extend/generator.html
- Craft Pest: https://craft-pest.com

## Common Pitfalls

- Adding new PHPStan errors to the baseline instead of fixing them — baseline is for legacy code only.
- Using `@phpstan-ignore-next-line` without a comment explaining why.
- Not running `ddev composer check-cs` AND `ddev composer phpstan` before every commit.
- Pest test names that don't describe the behavior — `it('works')` tells nothing.
- Missing factories for custom elements — makes test setup verbose and fragile.

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
    ignoreErrors:
        - '#PHPDoc tag @mixin contains invalid type#'
        - '#^Dead catch#'
```

Run: `ddev composer phpstan`

### Common Fix Patterns

**ActiveQuery returns `array`:**
```php
/** @var MyRecord[] $records */
$records = MyRecord::find()->where(['categoryId' => $id])->all();
```

**Element query returns `ElementQueryInterface`:**
```php
/** @var MyQuery $query */
$query = MyElement::find();
```

**Yii2 component access:**
```php
/** @var MyPlugin $plugin */
$plugin = MyPlugin::getInstance();
```

**`$sourceElements` type narrowing in eager loading:**
```php
/** @var MyElement[] $sourceElements */
foreach ($sourceElements as $element) {
    // PHPStan now knows custom properties
}
```

### Baseline Strategy

Generate baseline for legacy code, fix all new code clean:

```bash
ddev composer phpstan -- --generate-baseline
```

Review the baseline periodically and chip away at it. Never add new errors to the baseline.

### `@phpstan-ignore-next-line`

Use sparingly, always with explanation:

```php
/** @phpstan-ignore-next-line Craft's event system uses mixed types */
$event->types[] = MyElement::class;
```

## Pest Testing

Reference implementation: [Blitz plugin tests](https://github.com/putyourlightson/craft-blitz/tree/develop/tests).

```json
{
    "require-dev": {
        "markhuot/craft-pest": "^3.0"
    }
}
```

Run: `ddev craft pest/test`

### Element Factories

```php
it('creates an element', function() {
    $element = MyElement::factory()
        ->externalId('item-123')
        ->categoryId(1)
        ->postDate(new DateTime('2024-01-01'))
        ->create();

    expect($element)
        ->toBeInstanceOf(MyElement::class)
        ->externalId->toBe('item-123')
        ->getStatus()->toBe(MyElement::STATUS_LIVE);
});
```

### HTTP Testing

```php
it('requires permission to view settings', function() {
    $this->actingAs(User::factory()->create())
        ->get('/admin/my-plugin/settings')
        ->assertForbidden();
});

it('allows admin to edit items', function() {
    $this->actingAsAdmin()
        ->get('/admin/my-plugin/settings/items/new')
        ->assertOk();
});
```

### Database Assertions

```php
it('saves item to database', function() {
    $item = new MyEntity(['name' => 'Test', 'handle' => 'test']);
    MyPlugin::$plugin->getItems()->saveItem($item);

    $this->assertDatabaseHas(Table::ITEMS, ['handle' => 'test']);
});
```

### Queue Assertions

```php
it('pushes sync job to queue', function() {
    MyPlugin::$plugin->getSync()->startSync($categoryId);

    expect(Craft::$app->getQueue())
        ->toHavePushed(SyncItems::class);
});
```

### Test Conventions

- Descriptive `it()` names: `it('prevents duplicate bulk operations')`.
- One assertion per test where practical.
- Factories for all elements and models.
- Mirror source paths: `src/services/Items.php` → `tests/services/ItemsTest.php`.

## Code Review Checklist

For the full PHP coding standards, see the `craft-php-guidelines` skill. Key checks before every commit:

1. `ddev composer check-cs` passes
2. `ddev composer phpstan` passes
3. Tests green
4. PHPDocs complete — classes, methods, properties, `@throws` chains
5. Section headers present with `=========` separators
6. Imports alphabetical and grouped
7. Permissions on all controller actions
8. `requirePostRequest()` on mutating actions
9. `addSelect()` convention in `beforePrepare()` (additive across extensions)
10. Events fired for extensibility
11. MemoizableArray cache invalidated on data changes
12. No N+1 queries — eager loading used where needed
13. Large operations pushed to queue
14. Conventional commit message prepared
