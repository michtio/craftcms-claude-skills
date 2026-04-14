# Craft CMS Claude Skills

> Production-ready [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills, agents, and project templates for Craft CMS 5 development.

Built and maintained by [michtio](https://github.com/michtio). Covers both **plugin/module development** (extending Craft) and **site development** (content modeling, Twig templates, front-end architecture).

## Quick Start

### 1. Install

```bash
# Claude Code Plugin (recommended)
# First time: add the marketplace, then install
/plugin marketplace add michtio/craftcms-claude-skills
/plugin install craftcms-claude-skills@michtio/craftcms-claude-skills

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

## Real-World Examples

These are the kinds of prompts that trigger skills and produce high-quality results:

### Content Modeling

```
Plan the content architecture for a multi-language corporate site with
news, team members, office locations, and a service catalog. We need
English, German, and French with subfolder-per-language routing.
```

```
I need a Matrix field for page building with these block types: hero banner,
text with image, testimonial slider, CTA section, and FAQ accordion.
What entry types should I create and how should I configure the Matrix?
```

```
We're migrating from WordPress. The old site has 3 category taxonomies
and about 200 tags. What's the Craft 5 approach for taxonomies?
```

### Plugin Development

```
Build a custom element type for "Job Listings" with postDate/expiryDate
status, a categories relation for departments, and a CP edit page with
field layout designer.
```

```
Add a webhook controller to my plugin that receives POST requests from
an external API, validates the signature, and queues a sync job.
```

```
Set up Pest tests for my plugin's Items service. I need tests for
CRUD operations, validation failures, and multi-site behavior.
```

### Twig Templates

```
Create an atomic button component that supports links, form submits,
and disabled states. It needs size variants and a loading spinner option.
```

```
Build a language switcher that shows all available translations for the
current entry, falls back to the site homepage when a translation doesn't
exist, and includes proper hreflang attributes.
```

```
Set up Vite with Tailwind v4 for our Craft site, including HMR in DDEV
and production builds with content hashing.
```

### Configuration & DevOps

```
Configure Redis for cache, sessions, and mutex in our Craft project.
We're running DDEV locally and deploying to a VPS with Redis installed.
```

```
Set up a headless Craft installation with GraphQL for our Next.js frontend.
We need preview support so editors can see draft content.
```

```
Our Commerce search takes over 100 seconds on 80k entries. The queries
show LIKE '%term%' instead of MATCH/AGAINST. How do we fix the search
performance?
```

```
Set up email for production using AWS SES, but locally in DDEV we want
Mailpit to catch everything. Show me the full config for both environments.
```

```
Harden our production Craft config — disable admin changes, set up proper
CSRF for static caching with Blitz, configure trusted hosts behind our
load balancer, and disable the X-Powered-By header.
```

```
We're setting up environment variables for our staging and production
servers. What CRAFT_* variables do we need, and how does the config
priority order work between .env, general.php, and app.php?
```

## What's Inside

### Skills

| Skill | Track | Description |
|-------|-------|-------------|
| `craftcms` | Plugin | Elements, queries, services, controllers, migrations, events, GraphQL, editions, Vite, headless, testing, configuration. 17 reference files. |
| `craft-php-guidelines` | Plugin | PHPDocs, section headers, naming, class organization, enums, ECS/PHPStan, Yii2 validators, scaffolding. 5 reference files. |
| `craft-content-modeling` | Site | Sections, entry types, fields, Matrix, CKEditor, relations, eager loading, entrification, asset volumes, users/permissions, storage architecture. 4 reference files. |
| `craft-site` | Site | Atomic design, component patterns, routing, image presets, Vite, JavaScript boundaries, multi-site patterns. 12 reference files + 22 plugin references. |
| `craft-twig-guidelines` | Site | Variable naming, null handling (`??`/`???`), whitespace, include isolation, Craft helpers, `collect()`. |
| `ddev` | Shared | Commands, services, configuration, Xdebug, custom commands, troubleshooting. |
| `craft-project-setup` | Shared | Interactive project scaffolding. Generates CLAUDE.md and .claude/rules/ for plugin, site, or module projects. |

Skills load automatically when relevant. They also declare **companion skills** so related knowledge loads together (e.g., `craftcms` always loads `craft-php-guidelines` alongside it).

### Agents

Six specialized sub-agents with dedicated models and tool scopes:

| Agent | Model | Purpose |
|-------|-------|---------|
| `craft-planner` | Opus | Break features into scoped implementation steps |
| `craft-feature-builder` | Opus | Build production-quality plugin code |
| `craft-simplifier` | Opus | Refine code for simplicity after implementation |
| `craft-debugger` | Sonnet | Systematic bug investigation |
| `craft-code-reviewer` | Sonnet | Code review with findings report |
| `craft-site-builder` | Opus | Site templates, content architecture, components |

Each agent loads relevant skills automatically and enforces DDEV-only commands, symlinked plugin paths, and scoped ECS fixes.

### Plugin Reference Library

22 Craft plugins with detailed configuration, Twig/PHP API, common pitfalls, and cross-references:

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

## Project Setup

### Automatic (recommended)

Use the `craft-project-setup` skill:

```
Set up Claude for this Craft project
```

It detects your project type from `composer.json`, `.ddev/config.yaml`, and directory structure, asks a few clarifying questions, and generates:

- `CLAUDE.md` with project-specific conventions and commands
- `.claude/rules/` with coding standards, architecture rules, security, git workflow

### Manual

Copy the project template:

```bash
cp -r ~/.claude/craftcms-claude-skills/project-template/.claude /path/to/your-project/
cp ~/.claude/craftcms-claude-skills/project-template/CLAUDE.md /path/to/your-project/
```

Then customize: replace `YourVendor` with your author name and `plugin-handle` with your plugin's handle.

### CSS Framework Note

The `craft-site` skill documents an atomic design system using Tailwind CSS for class composition. **Craft CMS is unopinionated about front-end tooling.** The component architecture (props, extends/block, include with only) is framework-agnostic.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and configured
- [DDEV](https://ddev.com) for local Craft CMS development
- Craft CMS 5.x
- Bash (macOS/Linux) for the install script

## Roadmap

- [ ] More plugin references (Neo, Scout, Campaign, Commerce)
- [ ] Release workflow reference (semver, changelog, CI/CD)
- [ ] Hosting/deployment patterns (Craft Cloud, Servd, self-hosted)
- [ ] Content modeling: deeper coverage (parked for next iteration)

## Contributing

Contributions are welcome:

- **Skill improvements** -- open a PR with before/after examples
- **New plugin references** -- follow the format in `skills/craft-site/references/plugins/`
- **Bug reports** -- use the bug report issue template

## License

MIT -- see [LICENSE](LICENSE).
