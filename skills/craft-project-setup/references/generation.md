# Generating the Configuration

Steps 3 and 3b of the setup workflow in full: which files to generate from `templates/` and which to write from project context, the `.claude/settings.local.json` permission set (base, plugin, connected projects, research folder), and the universal defaults every generated `CLAUDE.md` carries.

## Step 3: Generate the configuration

Generate `CLAUDE.md` and `.claude/rules/` files. Two sources:

1. **From templates** — files in `templates/{type}/` are starting points. Replace placeholders (`{{pluginHandle}}`, `{{vendorNamespace}}`, `{{pluginName}}`, `{{composerName}}` = the composer.json `name`, e.g. `acme/my-plugin`), customize based on detection results. These exist and are ready to use.
2. **Generated from context** — files not in `templates/` must be written from scratch based on the project's actual setup. Use the skill references, detection results, and user answers to produce these. Don't skip a file just because no template exists.

Before generating, **verify which templates exist** for the detected project type:

```bash
ls templates/{type}/.claude/rules/
ls templates/{type}/.claude/settings.local.json
```

For any file listed below that doesn't have a template, generate it from the project context and skill knowledge. Flag to the user: "These files were generated from your project's conventions (no starter template exists): [list]."

**File structure to generate:**

```
CLAUDE.md                          # Project overview, commands, structure
.claude/
  settings.local.json             # Pre-approved permissions (gitignored) — generate from Step 3b
  rules/
    coding-style.md               # PHP conventions (plugin/module) — template
    architecture.md               # Architecture patterns (plugin/module) — template
    templates.md                  # Twig conventions (site) — template
    git-workflow.md               # Commit conventions (all) — template
    scaffolding.md                # Generator commands (plugin/module) — template
    security.md                   # Security rules (all) — template
    testing.md                    # Test conventions (if Pest exists) — generate from project's test setup
    migrations.md                 # Migration rules (plugin/module) — generate from project conventions
```

## Step 3b: Generate permissions

Generate `.claude/settings.local.json` with pre-approved permissions for commands the agents run repeatedly. Without this, every `ddev composer check-cs` or `ddev craft up` triggers a permission prompt, breaking the autonomous flow.

```json
{
  "permissions": {
    "allow": [
      "Bash(ddev composer *)",
      "Bash(ddev craft *)",
      "Bash(ddev npm *)",
      "Bash(ddev exec *)",
      "Bash(ddev ssh)",
      "Bash(ddev start)",
      "Bash(ddev stop)",
      "Bash(ddev restart)",
      "Bash(ddev describe)",
      "Bash(ddev logs *)",
      "Bash(ddev import-db *)",
      "Bash(ddev export-db *)",
      "Bash(ddev xdebug *)",
      "Bash(git status *)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git add *)",
      "Bash(git branch *)",
      "Bash(gh *)"
    ]
  }
}
```

Use `.claude/settings.local.json` (not `settings.json`) — local settings are gitignored by default, so each developer can adjust permissions without affecting the team. Note this in the generated CLAUDE.md under a "Permissions" section.

For **plugin projects**, also add read access to the Craft installation where the plugin is tested:

```json
"Bash(tail *storage/logs/*)"
```

### Connected projects

After generating the base permissions, ask: **"Are there connected projects or folders Claude should have access to?"**

Common patterns:

| Scenario | Example paths | What to add |
|----------|--------------|-------------|
| Plugin dev with test site | `/path/to/craft-site/` (the Craft install where the plugin is symlinked) | Read/write on the site's `vendor/`, `storage/logs/`, `config/` |
| Headless frontend | `/path/to/frontend/` (Next.js, Nuxt, Astro alongside Craft backend) | Read on the frontend project for cross-referencing GraphQL queries |
| Multi-repo site | `/path/to/shared-modules/` (shared modules repo) | Read/write on the shared repo |
| Monorepo packages | Already covered — everything is in the same working directory | No extra paths needed |

If the user identifies connected paths, add them to `settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Read(/path/to/connected-project/**)",
      "Edit(/path/to/connected-project/**)",
      "Bash(tail */path/to/connected-project/storage/logs/*)"
    ]
  }
}
```

If the user says no connected projects, skip this. Don't press — it's an advanced concern and many projects are self-contained.

### Research folder permissions

Always add permissions for the dev root's research folder — the planner uses it to clone and audit public plugins:

```json
"Bash(git clone * {devRootPath}/research/*)",
"Bash(gh repo view *)",
"Bash(gh api *)",
"Read({devRootPath}/research/**)",
"Bash(rm -rf {devRootPath}/research/*)"
```

Replace `{devRootPath}` with the actual path. The research folder is ephemeral — clones are shallow (`--depth 1`) and cleaned up after planning.

## Universal Defaults

Every generated CLAUDE.md includes these rules regardless of project type. These are baseline expectations for professional Craft CMS work:

```markdown
## General

Be critical. We're equals — push back when something doesn't make sense.

Do not excessively use emojis.

Do not include AI attribution in commits, PR descriptions, PR comments, issue comments, or generated code. Many clients and enterprises remain skeptical of AI-generated work, so all output should be indistinguishable from human-authored work.

Do not include "Test plan" sections in PR descriptions.
```

```markdown
## Tools

Use `ddev` shorthand commands: `ddev composer`, `ddev craft`, `ddev npm`. Never run `php`, `composer`, or `npm` on the host — everything goes through DDEV.

Use `gh` for all GitHub operations — it's already authenticated.

## Paths

- **Dev root**: `{devRootPath}` — parent folder for all projects. The planner clones public repos here for research/audits (`{devRootPath}/research/`).
- **Research folder**: `{devRootPath}/research/` — ephemeral. Shallow clones for plugin audits and pattern research. Cleaned up after use.

## Permissions

`.claude/settings.local.json` pre-approves DDEV and git commands so agents run without permission prompts. This file is gitignored — each developer can adjust it locally. If commands are being blocked, check this file first.
```
