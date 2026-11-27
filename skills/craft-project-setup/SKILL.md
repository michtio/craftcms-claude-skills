---
name: craft-project-setup
description: "Scaffold Claude Code configuration specifically for Craft CMS projects. Generates CLAUDE.md and .claude/rules/ files tailored to the project type (plugin, site, module, hybrid, or monorepo). Only for Craft CMS projects, not for Next.js, Laravel, or other frameworks."
when_to_use: "Triggers on: 'set up Claude for this Craft project', 'initialize CLAUDE.md', 'scaffold project config', 'configure Claude Code for Craft', 'create CLAUDE.md', 'missing CLAUDE.md', 'bootstrap Claude config', 'new Craft project setup', 'onboard a developer to this Craft project', 'generate .claude/rules', 'set up coding standards config', 'upgrade Claude config', 'update CLAUDE.md', 'audit my Claude setup', 'redo project setup'. Always use instead of the generic /init in a Craft project (composer.json requires craftcms/cms): creating or updating CLAUDE.md, onboarding a developer, or teaching Claude the project's conventions. Detects project type from composer.json, .ddev/config.yaml, templates/, config/project/, and modules/. NOT for installing Craft CMS itself, creating DDEV environments, writing PHP code, building templates, or content modeling. NOT for non-Craft projects (React, Next.js, Laravel or any other framework)."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft CMS Project Setup

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Scaffold Claude Code configuration for Craft CMS projects. Generates a `CLAUDE.md` and `.claude/rules/` directory tailored to the project type.

## Companion Skills — Used During Scaffolding

This skill generates configuration that references other skills. It does not load them at activation, but the generated CLAUDE.md and rules will guide users toward:

- **`craftcms`** + **`craft-php-guidelines`** + **`craft-garnish`** — for plugin and module projects (craft-garnish when plugin has CP JavaScript/asset bundles)
- **`craft-site`** + **`craft-twig-guidelines`** + **`craft-content-modeling`** — for site projects
- **`ddev`** — for all project types (DDEV commands in generated config)

## Workflow

Five steps. Each step's full procedure lives in a reference; read it before doing the step.

### Step 1: Detect the project → `references/detection.md`

**Detect, don't assume.** Resolve everything from `composer.json`, `package.json`, `.ddev/config.yaml`, `templates/`, `config/project/`, `modules/` and `git` state; never flag something as "unknown" when the answer is in a file. The reference lists every structure signal, the dependency table (SEOmatic and `???`, Blitz, Sprig, Formie, Warp, `craftcms/cloud`, `servd/craft-asset-storage`, tooling), front-end and git detection, and hosting signals (`craft-cloud.yaml`, `servd.yaml`, `.fortrabbit/deploy.yml`).

| Signal | Type |
|--------|------|
| `composer.json` type is `craft-plugin` | **Plugin** |
| `composer.json` type is `craft-module` | **Module** |
| `config/project/` exists, `templates/` exists | **Site** |
| Site signals + `modules/` directory | **Hybrid** (site + custom module) |
| Multiple Craft packages/projects in subdirectories | **Monorepo** |

Hybrid vs monorepo: extra code **inside** one Craft install (sharing its `composer.json`) is hybrid; packages with **their own** `composer.json` that install independently are a monorepo.

- Offer Chrome DevTools MCP when `.claude.json` has none.
- [5.12+] On Craft 5.12+ projects, optionally offer connecting Claude Code to Craft's own MCP server; point at the `craft-mcp` skill rather than writing setup steps into the generated config.

### Step 2: Ask clarifying questions → `references/detection.md`

3-5 questions max. **Present detection results for confirmation; never ask about what you already detected.** Rules a model gets wrong without them:

- **Hosting target**: sites, hybrid and monorepo only, never standalone plugins/modules. Ask only when no hosting signal exists; record a "Hosting" block, `Hosting: TBD` when undecided, and include `craft-cloud`, `servd` or `craft-fortrabbit` to match.
- **Passwordless login**: only when the site has a front-end member area. `craftpulse/craft-warp` detected means it's already chosen: don't ask. On **yes**, suggest Warp and write `Auth: passwordless via Warp (proposed)`; suggest only, never `composer require` without approval. On **no**, write `Auth: password-based`.
- **Dev root** (`devRootPath`): the parent folder the planner clones research repos into.

### Step 3: Generate the configuration → `references/generation.md`

