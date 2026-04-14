# Migrations

## Documentation

- Migrations: https://craftcms.com/docs/5.x/extend/migrations.html
- Content migrations: https://craftcms.com/docs/5.x/extend/migrations.html#content-migrations

## Common Pitfalls

- Forgetting `muteEvents` on `ProjectConfig::set()` inside migrations -- triggers handlers that may depend on state that doesn't exist yet.
- Generating random UIDs when project config YAML already ships from dev -- check if the config path exists first.
- Non-idempotent steps -- always check column/table existence before adding.
- Using `null` for FK name but specifying one for index -- use `null` for both, Craft generates deterministic names.
- Missing `TRUNCATE cache` after failed migrations on Craft Cloud -- stale mutex locks block retries.
- Not thinking about ON DELETE behavior -- `CASCADE` for owned data, `SET NULL` for references, `RESTRICT` for protected refs.
- Running raw SQL without checking column/table existence first -- `addColumn` on an existing column throws, `dropColumn` on a missing one throws.
- Creating project config entries in migrations AND in YAML -- double-apply causes UID collisions or duplicate structures.
- Not wrapping data transformations in transactions -- partial updates corrupt data if the migration fails halfway through.
- Using Craft element APIs (`Entry::find()`, `Craft::$app->getElements()->saveElement()`) in migrations -- the schema may not be ready yet, and element types may depend on columns/tables that don't exist until later in the migration sequence.
- Forgetting to handle both MySQL and PostgreSQL syntax differences -- `renameColumn()` is safe, but raw SQL (e.g. `ALTER TABLE ... MODIFY COLUMN`) is MySQL-only.

## Contents

