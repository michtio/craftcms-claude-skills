# Getting Started

This guide walks you through installing the Craft CMS Claude Skills, setting up your first project, and understanding how skills work together.

## Installation

Three installation methods are available. Choose whichever fits your workflow.

### Claude Code Plugin (recommended)

The plugin system handles versioning and updates automatically.

```bash
# First time only: register the marketplace
/plugin marketplace add michtio/craftcms-claude-skills

# Install the skill pack
/plugin install craftcms-claude-skills@michtio/craftcms-claude-skills
```

After installation, skills are available in every Claude Code session. Updates arrive via `/plugin update`.

### Vercel Skills CLI

If you use the Vercel Skills CLI for managing skills across projects:

```bash
npx skills add michtio/craftcms-claude-skills --all
```

This installs all 8 skills and 5 agents. You can also install individual skills by name if you only need a subset.

### Manual (git clone)

For contributors or anyone who wants to inspect the source:

```bash
git clone https://github.com/michtio/craftcms-claude-skills.git ~/.claude/craftcms-claude-skills
cd ~/.claude/craftcms-claude-skills && bash install.sh
```

The install script symlinks skill and agent definitions into the correct directories. Run it again after pulling updates.

## Project Setup

Once the skills are installed globally, each Craft project needs its own `CLAUDE.md` and `.claude/rules/` directory. The `craft-project-setup` skill handles this automatically.

### Running the setup

Open Claude Code inside your Craft project directory and say:

```
Set up Claude for this Craft project
```

The skill reads your project to determine what you're building:

| What it checks | What it infers |
|----------------|----------------|
| `composer.json` type field | Plugin, module, or site project |
| `.ddev/config.yaml` | PHP version, database, project name |
| `templates/` directory | Site templates exist |
| `config/project/` directory | Craft project config present |
| `modules/` directory | Custom modules alongside site |
| `package.json` | CSS framework, build tools |

It then asks 3-5 clarifying questions (plugin handle, CSS framework, tooling confirmation) and generates:

- **`CLAUDE.md`** -- project-specific conventions, commands, structure overview
- **`.claude/rules/`** -- coding standards, architecture rules, security, git workflow, and more

These files are committed to your repo so every developer on the team gets the same Claude Code behavior.

### What gets generated

For a **plugin project**, you get rules for PHP conventions, architecture patterns, scaffolding commands, migration safety, and security.

For a **site project**, you get rules for Twig conventions, template architecture, content modeling, and Git workflow.

For a **hybrid project** (site with custom modules), you get both sets merged together.

The generated config references the Craft CMS skills by name so Claude Code knows which skills to load when.

## How Skills Auto-Trigger

You do not need to load skills manually in most cases. Each skill has a description with trigger keywords that Claude Code matches against your prompts. When you ask something like:

```
Build a custom element type for Job Listings with postDate/expiryDate status
```

Claude Code matches keywords like "custom element type", "postDate", and "expiryDate" against the `craftcms` skill's trigger list and loads it automatically. You see the skill name in the Claude Code status bar when it activates.

The trigger system is designed to be specific enough to avoid false positives. Each skill declares explicit "NOT for" boundaries -- for example, `craftcms` will not trigger for front-end Twig templates (that's `craft-site`), and `craft-site` will not trigger for PHP plugin development (that's `craftcms`).

## How Companion Skills Work

Skills do not exist in isolation. When one skill loads, it declares **companion skills** that should load alongside it. This happens automatically.

For example, when `craftcms` triggers:
- `craft-php-guidelines` always loads (you're writing PHP)
- `ddev` always loads (commands run through DDEV)
- `craft-garnish` loads conditionally (only when CP JavaScript is involved)

When `craft-site` triggers:
- `craft-twig-guidelines` always loads (you're writing Twig)
- `craft-content-modeling` always loads (templates depend on content structure)
- `ddev` always loads (commands run through DDEV)

This means asking a single question often loads 3-4 skills behind the scenes, giving Claude the full context it needs without you having to specify anything.

## Loading Skills Manually

If auto-triggering does not pick up the right skill (rare, but possible for ambiguous prompts), you can load a skill explicitly:

```
Load the craft-garnish skill
```

Or reference the skill by mentioning its core domain:

```
I need help with Garnish drag-sort in my plugin's CP JavaScript
```

The trigger keywords in each skill's description are tuned for natural language -- you do not need to memorize them. Just describe what you're doing with enough specificity and the right skill loads.

## First Steps

### For Plugin Developers

1. **Set up the project** -- run the project setup skill to generate `CLAUDE.md` and rules
2. **Scaffold with generators** -- ask Claude to scaffold new components:
   ```
   Scaffold a new element type called JobListing
   ```
   The `craftcms` skill knows to use `ddev craft make element` and applies the PHP guidelines automatically.
3. **Build layer by layer** -- for complex features, delegate to the `craft-feature-builder` agent. It enforces build-verify gates so each layer (migration, model, service, controller) is verified before the next starts.
4. **Review your code** -- delegate to the `craft-code-reviewer` agent for a findings report covering security, performance, and conventions.

The core skills you'll use: `craftcms`, `craft-php-guidelines`, `craft-garnish` (for CP JavaScript), and `ddev`.

### For Site Developers

1. **Set up the project** -- same as above
2. **Plan your content model** -- describe what you're building:
   ```
   Plan the content architecture for a blog with topics, authors, and a flexible body builder
   ```
   The `craft-content-modeling` skill enforces the reuse-first field workflow -- it audits your existing field pool before proposing new fields.
3. **Build templates** -- ask for specific components:
   ```
   Create an atomic button component that supports links, form submits, and disabled states
   ```
   The `craft-site` skill applies atomic design conventions, prop patterns, and Tailwind class composition.
4. **Use the site builder agent** -- for multi-template work, delegate to `craft-site-builder`. It builds atoms before molecules before organisms, verifying each layer renders before composing the next.

The core skills you'll use: `craft-site`, `craft-twig-guidelines`, `craft-content-modeling`, and `ddev`.

### For Both

- **DDEV commands only** -- never run `php`, `composer`, or `npm` on the host. Always `ddev composer`, `ddev craft`, `ddev npm`.
- **Project config workflow** -- after content model changes in the CP, always `ddev craft project-config/write` to capture changes, then commit the YAML files.
- **Agent delegation** -- for complex multi-step work, use the specialized agents (planner, builder, debugger, reviewer) rather than doing everything in a single conversation.

## Next Steps

- [Skills Overview](skills-overview.md) -- what each skill covers and when it triggers
- [Prompt Guide](prompt-guide.md) -- 40+ real-world prompts organized by task type
- [Agents](agents.md) -- when to use each agent and how they work
- [Contributing](contributing.md) -- how to improve the skills or add plugin references
