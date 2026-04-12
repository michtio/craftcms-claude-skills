# Naming Conventions

## General Naming

| Thing | Convention | Example |
|-------|-----------|---------|
| Namespace | All lowercase | `vendor\pluginhandle` |
| Class | StudlyCase | `MyEntity` |
| Method | camelCase | `getEntityById()` |
| Private method | Underscore prefix | `_registerCpUrlRules()` |
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
use craftpulse\myplugin\models\MyEntity;
use craftpulse\myplugin\records\MyEntity as MyEntityRecord;
```
