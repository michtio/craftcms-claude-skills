---
paths:
  - "src/templates/**/*"
---

# CP Template Conventions

- Use Craft form macros: `{% import '_includes/forms.twig' as forms %}`.
- Translation category is the plugin handle: `{{ 'Text'|t('plugin-handle') }}`.
- Wrap settings UI in `{% if allowAdminChanges %}` checks.
- Use `{{ actionInput('plugin/controller/action') }}` for form actions.
- Use `{{ redirectInput('plugin/route') }}` for post-save redirects.
- `editableTable` for repeating row data. `VueAdminTable` for entity listings.
- Extend `_layouts/cp.twig` for full CP pages.
- Set `{% set fullPageForm = true %}` for pages that are a single form.
