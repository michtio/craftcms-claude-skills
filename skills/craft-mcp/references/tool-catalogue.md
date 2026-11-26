# MCP Tool Catalogue (Craft 5.12.4) [5.12+]

Every capability core Craft registers, derived from the `#[McpTool]`, `#[McpResource]`, `#[McpResourceTemplate]` and `#[McpPrompt]` attributes in [`src/mcp/capabilities/`](https://github.com/craftcms/cms/tree/5.12.4/src/mcp/capabilities). 71 tools in total: 69 on the authenticated and stdio servers, plus the 2 public-only tools.

Tool names are snake_case [changed 5.12.1]. Before 5.12.1 they were dot-separated (elements, then a dot, then list) and some clients rejected or renamed them; update notes, prompts and allowlists that use the old names. Resource and prompt names keep their hyphens (`craft-sites`, `audit-content-model`).

Ask the server rather than this list when it matters: `info_get` returns the live instructions, `tools/list` the tools this user and token can see (paginated, 50 per page).

## Contents

- [Legend](#legend)
- [Content tools](#content-tools)
- [Assets and uploads](#assets-and-uploads)
- [Schema and configuration](#schema-and-configuration)
- [System tools](#system-tools)
- [Users and permissions](#users-and-permissions)
- [Public server tools](#public-server-tools)
- [Resources and prompts](#resources-and-prompts)
- [Behaviour notes](#behaviour-notes)

## Legend

| Column | Meaning |
|---|---|
| Scope | Minimum OAuth level on HTTP: `read` (`readOnlyHint: true`), `write`, `admin` |
| Gate | `Admin` = `#[RequiresAdmin]`; `AdminChanges` = `#[RequiresAdminChanges]` (admin and `allowAdminChanges`, so gone on production); a permission handle = `#[RequiresPermission]`; blank = any user, with record-level checks inside |

## Content Tools

| Tool | Scope | Gate | Does |
|---|---|---|---|
| `info_get` | read | `accessCp` | Craft info and full MCP instructions; clients should call it first |
| `elements_schema` | read | `accessCp` | Criteria, attributes and duplication modes for an element type |
| `elements_list` | read | | List entries, assets, users or addresses |
| `elements_get` | read | | One element by ID or UID (a saved draft's own ID loads the draft) |
| `elements_field_schema` | read | | Writable custom-field JSON Schema for an element or a new one |
| `elements_validate` | read | | Validate under live rules without saving |
| `elements_create` | write | | Create an element; `asUnpublishedDraft` for entries |
| `elements_update` | write | | Update an element or a saved draft |
| `elements_delete` | write | | Soft delete unless `hardDelete` |
| `elements_restore` | write | | Restore a soft-deleted element |
| `elements_duplicate` | write | | Duplicate as independent content |
| `search_query` | read | | Craft search syntax across element types |
| `drafts_list` | read | | Drafts of an element |
| `drafts_create` | write | | Draft of an existing element |
| `drafts_apply` | write | | Apply a draft |
| `drafts_delete` | write | | Delete a draft |
| `revisions_list` | read | | Revisions of an element |
| `revisions_get` | read | | One revision |
| `revisions_apply` | write | | Revert to a revision |
| `structures_move_element` | write | | Move an element within a structure |
| `preferences_get` | read | `accessCp` | The user's CP language and formatting locale |
| `preferences_update` | write | `accessCp` | Change them |

## Assets and Uploads

| Tool | Scope | Gate | Does |
|---|---|---|---|
| `assets_create` | write | | Create an asset from a file reference into `folderId`, `volumeId`, or an Assets field's default location (`fieldId` + `elementId`) [5.12.1+] |
| `assets_replace` | write | | Replace an asset's file, keeping ID and references |
| `assets_upload_url` | write | | Single-use upload URL for a local or large file [5.12.1+] |
| `assets_transform_url` | read | | Transformed URL by handle or inline params |
| `asset_folders_list` | read | | Folders; `criteria.parentId: null` lists volume roots [5.12.1+] |
| `asset_folders_get` | read | | One folder |
| `asset_folders_create` | write | | Create a folder |
| `asset_folders_update` | write | | Rename a folder |
| `asset_folders_delete` | write | | Permanently delete a folder, subfolders and their asset records (not restorable) |

File references for `assets_create` / `assets_replace` [changed 5.12.1]: an HTTPS download URL (private-network addresses rejected, every redirect hop re-checked, up to 3 redirects, no `file_id` needed any more), base64 data, a local absolute path (stdio only), or an `upload_id` from `assets_upload_url`. Before 5.12.1: download URLs only.

`assets_upload_url` returns `upload_id`, `upload_url`, `method`, `expires_at` (15 minutes) and `max_size`. PUT the raw bytes to `upload_url` (it carries a single-use token, so it works without the bearer token and while offline), then pass `upload_id`. Over stdio the URL is built from the site's base URL, which must be absolute. Upload URLs answer with JSON errors [5.12.2+] and work on load-balanced sites [5.12.2+]; before 5.12.2 an upload could land on a different node than the tool call. Asset URLs in tool results are absolute [5.12.2+].

## Schema and Configuration

Configuration types: `sections`, `entry-types`, `fields`, `volumes`, `sites`, `site-groups`, `user-groups`, `image-transforms`, `routes`.

| Tool | Scope | Gate | Does |
|---|---|---|---|
| `configuration_schema` | read | Admin | Types, operations and input schemas |
| `configuration_list` | read | Admin | Records of one type, each with its `revision` [5.12.1+] |
| `configuration_get` | read | Admin | One record with its `revision` [5.12.1+] |
| `configuration_create` | admin | AdminChanges | Create a record |
| `configuration_update` | admin | AdminChanges | Update supplied attributes; `expectedRevision` [5.12.1+] |
| `configuration_delete` | admin | AdminChanges | Delete with the type's content effects; `expectedRevision` [5.12.1+] |
| `users_field_layout_get` | read | Admin | User field layout |
| `users_field_layout_update` | admin | AdminChanges | Update it |
| `addresses_field_layout_get` | read | Admin | Address field layout |
| `addresses_field_layout_update` | admin | AdminChanges | Update it |
| `content_model_audit` | read | Admin | Unused fields and entry types, empty sections, duplicate field candidates, images missing alt text |

**`expectedRevision`** [5.12.1+]: pass the `revision` you last read or wrote to `configuration_update` / `configuration_delete`. If the record changed since, nothing is changed and the call fails; read again and redo the change. Without it, newer changes can be overwritten. Writes go through project config like CP edits, so commit the resulting `config/project/` YAML.

## System Tools

| Tool | Scope | Gate | Does |
|---|---|---|---|
| `project_config_get` | read | Admin | A loaded or external project config value |
| `project_config_status` | read | Admin | Pending YAML changes and write issues |
| `project_config_diff` | read | Admin | Diff of pending YAML changes (sensitive values redacted) |
| `project_config_apply` | admin | AdminChanges | Apply YAML to the database |
| `project_config_write` | admin | AdminChanges | Write loaded config to YAML, overwriting files |
| `project_config_rebuild` | admin | Admin | Rebuild from the database (not gated on `allowAdminChanges`) |
| `plugins_list` | read | Admin | Plugins, versions, license and update status |
| `plugins_install` | admin | AdminChanges | Install a Composer-installed plugin |
| `plugins_enable` | admin | AdminChanges | Enable a plugin |
| `plugins_disable` | admin | AdminChanges | Disable a plugin |
| `plugins_uninstall` | admin | AdminChanges | Uninstall, removing its data |
| `system_status_get` | read | Admin | Whether the system is live |
| `system_status_enable` | admin | AdminChanges | Turn the system on |
| `system_status_disable` | admin | AdminChanges | Turn it off |
| `caches_list` | read | `utility:clear-caches` | Clearable caches |
| `caches_clear` | write | `utility:clear-caches` | Clear some or all caches |
| `queue_status` | read | `utility:queue-manager` | Jobs with status and progress |
| `queue_run` | write | `utility:queue-manager` | Run waiting jobs for up to `maxSeconds` |
| `queue_retry_all` | write | `utility:queue-manager` | Retry failed jobs |
| `queue_release_all` | write | `utility:queue-manager` | Remove waiting and failed jobs |

## Users and Permissions

All need `assignUserPermissions`.

| Tool | Scope | Extra gate | Does |
|---|---|---|---|
| `user_permissions_list` | read | | Known permissions by category |
| `user_permissions_user_get` | read | | Effective permissions plus `directPermissions` |
| `user_permissions_group_get` | read | | A group's permissions |
| `user_permissions_user_set` | write | | Replace a user's direct permissions (send the full list) |
| `user_permissions_user_update` | write | | Add and remove specific direct permissions [5.12.1+] |
| `user_permissions_group_set` | admin | AdminChanges | Replace a group's permissions |
| `user_permissions_group_update` | admin | AdminChanges | Add and remove specific group permissions [5.12.1+] |

Prefer the `_update` tools: `_set` replaces the whole list. The permission tools reject unknown permissions [changed 5.12.1]; before 5.12.1 they ignored them, and saving over stdio could drop permissions that weren't registered in that request.

## Public Server Tools

Only on the public server, and only once approved in Settings → MCP:

| Tool | Does |
|---|---|
| `craft_context_get` | Approved query types, criteria, sites, sections, volumes, user groups and element types |
| `craft_query` | Query approved element types with element query criteria; 25 results by default, max 100 |

## Resources and Prompts

| Name | URI | Gate |
|---|---|---|
| `craft-sites`, `craft-sites-get` | `craft://sites`, `craft://sites/{site}` | Admin |
| `craft-sections`, `craft-sections-get` | `craft://sections`, `craft://sections/{section}` | Admin |
| `craft-entry-types`, `craft-entry-types-get` | `craft://entry-types`, `craft://entry-types/{entryType}` | Admin |
| `craft-entry-types-field-layout` | `craft://field-layouts/entry-types/{entryType}` | Admin |
| `craft-fields`, `craft-fields-get` | `craft://fields`, `craft://fields/{field}` | Admin |
| `craft-user-groups`, `craft-user-groups-get` | `craft://user-groups`, `craft://user-groups/{group}` | Admin |
| `craft-user-permissions` | `craft://user-permissions` | `assignUserPermissions` |
| `craft-element-types`, `craft-element-types-get` | `craft://element-types`, `craft://element-types/{type}` | `accessCp` |
| `craft-entries-get` | `craft://entries/{id}/sites/{siteId}` | |
| `craft-assets-get` | `craft://assets/{id}/sites/{siteId}` | |
| `craft-addresses-get` | `craft://addresses/{id}/sites/{siteId}` | |
| `craft-users-get` | `craft://users/{user}` | `viewUsers` |
| Prompt `audit-content-model` | | Admin |

Resources and prompts need `mcp:read` on HTTP; `Admin`-gated ones need `mcp:admin`.

## Behaviour Notes

- **`fields` argument** on list/get tools: `null` returns all non-nested custom fields [5.12.1+]; dot paths such as `blocks.innerBlocks` include nested elements' fields as summaries [5.12.1+]; `addresses` returns users' addresses [5.12.1+].
- Only fields the element's field layout conditions show are returned or writable.
- `postDate` and `expiryDate` can be set [5.12.1+]; CKEditor values aren't empty arrays any more [5.12.1+].
- Tools that declare an `outputSchema` fail if their structured result doesn't match it (`mcp/sdk` 0.9) [5.12.1+].
- Only sensitive settings are redacted, not all field and project config settings [changed 5.12.1].
- Categories, tags and global sets aren't exposed.
