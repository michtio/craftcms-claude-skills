# Craft CMS Claude Skills

> Production-ready [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills, agents, and project templates for Craft CMS 5 development.

Built and maintained by [michtio](https://github.com/michtio). Covers both **plugin/module development** (extending Craft) and **site development** (content modeling, Twig templates, front-end architecture).

## Install

Three ways to install — pick what fits your workflow:

### Method 1: Claude Code Plugin (recommended)

Register as a marketplace source, then install:

```bash
# In Claude Code
/plugin install craftcms-claude-skills@michtio/craftcms-claude-skills
```

This installs all skills and agents through Claude Code's native plugin system.

### Method 2: Vercel Skills CLI

```bash
npx skills add michtio/craftcms-claude-skills --all
```

Installs all skills via the open [Agent Skills](https://agentskills.io) ecosystem. Works with Claude Code, Cursor, Codex, and other compatible agents.

### Method 3: Git Clone

```bash
git clone https://github.com/michtio/craftcms-claude-skills.git ~/.claude/craftcms-claude-skills
cd ~/.claude/craftcms-claude-skills && bash install.sh
```

Symlinks skills and agents into `~/.claude/`. Existing skills are never overwritten.

To uninstall: `cd ~/.claude/craftcms-claude-skills && bash uninstall.sh`

## What's Inside

### Two Development Tracks

#### Plugin Development — Extending Craft

For building plugins, modules, custom element types, field types, services, controllers, migrations, queue jobs, events, and GraphQL schemas.

| Skill | Description |
|-------|-------------|
| `craftcms` | Complete extending reference — elements, queries, services, controllers, CP templates, migrations, events, GraphQL. 13 reference files. |
| `craft-php-guidelines` | PHP coding standards — PHPDocs, section headers, naming, verification checklist. |

#### Site Development — Building with Craft

For content architecture, Twig templates, atomic design, component systems, and plugin configuration.

| Skill | Description |
|-------|-------------|
| `craft-content-modeling` | Content architecture — sections, entry types, all 26 field types, Matrix, relations, eager loading, project config, strategic patterns. 3 reference files. |
| `craft-site` | Front-end Twig architecture — atomic design, component patterns, routing, image presets, Vite, JavaScript boundaries. 11 reference files + 20 plugin references. |
| `craft-twig-guidelines` | Twig coding standards — naming, null handling, whitespace, include isolation, Craft helpers, `collect()` conventions. |

#### Shared

| Skill | Description |
|-------|-------------|
| `ddev` | DDEV development environment — commands, services, configuration, Xdebug, multi-site. |

### Agents

Six specialized sub-agents with dedicated models and tool scopes:

**Plugin Development**

| Agent | Model | Purpose | Tools |
|-------|-------|---------|-------|
| `craft-planner` | Opus | Break features into scoped implementation steps | Read-only |
| `craft-feature-builder` | Opus | Build production-quality plugin code | All |
| `craft-simplifier` | Opus | Refine code for simplicity after implementation | All |
| `craft-debugger` | Sonnet | Systematic bug investigation | All |
| `craft-code-reviewer` | Sonnet | Code review with findings report | Read-only |

**Site Development**

| Agent | Model | Purpose | Tools |
|-------|-------|---------|-------|
| `craft-site-builder` | Opus | Site templates, content architecture, components | All |

### Project Template

A ready-to-use `.claude/` directory for any Craft CMS 5 plugin repository. Copy `project-template/` into your plugin repo and customize.

```
your-plugin/
├── CLAUDE.md                    # Imports rules, defines environment commands
└── .claude/
    └── rules/
        ├── architecture.md      # Service patterns, element operations, project config
        ├── coding-style.md      # PHPDocs, section headers, naming conventions
        ├── git-workflow.md      # Conventional commits, verification before push
        ├── migrations.md        # Idempotency, foreign keys, deployment safety
        ├── scaffolding.md       # ddev craft make generators
        ├── security.md          # Permissions, input sanitization, secrets
        ├── templates.md         # CP template macros, translations, admin checks
        └── testing.md           # Pest, factories, site context
```

Rules are path-scoped where appropriate — `migrations.md` only loads when editing files in `src/migrations/`, `testing.md` only in `tests/`.

### CSS Framework Note

The `craft-site` skill documents an atomic design system that assumes Tailwind CSS for class composition. **Craft CMS is unopinionated about front-end tooling** — adapt the class patterns to your CSS framework. The component architecture (props, extends/block, include with only) is framework-agnostic.

## Plugin Reference Library

The `craft-site` skill includes detailed references for 20 Craft plugins, each covering configuration, Twig/PHP API, common pitfalls, and cross-references:

<details>
<summary>View all 20 plugin references</summary>

| Plugin | Author | Key Surface |
|--------|--------|-------------|
| SEOMatic | nystudio107 | Meta cascade, JSON-LD, sitemaps, GraphQL |
| Blitz | putyourlightson | Static caching, Cloudflare, dynamic content, purgers |
| Formie | verbb | Form rendering, Tailwind theming, submissions, hooks |
| ImageOptimize | nystudio107 | Responsive images, transforms, loading strategies |
| CKEditor | craftcms | Rich text, nested entries, HTML Purifier |
| Sprig | putyourlightson | Reactive Twig components (htmx) |
| Element API | craftcms | JSON API endpoints |
| Retour | nystudio107 | Redirects, 404 tracking |
| Navigation | verbb | Menu node querying, active states |
| Hyper | verbb | Link fields, button integration |
| Colour Swatches | craftpulse | Color palettes, Tailwind class mapping |
| Password Policy | craftpulse | Validation rules, HIBP check |
| Typogrify | nystudio107 | Typography filters, widow prevention |
| Cache Igniter | putyourlightson | CDN cache warming |
| Knock Knock | verbb | Staging password protection |
| Elements Panel | putyourlightson | Debug toolbar, N+1 detection |
| Sherlock | putyourlightson | Security scanning |
| Embedded Assets | spicyweb | oEmbed as assets |
| Amazon SES | putyourlightson | SES mail transport |
| Timeloop | craftpulse | Recurring dates |

</details>

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and configured
- [DDEV](https://ddev.com) for local Craft CMS development
- Craft CMS 5.x
- Bash (macOS/Linux) for the install script

## Customization

### Personal CLAUDE.md

The installer does **not** touch your `~/.claude/CLAUDE.md`. A reference version is provided at `reference/CLAUDE.md` — review it and merge what you need.

### Project Template

Copy the project template into your plugin repository:

```bash
cp -r ~/.claude/craftcms-claude-skills/project-template/.claude /path/to/your-plugin/
cp ~/.claude/craftcms-claude-skills/project-template/CLAUDE.md /path/to/your-plugin/
```

Then customize:
- Replace `YourVendor` in `rules/coding-style.md` with your author name
- Replace `plugin-handle` in `rules/templates.md` with your plugin's handle

## Roadmap

- [ ] Additional plugin references (Neo, Imager-X, Feed Me, Commerce, Scout, Campaign)
- [ ] Twig element query reference (relatedTo patterns, cache tags)
- [ ] Multi-site patterns reference (propagation, language switchers)
- [ ] Release workflow reference (semver, changelog, CI/CD)
- [ ] Plugin Vite reference (VitePluginService, CP asset bundles)
- [ ] Hosting/deployment patterns (Craft Cloud, Servd, self-hosted)

## Contributing

Contributions are welcome. See the issue templates for guidance:

- **Skill improvements** — open a PR with before/after examples
- **New plugin references** — follow the format in `skills/craft-site/references/plugins/`
- **Bug reports** — use the bug report issue template

All contributions must maintain the A+ quality standard established across the skill library.

## License

MIT — see [LICENSE](LICENSE).
