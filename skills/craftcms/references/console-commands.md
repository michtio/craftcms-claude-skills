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

## Contents

- [Environment Notes](#environment-notes)
- [Built-in Command Reference](#built-in-command-reference)
- [Generator Commands](#generator-commands-craft-make)
- [Scaffold](#scaffold)
- [Arguments and Options](#arguments-and-options)
- [Rich Output Helpers](#rich-output-helpers-since-440)
- [Interactive Prompts](#interactive-prompts)
- [Progress Bars](#progress-bars)
- [Resave Pattern via EVENT_DEFINE_ACTIONS](#resave-pattern-via-event_define_actions)
- [Long-Running Commands](#long-running-commands)
- [Command Registration](#command-registration)

## Environment Notes

Always use `ddev craft` instead of running `craft` directly on the host. DDEV executes the command inside the web container where PHP, Composer dependencies, and database connections are available.

| Variable | Purpose |
|----------|---------|
| `CRAFT_ALLOW_SUPERUSER` | Set to `1` when running as root in containers. DDEV sets this automatically. |
| `CRAFT_ENVIRONMENT` | Determines which config overrides apply (`dev`, `staging`, `production`). Matched by multi-environment config arrays in `config/general.php` and `config/db.php`. |
| `CRAFT_RUN_QUEUE_AUTOMATICALLY` | Set to `0` in production — process jobs via `craft queue/listen` daemon instead. |

When scripting CI/CD pipelines, pass `--interactive=0` to all commands so prompts return their defaults without blocking.

## Built-in Command Reference

### Project & Setup

| Command | Purpose |
|---------|---------|
| `craft up` | Run pending migrations + apply project config. The single command for deployments. |
| `craft install` | Run the Craft installer (creates admin user, sets site URL). |
| `craft setup` | Interactive setup wizard — generates `.env`, creates database, runs installer. |
| `craft project-config/apply` | Apply project config YAML without running migrations. |
| `craft project-config/rebuild` | Rebuild project config from current DB state. Useful when YAML and DB diverge. |
| `craft project-config/touch` | Update `dateModified` to force re-apply on next `craft up`. |
| `craft project-config/diff` | Show diff between DB state and YAML files. |

### Content & Elements

| Command | Purpose |
|---------|---------|
| `craft resave/entries` | Resave entries — triggers `afterSave` events, updates search index. |
| `craft resave/assets` | Resave assets. |
| `craft resave/users` | Resave users. |
| `craft resave/tags` | Resave tags. |
| `craft resave/categories` | Resave categories. |
| `craft entrify/categories` | Convert categories to entries (Craft 5 entrification). |
| `craft entrify/tags` | Convert tags to entries. |
| `craft update-statuses` | Update entry statuses based on post/expiry dates. Required when `staticStatuses` is enabled in `config/general.php`. |

Common resave flags: `--section=blog`, `--type=post`, `--status=disabled`, `--limit=100`, `--update-search-index`, `--queue` (push to queue instead of running inline), `--set=fieldHandle`, `--to=value`.

### Cache & Performance

| Command | Purpose |
|---------|---------|
| `craft clear-caches/all` | Clear all caches (data, templates, transforms, asset indexing). |
| `craft clear-caches/data` | Clear data cache only (Redis/DB/file depending on config). |
| `craft clear-caches/compiled-templates` | Clear compiled Twig templates. Required after template engine changes. |
| `craft clear-caches/asset-indexing-data` | Clear asset indexing data. |
| `craft invalidate-tags/all` | Invalidate all template cache tags. |
| `craft invalidate-tags/template` | Invalidate template caches only. |
| `craft gc` | Run garbage collection — purge soft-deleted elements, unsaved drafts, expired tokens. Accepts `--delete-all-trashed` to skip the soft-delete retention period. |

### Database

| Command | Purpose |
|---------|---------|
| `craft db/backup` | Create database backup to `storage/backups/`. Accepts `--path` for custom location. |
| `craft db/restore` | Restore from backup file. Pass the path as an argument. |
| `craft db/search-indexes` | Rebuild search indexes. Required after changing the search component config in `config/app.php`. |
| `craft db/convert-charset` | Convert database charset (e.g., to `utf8mb4`). |

### Users

| Command | Purpose |
|---------|---------|
| `craft users/create` | Create a user interactively (email, username, password, admin flag). |
| `craft users/set-password` | Set a user's password. Accepts `--password` or prompts securely. |
| `craft users/list` | List users with ID, email, username, and admin status. |

### Queue

For queue architecture and custom job implementation, see `queue-jobs.md`.

| Command | Purpose |
|---------|---------|
| `craft queue/run` | Process all pending jobs (one-off, exits when empty). |
| `craft queue/listen` | Start queue daemon — continuously polls for new jobs. Add `--verbose` for per-job logging. Use with process managers (systemd, supervisor) in production. |
| `craft queue/info` | Show queue state: pending, reserved, done, and failed counts. |
| `craft queue/retry` | Retry all failed jobs. Accepts `--id` to retry a specific job. |
| `craft queue/release` | Release stuck/reserved jobs back to pending. Use when a worker crashed mid-job. |

### Other Useful Commands

| Command | Purpose |
|---------|---------|
| `craft serve` | Start PHP's built-in web server. Not needed with DDEV. |
| `craft migrate/all` | Run all pending migrations (content, plugin, Craft). `craft up` is preferred. |
| `craft off` | Enable system offline mode (maintenance). Accepts `--retry` to set `Retry-After` header. |
| `craft on` | Disable system offline mode. |
| `craft index-assets/all` | Re-index all asset volumes. Accepts a volume handle to index selectively. |
| `craft index-assets <volume>` | Re-index a specific volume by handle. |

### Deployment Recipes

**Standard deployment** (CI/CD or post-deploy hook):

```bash
ddev craft up                    # Migrations + project config
ddev craft clear-caches/all      # Purge stale caches
```

**After content modeling changes** (new sections, fields, entry types):

```bash
ddev craft project-config/touch  # Force dateModified update
ddev craft up                    # Apply the changes
ddev craft resave/entries --update-search-index  # Re-index affected entries
```

**After search config changes** (`config/app.php` search component):

```bash
ddev craft db/search-indexes     # Full search index rebuild
```

**Emergency: project config out of sync with DB**:

```bash
ddev craft project-config/diff   # See what diverged
ddev craft project-config/rebuild # Rebuild YAML from DB (destructive to YAML)
# Or: ddev craft project-config/apply  # Apply YAML to DB (destructive to DB)
```

**Pre-backup before risky operations**:

```bash
ddev craft db/backup             # Snapshot to storage/backups/
```

## Generator Commands (`craft make`)

Craft 5's generator scaffolds boilerplate with correct namespaces, class structure, and optional PHPDoc blocks. Always use `--with-docblocks` to include section headers and documentation stubs.

```bash
ddev craft make <type> --with-docblocks
```

### Available Generators

| Command | What it scaffolds |
|---------|------------------|
| `craft make module` | Module class + `app.php` registration config. |
| `craft make element-type` | Element class + element query class. |
| `craft make field-type` | Custom field type class with settings and input template. |
| `craft make controller` | Controller with action method stubs. |
| `craft make model` | Model class with `defineRules()` and `attributeLabels()`. |
| `craft make migration` | Timestamped migration file in the correct plugin/module directory. |
| `craft make widget` | Dashboard widget class with body template. |
| `craft make utility` | CP utility page with content template. |
| `craft make command` | Console command class extending `craft\console\Controller`. |
| `craft make queue-job` | Queue job class with `execute()` method. |
| `craft make gql-directive` | GraphQL directive class. |
| `craft make generator` | Custom generator — extend the `craft make` system with project-specific scaffolding. |

### Generator Tips

- Generators prompt for the target module or plugin — no manual path wrangling needed.
- `--with-docblocks` adds section headers (`// =========================================================================`), `@author`, `@since`, and `@inheritdoc` where applicable.
- After scaffolding, customize to match project conventions: add `@throws` chains, remove unused section headers, and fill in property types.
- For elements, the generator creates both the element class and its query class. You still need to add migration(s) for the content table and register CP routes.

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
