# Security

- `$this->requirePermission()` on every controller action that accesses protected resources.
- `$this->requirePostRequest()` on every mutating action.
- `$this->requireAdmin(requireAdminChanges: true)` for settings that modify project config.
- All user input through `Db::parseParam()` or `Db::parseDateParam()` — never raw SQL interpolation.
- Sensitive data (API keys, webhook secrets) via `App::env()`, never hardcoded.
- No secrets in CLAUDE.md, committed files, or log output.
- Per-resource permission scoping: `"{{pluginHandle}}:action-name:{$entityUid}"`.
- Element authorization via `canView()`, `canSave()`, `canDelete()` on element classes.
