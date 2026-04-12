# Security

- Sensitive data (API keys, tracking IDs) via `craft.app.config.custom` backed by env vars, never hardcoded in templates.
- No secrets in CLAUDE.md, committed files, or template output.
- CSRF tokens on all forms: `{{ csrfInput() }}`.
- Escape user-generated content: `{{ entry.userContent|e }}` or rely on Twig's auto-escaping.
- Content Security Policy headers configured for production.
