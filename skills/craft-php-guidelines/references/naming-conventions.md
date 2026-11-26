# Naming Conventions

## General Naming

| Thing | Convention | Example |
|-------|-----------|---------|
| Namespace | All lowercase | `vendor\pluginhandle` |
| Class | StudlyCase | `MyEntity` |
| Method | camelCase | `getEntityById()` |
| Private method | Underscore prefix | `_registerCpUrlRules()` |
| Yii-invoked method | Public, **no** underscore | `validateSiteSettings()` — see exception below |
| Property | camelCase | `$entityId` |
| Private property | Underscore prefix | `$_items` |
| Constant | UPPER_SNAKE_CASE | `EVENT_BEFORE_SAVE` |
| Table constant | Craft format | `{{%pluginhandle_items}}` |
| Event constant | Before/after pattern | `EVENT_BEFORE_SAVE_ITEM` |
| Config path | Dot-separated | `pluginhandle.items` |
| Enum | StudlyCase | `BulkOperationStatus` |
| Enum case | PascalCase | `Processing` |

## File Structure Naming

| Type | Convention | Example |
|------|-----------|---------|
| Plugin entry | Named after the plugin | `Cockpit.php`, `Typesense.php`, `PasswordPolicy.php` |
| Element | Singular | `Entry.php`, `Asset.php`, `User.php` |
| Element query | Singular + Query | `EntryQuery.php`, `AssetQuery.php` |
| Element action | Action verb, no suffix | `Delete.php`, `Duplicate.php`, `SetStatus.php` |
| Element condition | Domain + ConditionRule | `SectionConditionRule.php`, `TypeConditionRule.php` |
| Element exporter | Descriptive, no suffix | `Expanded.php`, `Raw.php` |
| Model | Singular | `Section.php`, `Volume.php`, `EntryType.php` |
| Record | Same name as model | `Section.php`, `Volume.php` (namespace distinguishes) |
| Service (resource) | Plural | `Entries.php`, `Volumes.php`, `Users.php` |
| Service (utility) | Domain noun | `Auth.php`, `Search.php`, `Gc.php` |
| Controller (resource) | Plural + Controller | `EntriesController.php`, `SectionsController.php` |
| Controller (action) | Domain + Controller | `AppController.php`, `AuthController.php` |
| Console controller | Domain + Controller | `SyncController.php`, `ResaveController.php` |
| Queue job | Action verb phrase, no suffix | `ResaveElements.php`, `UpdateSearchIndex.php` |
| Event | Domain + Event | `SectionEvent.php`, `VolumeEvent.php` |
| Register event | Register + Domain + Event | `RegisterUrlRulesEvent.php` |
| Define event | Define + Domain + Event | `DefineHtmlEvent.php`, `DefineRulesEvent.php` |
| Validator | Domain + Validator | `HandleValidator.php`, `UniqueValidator.php` |
| Helper | Domain (suffix optional) | `Db.php`, `Cp.php`, `ArrayHelper.php` |
| Enum | Descriptive name | `PropagationMethod.php`, `CmsEdition.php` |
| Migration | Timestamped | `m240101_000000_add_column.php` |
| Install migration | `Install.php` | `Install.php` |

## Record Aliasing

When importing both model and record in the same file, alias the record:

```php
use vendor\myplugin\models\MyEntity;
use vendor\myplugin\records\MyEntity as MyEntityRecord;
```

## Visibility Exception: Yii-Invoked Methods

Methods that Yii invokes by name from outside the class are **public with no underscore prefix**, even if they feel "internal." Yii resolves these by string name on the object — private or underscore-prefixed methods won't be found.

This applies to:
- **Inline validator methods** referenced from `defineRules()` — `'validateSiteSettings'`
- **`when` callables** in validator rules — `[$this, 'hasMaxRows']`
- **Event handler methods** referenced as strings in config
- **Behavior callables** referenced by name

General principle: any method Yii invokes by name is part of the public API surface.

## Quick Reference

| Thing | Convention | Example |
|-------|-----------|---------|
| Services (resource) | Plural | `Entries`, `Volumes`, `Users` |
| Services (utility) | Domain noun | `Auth`, `Search`, `Gc` |
| Queue jobs | Action verb, no suffix | `ResaveElements`, `UpdateSearchIndex` |
| Records | Same name as model | Namespace distinguishes |
| Events | Three patterns | `SectionEvent`, `RegisterUrlRulesEvent`, `DefineHtmlEvent` |
| Element actions | Action verb, no suffix | `Delete`, `Duplicate`, `SetStatus` |
| Enums | PascalCase cases, string/int backed | `PropagationMethod`, `CmsEdition` |

## Permission Handles

**Permission handles are kebab-case (`handle:manage-settings`); never camelCase.** Both halves are lowercase kebab — `savepoint:manage-settings`, `multiplayer:take-over-field`, not `savepoint:manageSettings`.

Craft lowercases permission names into `userpermissions.name`, so case is discarded on the way to storage: `manageSettings` collapses to `managesettings`, while `manage-settings` keeps its word boundaries and stays readable in the database, in exports, and in debug output.

**Craft core's own permissions are camelCase** (`accessCp`, `editUsers`, `viewPeerEntries`). This is a deliberate divergence for plugin-owned handles — don't "correct" plugin handles back to camelCase for consistency with core, and don't rewrite core's handles.

The PHP constant holding the handle stays `SCREAMING_SNAKE_CASE` (`PERMISSION_MANAGE_SETTINGS`); only the string value is kebab. Full mechanics in the `craftcms` skill's `permissions.md`.

### Permission handle constants

Duplicating contract constants as `private const` across multiple classes with "keep in lockstep" comments — PHPStan can't detect drift. Declare `public const` on the owning service, reference as `OwnerService::CONSTANT_NAME` everywhere else. This applies specifically to **permission handles**: a handle like `'my-plugin:manage-settings'` is a contract string referenced from registration (`EVENT_REGISTER_PERMISSIONS`), the controller gate (`requirePermission()`), and the nav check (`->can()`); a bare literal drifts silently and a typo passes for admins (who hold every permission) while denying everyone else. Declare it as a `public const` on the controller that enforces it — `SettingsController::PERMISSION_MANAGE_SETTINGS` — and reference the const everywhere. (Craft core uses bare literals here; the const is a deliberately stricter house rule. See the `craftcms` skill's `permissions.md`.)
