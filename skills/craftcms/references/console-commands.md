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
  - [Global Options](#global-options)
  - [Project and Setup](#project-and-setup)
  - [Project Config](#project-config)
  - [Sections and Entry Types](#sections-and-entry-types)
  - [Fields](#fields)
  - [Content and Elements](#content-and-elements)
  - [Cache and Performance](#cache-and-performance)
  - [Database](#database)
  - [Users](#users)
  - [Plugin Management](#plugin-management)
  - [Queue](#queue)
  - [Migrations](#migrations)
  - [GraphQL](#graphql)
  - [Email](#email)
  - [Utilities](#utilities)
  - [Environment and Shell](#environment-and-shell)
  - [Other Commands](#other-commands)
  - [Deployment Recipes](#deployment-recipes)
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

### Global Options

Every Craft CLI command supports these inherited options:

| Option | Purpose |
|--------|---------|
| `--color` | Force ANSI color output. |
| `--help` | Display help for the command. |
| `--interactive=0` | Disable interactive prompts (use defaults). Required for CI/CD pipelines. |
| `--isolated` | Prevent concurrent execution via mutex. Use for sync/import/cleanup commands. |
| `--silent-exit-on-exception` | Exit silently on exception (no stack trace). |

### Project and Setup

| Command | Purpose |
|---------|---------|
| `craft up` | Run pending migrations + apply project config. The single command for deployments. |
| `craft install/check` | Check whether Craft is already installed. Returns exit code `0` if installed. |
| `craft install/craft` | Run the Craft installer. Accepts `--email`, `--username`, `--password`, `--site-name`, `--site-url`, `--language`. |
| `craft setup` | Interactive setup wizard — generates `.env`, creates database, runs installer. |
| `craft setup/app-id` | Generate and save a unique `APP_ID` to `.env`. |
| `craft setup/security-key` | Generate and save a `CRAFT_SECURITY_KEY` to `.env`. |
| `craft setup/keys` | Generate both `APP_ID` and `CRAFT_SECURITY_KEY` at once. |
| `craft setup/db` | Configure database connection settings in `.env`. |
| `craft setup/db-cache-table` | Create the `cache` table for DB-based cache driver. |
| `craft setup/php-session-table` | Create the `phpsessions` table for DB-based session driver. |
| `craft setup/cloud` | Configure Craft Cloud settings. |
| `craft setup/welcome` | Display post-install welcome information. |
| `craft update/info` | Show available Craft and plugin updates. |
| `craft update/update` | Apply updates. Accepts `--minor-only`, `--patch-only`, `--force`, `--backup`. |
| `craft update/composer-install` | Run `composer install` and apply pending migrations. |

### Project Config

The `project-config/` controller has a `pc/` shorthand alias — `craft pc/apply` is equivalent to `craft project-config/apply`.

| Command | Purpose |
|---------|---------|
| `craft pc/apply` | Apply project config YAML without running migrations. |
| `craft pc/rebuild` | Rebuild project config from current DB state. Useful when YAML and DB diverge. |
| `craft pc/touch` | Update `dateModified` to force re-apply on next `craft up`. |
| `craft pc/diff` | Show diff between DB state and YAML files. |
| `craft pc/export` | Export project config as a single YAML blob to stdout. |
| `craft pc/get` | Get a project config value by path (e.g., `craft pc/get system.name`). |
| `craft pc/set` | Set a project config value. Accepts `--force`, `--message`, `--update-timestamp`. |
| `craft pc/remove` | Remove a project config value by path. |
| `craft pc/write` | Write project config YAML files to `config/project/` from the loaded config. |

### Sections and Entry Types

| Command | Purpose |
|---------|---------|
| `craft sections/create` | Create a new section. Accepts `--name`, `--handle`, `--type` (single/channel/structure), `--uri-format`, `--template`, `--from-category-group`, `--from-tag-group`, `--from-global-set`. |
| `craft sections/delete` | Delete a section by handle or interactively. |
| `craft entry-types/merge` | Merge two entry types — reassign entries from one type to another, then delete the source type. |

### Fields

| Command | Purpose |
|---------|---------|
| `craft fields/auto-merge` | Automatically merge fields with identical settings into a single global field. |
| `craft fields/delete` | Delete a field by handle or interactively. |
| `craft fields/merge` | Merge two fields — reassign content from one field to another, then delete the source field. |

### Content and Elements

| Command | Purpose |
|---------|---------|
| `craft resave/all` | Resave all element types. |
| `craft resave/entries` | Resave entries — triggers `afterSave` events, updates search index. |
| `craft resave/assets` | Resave assets. |
| `craft resave/users` | Resave users. |
| `craft resave/addresses` | Resave address elements. |
| `craft resave/tags` | Resave tags. |
| `craft resave/categories` | Resave categories. |
| `craft entrify/categories` | Convert categories to entries (Craft 5 entrification). |
| `craft entrify/tags` | Convert tags to entries. |
| `craft entrify/global-set` | Convert a global set to a single entry. |
| `craft elements/delete` | Delete elements by ID or criteria. Accepts `--hard` for permanent deletion (skip soft-delete). |
| `craft elements/delete-all-of-type` | Delete all elements of a given type. Accepts `--dry-run` to preview without deleting. |
| `craft elements/restore` | Restore soft-deleted elements by ID. |
| `craft update-statuses` | Update entry statuses based on post/expiry dates. Required when `staticStatuses` is enabled in `config/general.php`. |

Common resave flags: `--queue` (push to queue instead of running inline), `--batch-size`, `--element-id`, `--uid`, `--site`, `--status`, `--offset`, `--limit`, `--update-search-index`, `--touch` (update `dateUpdated` without re-saving), `--set=fieldHandle`, `--to=value`, `--if-empty` (only set if field is empty), `--if-invalid` (only resave elements that fail validation).

Element type-specific flags: `--section=blog`, `--type=post` (entries), `--volume=images` (assets), `--group=myGroup` (users).

### Cache and Performance

| Command | Purpose |
|---------|---------|
| `craft clear-caches/all` | Clear all caches (data, templates, transforms, asset indexing). |
| `craft clear-caches/data` | Clear data cache only (Redis/DB/file depending on config). |
| `craft clear-caches/compiled-templates` | Clear compiled Twig templates. Required after template engine changes. |
| `craft clear-caches/compiled-classes` | Clear compiled class files. |
| `craft clear-caches/cp-resources` | Clear published CP resource files. |
| `craft clear-caches/temp-files` | Clear temporary files from `storage/runtime/temp/`. |
| `craft clear-caches/transform-indexes` | Clear asset transform index data. |
| `craft clear-caches/asset-indexing-data` | Clear asset indexing data. |
| `craft invalidate-tags/all` | Invalidate all template cache tags. |
| `craft invalidate-tags/template` | Invalidate template caches only. |
| `craft invalidate-tags/graphql` | Invalidate GraphQL query caches. |
| `craft clear-deprecations` | Clear all logged deprecation warnings. |
| `craft gc` | Run garbage collection — purge soft-deleted elements, unsaved drafts, expired tokens. Accepts `--delete-all-trashed` to skip the soft-delete retention period. |

### Database

| Command | Purpose |
|---------|---------|
| `craft db/backup` | Create database backup to `storage/backups/`. Accepts `--path`, `--zip`, `--overwrite`. |
| `craft db/restore` | Restore from backup file. Pass the path as an argument. Accepts `--drop-all-tables` to wipe before restoring. |
| `craft db/convert-charset` | Convert database charset (e.g., to `utf8mb4`). |
| `craft db/drop-all-tables` | Drop all tables in the database. Destructive — prompts for confirmation. |
| `craft db/drop-table-prefix` | Remove the table prefix from all Craft tables. |
| `craft db/repair` | Repair database integrity issues (foreign keys, orphaned rows). |

Note: search index rebuilding is handled via `craft resave/* --update-search-index`. Check `craft help` for the current list of DB commands in your Craft version.

### Users

| Command | Purpose |
|---------|---------|
| `craft users/create` | Create a user interactively (email, username, password, admin flag). |
| `craft users/delete` | Delete a user. Accepts `--inheritor` (user to inherit content), `--delete-content`, `--hard`. |
| `craft users/set-password` | Set a user's password. Accepts `--password` or prompts securely. |
| `craft users/list` | List users with ID, email, username, and admin status. |
| `craft users/list-admins` | List admin users only. |
| `craft users/unlock` | Unlock a locked-out user account. |
| `craft users/activation-url` | Generate an activation URL for a pending user. |
| `craft users/password-reset-url` | Generate a password reset URL for a user. |
| `craft users/impersonate` | Generate an impersonation URL to log in as a user. |
| `craft users/remove-2fa` | Remove two-factor authentication from a user account. |
| `craft users/logout-all` | Log out all users by invalidating all active sessions. |

### Plugin Management

| Command | Purpose |
|---------|---------|
| `craft plugin/list` | List all installed plugins with their status (enabled/disabled) and version. |
| `craft plugin/install` | Install a plugin by handle. Accepts `--all` to install all pending plugins. |
| `craft plugin/uninstall` | Uninstall a plugin by handle. Accepts `--force` (skip confirmation), `--all`. |
| `craft plugin/enable` | Enable a disabled plugin. Accepts `--all`. |
| `craft plugin/disable` | Disable a plugin without uninstalling. Accepts `--all`. |

### Queue

For queue architecture and custom job implementation, see `queue-jobs.md`.

| Command | Purpose |
|---------|---------|
| `craft queue/run` | Process all pending jobs (one-off, exits when empty). |
| `craft queue/listen` | Start queue daemon — continuously polls for new jobs. Add `--verbose` for per-job logging. Use with process managers (systemd, supervisor) in production. |
| `craft queue/info` | Show queue state: pending, reserved, done, and failed counts. |
| `craft queue/retry` | Retry all failed jobs. Accepts `--id` to retry a specific job. |
| `craft queue/release` | Release stuck/reserved jobs back to pending. Use when a worker crashed mid-job. |
| `craft queue/exec` | Internal — execute a specific job by ID. Called by the queue runner, not invoked directly. |

### Migrations

| Command | Purpose |
|---------|---------|
| `craft migrate/all` | Run all pending migrations (content, plugin, Craft). `craft up` is preferred. |
| `craft migrate/create` | Create a new migration file. Prompts for migration name and target (content, plugin, or module). |
| `craft migrate/up` | Run pending migrations. Accepts a count to limit how many to apply. |
| `craft migrate/down` | Revert migrations. Accepts a count (default 1). |
| `craft migrate/redo` | Revert and re-apply migrations. Accepts a count. |
| `craft migrate/to` | Migrate to a specific version (timestamp or migration name). |
| `craft migrate/history` | Show applied migration history. Accepts `--limit` to control output. |
| `craft migrate/new` | Show pending (unapplied) migrations. |
| `craft migrate/mark` | Mark a migration as applied without running it. |

### GraphQL

| Command | Purpose |
|---------|---------|
| `craft graphql/create-token` | Create a new GraphQL API token. |
| `craft graphql/dump-schema` | Dump the GraphQL schema to a file. |
| `craft graphql/list-schemas` | List all GraphQL schemas. |
| `craft graphql/print-schema` | Print the GraphQL schema to stdout. |

### Email

| Command | Purpose |
|---------|---------|
| `craft mailer/test` | Send a test email. Accepts `--to` to specify the recipient address. |

### Utilities

| Command | Purpose |
|---------|---------|
| `craft utils/prune-revisions` | Prune excess entry revisions. Accepts `--dry-run`, `--max-revisions`, `--section`. |
| `craft utils/prune-orphaned-entries` | Delete entries that belong to deleted sections or entry types. |
| `craft utils/prune-provisional-drafts` | Delete stale provisional drafts. |
| `craft utils/ascii-filenames` | Rename assets to ASCII-safe filenames. |
| `craft utils/delete-empty-volume-folders` | Remove empty folders from asset volumes. |
| `craft utils/fix-element-uids` | Regenerate missing or duplicate element UIDs. |
| `craft utils/fix-field-layout-uids` | Regenerate missing or duplicate field layout UIDs. |
| `craft utils/repair/category-group-structure` | Repair a category group's nested set structure. |
| `craft utils/repair/section-structure` | Repair a section's nested set structure. |
| `craft utils/repair/project-config` | Repair project config inconsistencies. |
| `craft utils/update-usernames` | Update usernames to match email addresses (when `useEmailAsUsername` is enabled). |

### Environment and Shell

| Command | Purpose |
|---------|---------|
| `craft env/set` | Set an environment variable in `.env`. |
| `craft env/remove` | Remove an environment variable from `.env`. |
| `craft env/show` | Display current `.env` values. |
| `craft shell` | Launch an interactive PHP shell (PsySH) with Craft bootstrapped. |
| `craft exec/exec` | Execute a PHP statement and print the result. |

### Other Commands

| Command | Purpose |
|---------|---------|
| `craft serve` | Start PHP's built-in web server. Not needed with DDEV. |
| `craft off` | Enable system offline mode (maintenance). Accepts `--retry` to set `Retry-After` header. |
| `craft on` | Disable system offline mode. |
| `craft index-assets/all` | Re-index all asset volumes. Accepts a volume handle to index selectively. |
| `craft index-assets <volume>` | Re-index a specific volume by handle. |
| `craft cache/flush` | Flush a specific cache component. |
| `craft cache/flush-all` | Flush all registered cache components. |
| `craft cache/flush-schema` | Flush the DB schema cache. Required after direct DB schema changes outside migrations. |

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
ddev craft resave/entries --update-search-index   # Rebuild search for entries
ddev craft resave/assets --update-search-index    # Rebuild search for assets
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
ddev craft db/backup --zip       # Compressed backup
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
