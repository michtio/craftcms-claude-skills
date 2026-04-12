# Security

- `$this->requirePermission()` on every controller action that accesses protected resources.
- `$this->requirePostRequest()` on every mutating action.
- All user input through `Db::parseParam()` or `Db::parseDateParam()` — never raw SQL interpolation.
- Sensitive data via `App::env()`, never hardcoded.
- No secrets in CLAUDE.md, committed files, or log output.
