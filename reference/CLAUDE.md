# Reference — Personal CLAUDE.md

> This is a reference for your `~/.claude/CLAUDE.md`. Review and merge what
> you need into your own file. Do not copy blindly — customize to your workflow.

## General

Be critical. Don't be sycophantic. We're equals — push back when something doesn't make sense.

Always plan first, execute after. Read the actual files before making claims about them.

Do not excessively use emojis. Do not include "Test plan" sections in PR descriptions.

## Coding Standards

When working with Craft CMS plugins or modules, load the `craft-php-guidelines` skill. The full guidelines live in `~/.claude/skills/craft-php-guidelines/SKILL.md`.

PHPDocs on everything. `@author` on classes and methods only. Section headers with `=========` separators on every class. These are non-negotiable.

## Tools

Use `ddev` shorthand commands: `ddev composer`, `ddev craft`, `ddev npm`. Never run `php`, `composer`, or `npm` on the host — everything goes through DDEV.

Never install Craft plugins (`composer require`) without explicit approval. Plugin selection is a planning-phase decision — the planner agent proposes plugins, you confirm. The fewer plugins, the better.

Use `gh` for all GitHub operations — it's already authenticated. Never mention Claude Code in PR descriptions, PR comments, or issue comments.

Use `web_fetch` to read documentation URLs directly when skills don't cover a specific pattern.

## Agents

Six specialized agents, each with a dedicated model and tool scope:

- **craft-planner** (Opus) — Architecture planning, investigation. Read-only tools.
- **craft-feature-builder** (Opus) — Full implementation of new features. All tools.
- **craft-simplifier** (Opus) — Refactoring and reducing complexity. All tools.
- **craft-site-builder** (Opus) — Site templates, content architecture, components. All tools.
- **craft-debugger** (Sonnet) — Focused bug investigation and fixes. All tools.
- **craft-code-reviewer** (Sonnet) — Code review and feedback. Read-only tools.

Use Opus agents for complex, multi-file work. Sonnet agents for focused, single-concern tasks.
