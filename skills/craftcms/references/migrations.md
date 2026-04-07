# Migrations

## Documentation

- Migrations: https://craftcms.com/docs/5.x/extend/migrations.html
- Content migrations: https://craftcms.com/docs/5.x/extend/migrations.html#content-migrations

## Common Pitfalls

- Forgetting `muteEvents` on `ProjectConfig::set()` inside migrations — triggers handlers that may depend on state that doesn't exist yet.
- Generating random UIDs when project config YAML already ships from dev — check if the config path exists first.
- Non-idempotent steps — always check column/table existence before adding.
- Using `null` for FK name but specifying one for index — use `null` for both, Craft generates deterministic names.
- Missing `TRUNCATE cache` after failed migrations on Craft Cloud — stale mutex locks block retries.
- Not thinking about ON DELETE behavior — `CASCADE` for owned data, `SET NULL` for references, `RESTRICT` for protected refs.

## Scaffold

```bash
ddev craft make migration --with-docblocks
```

The `Install.php` migration runs on plugin install. Numbered migrations run on `ddev craft up`.

**Modules** don't have `Install.php` — use content migrations created with `ddev craft migrate/create my_migration_name`. These go in the project's `migrations/` directory and share a global track.

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
// Element table → elements.id with CASCADE delete
$this->addForeignKey(null, Table::MY_ELEMENTS, ['id'], CraftTable::ELEMENTS, ['id'], 'CASCADE', null);

// Reference to config table — SET NULL on delete
$this->addForeignKey(null, Table::MY_ELEMENTS, ['categoryId'], Table::CATEGORIES, ['id'], 'SET NULL', null);
```

Use `null` for the FK name — Craft generates a deterministic name. Always decide: `CASCADE` for owned data, `SET NULL` for references, `RESTRICT` for protected references.

## Indexes

```php
// Compound unique for external ID scoping
$this->createIndex(null, Table::MY_ELEMENTS, ['categoryId', 'externalId'], true);

// Performance indexes
$this->createIndex(null, Table::MY_ELEMENTS, ['postDate']);
$this->createIndex(null, Table::MY_ELEMENTS, ['expiryDate']);
```

## Deployment

These apply to every Craft deployment — Craft Cloud, Servd, Forge, bare metal, or any CI/CD pipeline:

- Always run `ddev craft up` locally before deploying — this runs pending migrations and applies project config changes in one command.
- Migrations should run before the application serves traffic. Most hosting platforms and CI/CD pipelines handle this as a separate deploy step.
- Failed migrations can leave mutex locks in the `cache` table — `TRUNCATE cache` to recover.
- `craft clear-caches/all` after deployment if caches aren't automatically invalidated by your hosting platform.
- The project config YAML files in `config/project/` are the source of truth for configuration. Never edit the `projectConfig` database table directly.