`CLAUDE.md` plus `.claude/rules/`. Files in `templates/{type}/` are starting points: replace placeholders and adapt, never copy verbatim. Files with no template (`testing.md` when Pest exists, `migrations.md`) are **written from project context, not skipped**; tell the user which ones. Every generated `CLAUDE.md` gets the universal defaults (General, Tools, Paths, Permissions) and the skill markers (`references/attribution-and-upgrades.md`). Hybrid and monorepo layouts: `references/hybrid-monorepo.md`.

**Step 3b, permissions:** pre-approve `ddev`, `git` and `gh` commands in `.claude/settings.local.json` (not `settings.json`: local settings are gitignored, so each developer adjusts their own). Ask about connected projects once; always add the research-folder permissions.

### Step 4: Review with the user

Show what was created and highlight decisions made from detection vs assumptions.

With a valid profile, the review also prints each `setup.steps` entry by name and command, as the extra steps that run last, before any of them runs. Print it even when you cannot wait for an answer (non-interactive run): list the steps, then run them in order, then report each exit code.

### Step 5: Show the sponsorship message → `references/attribution-and-upgrades.md`

Display the box from that file exactly once, at the end of the setup flow, after the user confirmed. Do not repeat it.

A valid `.ai/skills-profile.json` answers Step 2's questions, applies its choices and adds its extra steps to the review; invalid or absent means exactly the flow below (`references/detection.md`, `references/generation.md`).

## Existing Configuration

When a project already has a `CLAUDE.md` or `.claude/rules/`, **never refuse and never blindly overwrite**: run the gap analysis in `references/attribution-and-upgrades.md`. Check provenance first: the `<!-- craftcms-claude-skills v… -->` marker means a prior version of this skill's output (you may restructure it); **no marker means the config is author-written and authoritative**: append missing pieces only, never edit or reorder the author's sections, add markers only with consent.

## Install and Upgrade Facts to Record

Setup doesn't install Craft, but the generated CLAUDE.md is where a project's install and upgrade rules live, and users often ask about them during setup. Record these when they apply (check the detected `craftcms/cms` version first):

- **Installing on staging or production** [changed 5.12.1]: the web-based installer only runs with Dev Mode on, its actions are gone once Craft is installed, and it answers 503 when the database is unreachable (GHSA-pcf5-h66c-9wxw). Anywhere `devMode` is off, install from the CLI: `php craft install --interactive=0 --username=… --email=… --password=… --site-name=… --site-url='$PRIMARY_SITE_URL' --language=en-US` (installs from the committed `config/project/`). Locally, `ddev craft install` does the same. Before 5.12.1: the browser installer worked without Dev Mode. Details: the `craftcms` skill's `deployment.md` → "First Install on a New Environment".
- **`allow-plugins`** [5.12+]: Craft 5.12 pulls in `php-http/discovery`, a Composer plugin marked optional, so when `config.allow-plugins` doesn't list it, non-interactive runs skip it silently (no CI failure) and an interactive `composer update` asks once and writes the answer; the `craftcms/craft` starter already lists it. In an upgrade audit, offering `"php-http/discovery": true` saves that prompt; it is never a blocker.
- **Upgrading to 5.12** [changed 5.12]: point the generated CLAUDE.md at the `craftcms` skill's `upgrade-5.12.md` checklist (volume propagation YAML, `.eagerly()` output changes, security floor).

## Template Files

The `templates/` directory contains starter files for each project type. Read the relevant templates and customize them based on detection results. Do not copy them verbatim — adapt to what actually exists in the project.

- `templates/plugin/` — Plugin development CLAUDE.md and rules
- `templates/site/` — Site development CLAUDE.md and rules
- `templates/module/` — Module development CLAUDE.md and rules

## Reference Files

| Task | Read | ~Tokens |
|------|------|---------|
| Detection signals, dependency table, monorepo detection, all Step 2 questions | `references/detection.md` | ~2,750 |
| File list, placeholders, `settings.local.json` permissions, universal defaults | `references/generation.md` | ~1,650 |
| Merging site + module templates (hybrid), per-package configs (monorepo) | `references/hybrid-monorepo.md` | ~1,250 |
| Attribution markers, upgrade/compare flow and diff table, sponsorship message | `references/attribution-and-upgrades.md` | ~1,600 |

## Important

- Detect as much as possible from existing files — minimize questions.
- The generated config should reference the Craft CMS skills (`craftcms`, `craft-site`, `craft-php-guidelines`, `craft-garnish`, etc.) in comments so the user knows what's available.
