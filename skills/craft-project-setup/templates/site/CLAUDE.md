# {{projectName}} — Craft CMS 5 Site

@.claude/rules/templates.md
@.claude/rules/git-workflow.md
@.claude/rules/security.md

## General

Be critical. We're equals — push back when something doesn't make sense.

Do not excessively use emojis. Do not include AI attribution in commits, PRs, issues, or comments.

Do not include "Test plan" sections in PR descriptions.

## Tools

Use `ddev` shorthand commands: `ddev composer`, `ddev craft`, `ddev npm`. Never run `php`, `composer`, or `npm` on the host — everything goes through DDEV.

Never install Craft plugins (`ddev composer require`) without explicit approval. Plugin selection is a planning decision.

Use `gh` for all GitHub operations.

## Environment

```bash
ddev npm run dev                     # Vite dev server
ddev npm run build                   # Production build
ddev craft up                        # Migrations + project config
ddev composer install                # Install deps (auto-runs craft up)
```

## Template Structure

```
templates/
├── _boilerplate/                # Base layouts, HTML head, critical partials
├── _atoms/                      # Smallest UI elements (buttons, links, text)
├── _molecules/                  # Composed atoms (cards, media objects)
├── _organisms/                  # Complex sections (heroes, footers, navs)
├── _views/                      # Page-level templates (entry type views)
├── _builders/                   # Content builder block renderers
└── index.twig                   # Homepage
```

## Content Model

Document the key sections, entry types, and fields here after content modeling is complete.

## Documentation

- Craft CMS Twig: https://craftcms.com/docs/5.x/development/twig.html
- Template tags: https://craftcms.com/docs/5.x/reference/twig/tags.html
- Field types: https://craftcms.com/docs/5.x/reference/field-types/
