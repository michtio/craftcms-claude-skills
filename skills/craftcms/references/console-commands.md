# Console Commands

## Documentation

- Commands: https://craftcms.com/docs/5.x/extend/commands.html
- `craft\console\Controller`: https://docs.craftcms.com/api/v5/craft-console-controller.html
- `craft\helpers\Console`: https://docs.craftcms.com/api/v5/craft-helpers-console.html

## Common Pitfalls

- Setting `controllerNamespace` after `parent::init()` in modules — it must come before, or commands are undiscoverable.
- Using raw `$this->stdout()` with color constants when Craft 5 provides `$this->success()`, `$this->failure()`, `$this->tip()`, `$this->warning()` with Markdown→ANSI rendering.
- Forgetting `parent::options($actionID)` — loses `--interactive`, `--color`, `--help`, `--isolated`.
- Not calling `App::maxPowerCaptain()` for long-running commands — runs into memory/time limits.
- Missing `--isolated` for commands that shouldn't run concurrently (sync, import, cleanup).

## Scaffold

```bash
ddev craft make command --with-docblocks
```

## Arguments and Options

**Arguments** are action method parameters, mapped positionally:

```php
// Usage: ddev craft my-plugin/sync/jobs 42
public function actionJobs(int $instanceId): int
{
    // $instanceId = 42
}
```

**Options** are public properties registered via `options()`. Always call parent first:

```php
public ?string $type = null;
public bool $dryRun = false;

public function options($actionID): array
{
    $options = parent::options($actionID);
    $options[] = 'type';
    $options[] = 'dryRun';
    return $options;
}

public function optionAliases(): array
{
    $aliases = parent::optionAliases();
    $aliases['t'] = 'type';
    $aliases['n'] = 'dryRun';
    return $aliases;
}
```

Usage: `ddev craft my-plugin/sync/jobs --type=widgets -n`

## Rich Output Helpers (since 4.4.0)

Craft's `ControllerTrait` provides semantic output methods. All support Markdown formatting (backticks become highlighted, `**bold**` becomes ANSI bold):

```php
$this->success('Import completed.');              // ✅ prefix
$this->failure('Import failed.');                  // ❌ prefix
$this->tip('Try `ddev craft resave/entries`.');    // 💡 prefix
$this->warning('**Careful** — this is destructive.'); // ⚠️ prefix
$this->note('Custom message.', '🔄 ');            // Custom emoji prefix
```

### Descriptive Actions with `do()`

Wraps an operation with status output and optional timing:

```php
$this->do('Rebuilding search index', function() {
    // ... expensive work ...
}, withDuration: true);
// Output: → Rebuilding search index … ✓ done (time: 2.341s)
```

### Table Output

```php
$this->table(
    ['ID', 'Title', ['Count', 'align' => 'right']],
    [
        ['1', 'My Entry', '42'],
        ['2', 'Another Entry', '7'],
    ]
);
```

### Raw Output with Colors

When you need low-level control:

```php
use craft\helpers\Console;

$this->stdout("Processing...\n", Console::FG_CYAN);
$this->stderr("Error: not found\n", Console::FG_RED);
```

Color constants: `FG_RED`, `FG_GREEN`, `FG_CYAN`, `FG_YELLOW`, `FG_GREY`. Decorations: `BOLD`, `ITALIC`, `UNDERLINE`.

## Interactive Prompts

All respect `--interactive=0` (return defaults in non-interactive mode):

```php
// Boolean yes/no
if ($this->confirm('Delete all records?', false)) {
    // proceed
}

// String input with validation
$handle = $this->prompt('Enter handle:', [
    'required' => true,
    'validator' => $this->createAttributeValidator($model, 'handle'),
]);

// Selection from options
$env = $this->select('Choose environment:', [
    'dev' => 'Development',
    'staging' => 'Staging',
    'prod' => 'Production',
]);

// Secure password input
$password = $this->passwordPrompt(['confirm' => true]);
```

## Progress Bars

```php
use craft\helpers\Console;

$items = $this->_fetchItems();
$total = count($items);

Console::startProgress(0, $total, 'Processing: ');
foreach ($items as $i => $item) {
    $this->_processItem($item);
    Console::updateProgress($i + 1, $total);
}
Console::endProgress();
```

## Resave Pattern via EVENT_DEFINE_ACTIONS

Add custom resave commands to Craft's built-in `ResaveController` — this gives you progress reporting, `--queue` support, and `--set`/`--to` for free:

```php
use craft\console\Controller;
use craft\console\controllers\ResaveController;
use craft\events\DefineConsoleActionsEvent;

Event::on(
    ResaveController::class,
    Controller::EVENT_DEFINE_ACTIONS,
    function(DefineConsoleActionsEvent $event) {
        $event->actions['my-elements'] = [
            'options' => ['type'],
            'helpSummary' => 'Re-saves custom elements.',
            'action' => function(): int {
                $controller = Craft::$app->controller;
                $criteria = [];
                if ($controller->type) {
                    $criteria['type'] = explode(',', $controller->type);
                }
                return $controller->resaveElements(MyElement::class, $criteria);
            },
        ];
    }
);
```

Usage: `ddev craft resave/my-elements --type=widgetType --queue`

## Long-Running Commands

```php
public function actionImport(): int
{
    App::maxPowerCaptain(); // Raise memory + remove time limit

    $db = Craft::$app->getDb();
    $transaction = $db->beginTransaction();

    try {
        foreach (Db::each($query) as $row) {
            $this->_processRow($row);
        }
        $transaction->commit();
        $this->success('Import completed.');
        return ExitCode::OK;
    } catch (\Throwable $e) {
        $transaction->rollBack();
        $this->failure("Import failed: {$e->getMessage()}");
        return ExitCode::UNSPECIFIED_ERROR;
    }
}
```

Use `Db::each()` instead of `$query->each()` — it handles unbuffered MySQL connections.

### Exclusive Execution

Use `--isolated` to prevent concurrent runs (mutex-based):

```php
// Built-in — just register the option
// Usage: ddev craft my-plugin/sync/jobs --isolated
```

The `--isolated` flag is inherited from `ControllerTrait` and uses Craft's mutex component.

## Command Registration

**Plugins**: Automatic. Place controllers in `src/console/controllers/`. Commands are accessible as `ddev craft plugin-handle/controller/action`.

**Modules**: Must set `controllerNamespace` before `parent::init()` AND be bootstrapped in `config/app.php`. See the main SKILL.md for the pattern.