- [Migration Types](#migration-types)
- [Scaffold](#scaffold)
- [Safety Rules](#safety-rules)
- [Table Creation](#table-creation)
- [Foreign Keys](#foreign-keys)
- [Indexes](#indexes)
- [Common Schema Patterns](#common-schema-patterns)
- [Content Migrations -- Creating Sections, Fields, Entry Types](#content-migrations----creating-sections-fields-entry-types)
- [Multi-Site Migrations](#multi-site-migrations)
- [Project Config Interaction](#project-config-interaction)
- [safeDown() and Rollback Patterns](#safedown-and-rollback-patterns)
- [Migration Ordering](#migration-ordering)
- [craft migrate vs craft up](#craft-migrate-vs-craft-up)
- [Deployment](#deployment)

## Migration Types

| Type | File / Location | Trigger | Use Case |
|------|----------------|---------|----------|
| Plugin install | `Install.php` in plugin's `migrations/` dir | `craft plugin/install` or first `craft up` after adding plugin | Create tables, seed project config, set up initial state |
| Plugin update | `m240101_000000_description.php` in plugin's `migrations/` dir | `craft up` when plugin version changes | Schema changes, data transformations between plugin versions |
| Content migration | `m240101_000000_description.php` in project root `migrations/` dir | `craft migrate/all` or `craft up` | Module-level or project-level changes -- anything not owned by a plugin |

### When to use which type

- **Plugin install migration**: One-time setup. Runs exactly once per environment when the plugin is installed. Handles table creation, foreign keys, indexes, and initial project config seeding. Has a corresponding `safeDown()` that tears everything down on uninstall.
- **Plugin update migration**: Incremental changes between versions. The plugin's `schemaVersion` in `composer.json` controls when these run -- Craft compares the installed version to the declared version and runs any new migrations.
- **Content migration**: For changes that belong to the project, not a plugin. Module schema changes, one-time data fixes, content structure modifications. Created with `ddev craft migrate/create my_migration_name`. These share a single global track.

## Scaffold

```bash
ddev craft make migration --with-docblocks
```

The `Install.php` migration runs on plugin install. Numbered migrations run on `ddev craft up`.

**Modules** don't have `Install.php` -- use content migrations created with `ddev craft migrate/create my_migration_name`. These go in the project's `migrations/` directory and share a global track.

## Safety Rules

### 1. Always Mute Events in Migrations

```php
Craft::$app->getProjectConfig()->muteEvents = true;
Craft::$app->getProjectConfig()->set($path, $data);
Craft::$app->getProjectConfig()->muteEvents = false;
```

### 2. Every Step Must Be Idempotent

```php
if (!$this->db->columnExists(Table::MY_ELEMENTS, 'categoryId')) {
    $this->addColumn(Table::MY_ELEMENTS, 'categoryId', $this->integer()->after('id'));
}
```

### 3. Check Before Generating UIDs

```php
$existingConfig = Craft::$app->getProjectConfig()->get($path);
if ($existingConfig !== null) {
    return; // Already seeded from YAML
}
```

## Table Creation

```php
$this->createTable(Table::MY_ELEMENTS, [
    'id' => $this->integer()->notNull(),
    'externalId' => $this->string()->notNull(),
    'categoryId' => $this->integer()->notNull(),
    'postDate' => $this->dateTime(),
    'expiryDate' => $this->dateTime(),
    'dateCreated' => $this->dateTime()->notNull(),
    'dateUpdated' => $this->dateTime()->notNull(),
    'uid' => $this->uid(),
    'PRIMARY KEY(id)',
]);
```

## Foreign Keys

```php
// Element table -> elements.id with CASCADE delete
$this->addForeignKey(null, Table::MY_ELEMENTS, ['id'], CraftTable::ELEMENTS, ['id'], 'CASCADE', null);

// Reference to config table -- SET NULL on delete
$this->addForeignKey(null, Table::MY_ELEMENTS, ['categoryId'], Table::CATEGORIES, ['id'], 'SET NULL', null);
```

Use `null` for the FK name -- Craft generates a deterministic name. Always decide: `CASCADE` for owned data, `SET NULL` for references, `RESTRICT` for protected references.

## Indexes

```php
// Compound unique for external ID scoping
$this->createIndex(null, Table::MY_ELEMENTS, ['categoryId', 'externalId'], true);

// Performance indexes
$this->createIndex(null, Table::MY_ELEMENTS, ['postDate']);
$this->createIndex(null, Table::MY_ELEMENTS, ['expiryDate']);
```

## Common Schema Patterns

### Adding columns (with idempotency)

```php
if (!$this->db->columnExists('{{%my_table}}', 'newColumn')) {
    $this->addColumn('{{%my_table}}', 'newColumn', $this->string()->after('existingColumn'));
}
```

Always check `columnExists()` first. Without this guard, re-running a migration (e.g., after a failed batch) throws a "column already exists" exception.

### Renaming columns

```php
$this->renameColumn('{{%my_table}}', 'oldName', 'newName');
```

Craft's `renameColumn()` is database-agnostic -- it generates the correct SQL for both MySQL and PostgreSQL. Do NOT use raw `ALTER TABLE ... CHANGE COLUMN` SQL, which is MySQL-only.

### Changing column types

```php
$this->alterColumn('{{%my_table}}', 'myColumn', $this->text());
```

Be careful with type changes that lose data -- `text` to `string(255)` truncates long values. For large tables, `ALTER` locks the table for its duration.

### Data transformations

```php
$transaction = Craft::$app->getDb()->beginTransaction();
try {
    $this->update('{{%my_table}}', ['status' => 'active'], ['status' => 'enabled']);
    $transaction->commit();
} catch (\Throwable $e) {
    $transaction->rollBack();
    throw $e;
}
```

Always wrap data transformations in transactions. Partial updates from a failed migration corrupt data.

### Dropping columns and tables safely

```php
if ($this->db->columnExists('{{%my_table}}', 'deprecatedColumn')) {
    $this->dropColumn('{{%my_table}}', 'deprecatedColumn');
}

$this->dropTableIfExists('{{%my_table}}');
```

`dropTableIfExists()` is built into Craft's migration base class -- preferred over checking `tableExists()` then calling `dropTable()`.

### Dropping indexes and foreign keys

```php
// Drop index by generated name
$indexName = $this->db->getIndexName('{{%my_table}}', ['columnA', 'columnB']);
$this->dropIndex($indexName, '{{%my_table}}');

// Drop foreign key by generated name
$fkName = $this->db->getForeignKeyName('{{%my_table}}', ['parentId']);
$this->dropForeignKey($fkName, '{{%my_table}}');
```

## Content Migrations -- Creating Sections, Fields, Entry Types

### Creating a section

```php
use craft\models\Section;
use craft\models\Section_SiteSettings;

$section = new Section([
    'name' => 'News',
    'handle' => 'news',
    'type' => Section::TYPE_CHANNEL,
    'siteSettings' => array_map(
        fn($site) => new Section_SiteSettings([
            'siteId' => $site->id,
            'hasUrls' => true,
            'uriFormat' => 'news/{slug}',
            'template' => 'news/_entry',
            'enabledByDefault' => true,
        ]),
        Craft::$app->getSites()->getAllSites(),
    ),
]);

if (!Craft::$app->getEntries()->saveSection($section)) {
    throw new \RuntimeException('Could not save section: ' . implode(', ', $section->getFirstErrors()));
}
```

### Creating a field

```php
use craft\fields\PlainText;

$field = new PlainText([
    'groupId' => Craft::$app->getFields()->getAllGroups()[0]->id,
    'name' => 'Subtitle',
    'handle' => 'subtitle',
    'translationMethod' => 'none',
]);

if (!Craft::$app->getFields()->saveField($field)) {
    throw new \RuntimeException('Could not save field: ' . implode(', ', $field->getFirstErrors()));
}
```

### Assigning fields to a field layout

```php
use craft\fieldlayoutelements\CustomField;
use craft\models\FieldLayout;
use craft\models\FieldLayoutTab;

$fieldLayout = new FieldLayout();
$fieldLayout->setTabs([
    new FieldLayoutTab([
        'name' => 'Content',
        'elements' => [
            ['type' => craft\fieldlayoutelements\entries\EntryTitleField::class],
            ['type' => CustomField::class, 'fieldUid' => $field->uid],
        ],
    ]),
]);

$section->setFieldLayout($fieldLayout);
Craft::$app->getEntries()->saveSection($section);
```

### Warning: project config coordination

Content migrations that create sections, fields, or entry types write to project config. If your project also has YAML files in `config/project/` that define the same structures, you get a conflict. The rule:

- **In dev**: Create structures via the CP, then export as YAML. Migrations are for data transformations only.
- **In CI/automated setups**: If you create structures programmatically, do NOT also ship YAML for those same structures. One source of truth.
- **`craft up`** applies migrations first, then project config YAML. If both create the same section, the second apply fails or creates duplicates.

## Multi-Site Migrations

### Iterating all sites

```php
$sites = Craft::$app->getSites()->getAllSites();

foreach ($sites as $site) {
    $this->update(
        '{{%content}}',
        ['field_subtitle' => 'Default subtitle'],
        ['siteId' => $site->id, 'field_subtitle' => null],
    );
}
```

### Propagating content across sites

When adding a new site, existing entries may need content populated. Query rows from the primary site and insert for the new site, checking existence first to avoid duplicates. Use `Craft::$app->getSites()->getPrimarySite()` for the source and `getSiteByHandle()` for the target.

### Site-specific data transformations

```php
$site = Craft::$app->getSites()->getSiteByHandle('de');

if ($site) {
    $this->update(
        '{{%my_table}}',
        ['locale' => 'de_DE'],
        ['siteId' => $site->id],
    );
}
```

Always null-check the site -- it may not exist in every environment (e.g., a staging environment with fewer sites than production).

## Project Config Interaction

### When to use project config vs direct DB writes

| Scenario | Approach | Reason |
|----------|----------|--------|
| Creating sections, fields, entry types | Project config (via service APIs) | These are config-managed -- direct DB writes get overwritten by `craft up` |
| Adding custom plugin tables/columns | Direct DB writes (`addColumn`, `createTable`) | Custom tables are not project config managed |
| Data transformations (UPDATE rows) | Direct DB writes | Data is not config -- project config only tracks structure |
| Seeding plugin settings | Project config with `muteEvents` | Settings sync across environments via YAML |

### The muteEvents pattern

When writing to project config inside a migration, always mute events. Without this, project config handlers fire immediately, potentially depending on database state that doesn't exist yet. See [Safety Rules](#safety-rules) for the code pattern.

### Execution order in `craft up`

1. Pending migrations run (all tracks)
2. Project config YAML is applied (diffed against the database)

If your migration creates a section and the YAML also defines that section, the YAML apply step conflicts. Rule of thumb: **let one system own each piece of config**. Migrations own data transformations. YAML owns structural config.

## safeDown() and Rollback Patterns

### Reversible schema changes

Schema changes (adding/dropping columns, tables, indexes) can typically be reversed:

```php
public function safeDown(): bool
{
    $this->dropTableIfExists('{{%my_table}}');
    // or: $this->dropColumn('{{%my_table}}', 'newColumn');
    return true;
}
```

### Non-reversible migrations

Data transformations (UPDATE, DELETE, INSERT) are generally not reversible. You can't un-transform data without storing the original values somewhere. For these, return `false`:

```php
public function safeDown(): bool|false
{
    // Data transformation is not reversible -- original values are lost.
    return false;
}
```

Returning `false` tells Craft this migration cannot be rolled back. `craft migrate/down` will refuse to undo it.

### Mixed migrations

If a migration has both schema changes and data transformations, the data transformation makes the whole migration non-reversible. Either return `false` from `safeDown()`, or reverse only the schema portions and document clearly that data changes are not restored.

## Migration Ordering

### Timestamp format

Migrations are named `m{YYMMDD}_{HHMMSS}_description.php` and execute in timestamp order. The timestamp is the creation time, not the intended execution time.

### Track isolation

Each plugin has its own migration track, triggered when the plugin's `schemaVersion` changes. Plugin A's migrations never block Plugin B's. Content migrations (project root `migrations/`) have their own track, independent of all plugin tracks.

### Running all tracks

| Command | Tracks |
|---------|--------|
| `craft up` | All plugin tracks + content track + project config |
| `craft migrate/all` | All plugin tracks + content track (no project config) |
| `craft migrate/up` | Content track only |
| `craft migrate/up --track=plugin:my-plugin` | Specific plugin track only |

## craft migrate vs craft up

| Command | Runs Migrations | Applies Project Config | Use When |
|---------|----------------|----------------------|----------|
| `craft up` | Yes (all tracks) | Yes | Deployment -- the standard deploy command |
| `craft migrate/all` | Yes (all tracks) | No | Need migrations without project config changes |
| `craft migrate/up` | Yes (content track only) | No | Running only content migrations |
| `craft migrate/down` | Rolls back last migration (content track) | No | Undoing a content migration in development |

`craft up` is the correct command for deployments. It runs migrations first, then applies project config YAML. Running `craft migrate/all` alone in a deploy script means project config changes from other developers never get applied.

## Deployment

These apply to every Craft deployment -- Craft Cloud, Servd, Forge, bare metal, or any CI/CD pipeline:

- Always run `ddev craft up` locally before deploying -- this runs pending migrations and applies project config changes in one command.
- Migrations should run before the application serves traffic. Most hosting platforms and CI/CD pipelines handle this as a separate deploy step.
- Failed migrations can leave mutex locks in the `cache` table -- `TRUNCATE cache` to recover.
- `craft clear-caches/all` after deployment if caches aren't automatically invalidated by your hosting platform.
- The project config YAML files in `config/project/` are the source of truth for configuration. Never edit the `projectConfig` database table directly.
