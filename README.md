# Craft CMS Claude Skills

> Production-ready [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills, agents, and project templates for Craft CMS 5 development.

Built and maintained by [michtio](https://github.com/michtio). Covers both **plugin/module development** (extending Craft) and **site development** (content modeling, Twig templates, front-end architecture).

## Support

If this project saves you time, consider supporting its development:

- [GitHub Sponsors](https://github.com/sponsors/michtio)
- [Buy Me a Coffee](https://buymeacoffee.com/michtio)

## Quick Start

### 1. Install

```bash
# Claude Code Plugin (recommended)
# First time: add the marketplace, then install
/plugin marketplace add michtio/craftcms-claude-skills
/plugin install craftcms-claude-skills@craftcms-claude-skills

# Or via Vercel Skills CLI
npx skills add michtio/craftcms-claude-skills --all

# Or clone manually
git clone https://github.com/michtio/craftcms-claude-skills.git ~/.claude/craftcms-claude-skills
cd ~/.claude/craftcms-claude-skills && bash install.sh
```

### 2. Set Up Your Project

Open Claude Code in your Craft project and say:

```
Set up Claude for this Craft project
```

The `craft-project-setup` skill detects your project type (plugin, site, module) and generates a tailored `CLAUDE.md` and `.claude/rules/` directory.

### 3. Start Building

The skills trigger automatically based on what you're doing. Just describe what you need:

```
Build a blog with topics, authors, and a flexible body builder using CKEditor
```

Claude loads the right skills, follows Craft conventions, and uses the correct field handles, DDEV commands, and project config workflow.

## Example Prompts

Just describe what you need. Skills trigger automatically and produce high-quality results.

```
Plan the content architecture for a multi-language corporate site with
news, team members, office locations, and a service catalog. We need
English, German, and French with subfolder-per-language routing.
```

```
Build a custom element type for "Job Listings" with postDate/expiryDate
status, a categories relation for departments, and a CP edit page with
field layout designer.
```

```
I need a modal dialog for my Craft plugin that opens when clicking
"Add Item", shows a form with name and handle fields, POSTs to my
plugin's save action, and closes on success. Make it keyboard accessible.
```

```
Create an atomic button component that supports links, form submits,
and disabled states. It needs size variants and a loading spinner option.
```

```
Configure Redis for cache, sessions, and mutex in our Craft project.
We're running DDEV locally and deploying to a VPS with Redis installed.
```

```
Build a member area with registration, login, password reset, and
profile editing. Users should be in the "Members" group and only see
content in the gated section.
```

See [docs/prompt-guide.md](docs/prompt-guide.md) for 40+ prompts organized by task type.

## What's Inside

### Skills

| Skill | Track | Key Coverage |
|-------|-------|--------------|
| `craftcms` | Plugin | Elements, queries, services, controllers, migrations, events, GraphQL, configuration, caching, permissions, CP templates (form macros, settings, navigation), CP components (widgets, utilities, slideouts), CP UI patterns (tri-state, condition builders, asset bundles), console commands (80+ commands), debugging. 30 reference files. |
| `craft-php-guidelines` | Plugin | PHPDocs, section headers, naming, class organization, ECS/PHPStan. 5 reference files. |
| `craft-content-modeling` | Site | Sections, entry types, fields, Matrix, relations, eager loading, entrification. Reuse-first field workflow. 6 reference files. |
| `craft-site` | Site | Atomic design, component patterns, routing, Vite, auth flows, search, feeds, headless. 18 reference files + 22 plugin references. |
| `craft-twig-guidelines` | Site | Variable naming, null handling, whitespace, include isolation, Craft helpers, `collect()`. |
| `craft-garnish` | Plugin | Garnish CP JavaScript: class system, UI widgets, drag system, ARIA/focus, Craft.* pattern. 5 reference files. |
| `ddev` | Shared | Commands, services, configuration, Xdebug, site sharing, troubleshooting. |
| `craft-project-setup` | Shared | Project scaffolding, upgrade, and audit. Generates CLAUDE.md, .claude/rules/, .claude/settings.local.json (permissions). Gap analysis for existing configs. |

8 skills, 86 reference files. Skills load automatically and declare companion skills so related knowledge loads together. See [docs/skills-overview.md](docs/skills-overview.md) for the full breakdown.

### Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `craft-planner` | Opus | Decompose features into vertical slices with verification gates. Can research/audit public plugins via `gh` and `git clone`. |
| `craft-feature-builder` | Opus | Build plugin code feature by feature with automated + manual test gates |
| `craft-site-builder` | Opus | Site templates and components feature by feature with build-verify gates |
| `craft-debugger` | Sonnet | Systematic bug investigation |
| `craft-code-reviewer` | Sonnet | Full-stack review: PHP, Twig, JS, CSS, config (45 checklist items) |

Agents build feature by feature (vertical slices), not layer by layer. Tests are written alongside each layer, not batched at the end. Manual testing gates (required + optional) are identified per feature. The builder's 16 prevention rules map to the reviewer's 45 checklist items across PHP, Twig, JS, and CSS. See [docs/agents.md](docs/agents.md) for details.

### Plugin Reference Library

22 Craft plugins with detailed configuration, Twig/PHP API, and common pitfalls:

<details>
<summary>View all 22 plugin references</summary>

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
| Feed Me | craftcms | Data import from XML/JSON/CSV, CLI automation |
| Imager-X | spacecrafttechnologies | Advanced image transforms, named presets, effects |

</details>

## Documentation

| Guide | What it covers |
|-------|----------------|
| [Getting Started](docs/getting-started.md) | Installation, project setup, how skills auto-trigger, first steps |
| [Skills Overview](docs/skills-overview.md) | All 8 skills with triggers, companion skills, reference counts, boundaries |
| [Prompt Guide](docs/prompt-guide.md) | 40+ real-world prompts organized by task type |
| [Agents](docs/agents.md) | 5 agents with tools, gate patterns, composition examples |
| [Contributing](docs/contributing.md) | Adding plugin references, improving skills, reporting issues |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and configured
- [DDEV](https://ddev.com) for local Craft CMS development
- Craft CMS 5.x
- Bash (macOS/Linux) for the install script

## Roadmap

- [ ] Upgrade guide (Craft 3→4, 4→5, 3→5) with deprecated plugin mapping and migration paths
- [ ] DDEV skill expansion (Xdebug deep-dive, custom services, production parity)
- [ ] Commerce skill (products, variants, orders, carts, payments -- separate skill)
- [ ] CKEditor 4→5 migration guide (config conversion, custom styles, plugin mapping, HTML cleanup)
- [ ] More plugin references (Neo, Scout, Campaign)

## Contributing

Contributions welcome. See [docs/contributing.md](docs/contributing.md) for how to add plugin references, improve skills, and report issues.

## License

MIT -- see [LICENSE](LICENSE).
