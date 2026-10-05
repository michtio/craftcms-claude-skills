# Contributing

Contributions are welcome. This page covers how to add plugin references, improve existing skills, report issues, and follow the conventions that keep the skill pack consistent.

By participating you agree to the [Code of Conduct](../CODE_OF_CONDUCT.md). For anything security-sensitive, follow the [Security Policy](../SECURITY.md) instead of filing a public issue.

## Adding a New Plugin Reference

Plugin references live in `skills/craft-plugins/references/`. Each file documents one Craft plugin with enough detail for Claude to use it correctly across templates, configuration, PHP/migrations, and deployment. Register the new reference in the `craft-plugins` skill's routing table (`skills/craft-plugins/SKILL.md`) and add its trigger name to that skill's `description`.

### Required sections

Every plugin reference must include these sections in this order:

```markdown
# Plugin Name

> One-line description of what the plugin does.

- **Plugin:** vendor/plugin-handle
- **Documentation:** https://...
- **Minimum Craft:** 5.x

## Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Twig API](#twig-api)
- [Common Pitfalls](#common-pitfalls)

## Installation

`ddev composer require vendor/plugin-handle`

Any post-install steps (settings, config files, migrations).

## Configuration

Key settings with code examples. Environment-specific config if applicable.
Show the config file format (e.g., `config/plugin-handle.php`).

## Twig API

The template-facing API. Include real code examples for the most common
use cases. Use Craft's Twig conventions (camelCase variables, ?? null
handling, only on includes).

## Common Pitfalls

Numbered list of mistakes developers make with this plugin. Each pitfall
should explain what goes wrong and how to fix it. These are high-value --
Claude uses them to avoid known issues proactively.
```

### Optional sections

- **GraphQL** -- if the plugin exposes a GraphQL API
- **Events** -- if the plugin fires events that other plugins can listen to
- **Console Commands** -- if the plugin adds CLI commands
- **Migration from X** -- if the plugin replaces another (e.g., CKEditor replacing Redactor)
- **Compatibility** -- interactions with other plugins (Blitz, SEOMatic, Sprig)

### Style guidelines for references

- Use `ddev composer require` for install commands, never bare `composer require`
- Include the Craft minimum version when it matters
- Code examples should be complete enough to copy-paste, not abstract pseudocode
- Document the Twig API with real field handles and entry queries, not `{{ someField }}`
- Every pitfall should have a "wrong" and "right" pattern

### Updating the SKILL.md after adding a reference

After adding a new plugin reference, update `skills/craft-plugins/SKILL.md`:

1. Add a row to the plugin references table with the reference path (`references/plugin-x.md`), plugin name, author, and key surface area
2. Add its trigger name to the skill's `description` frontmatter so prompts naming the plugin route to it
3. Update the README.md and `docs/skills-overview.md` plugin reference counts if they changed

## Improving an Existing Skill

### What to check before submitting

1. **Accuracy** -- verify claims against Craft's source code or official docs. Reference files should be source-validated, not based on memory or outdated blog posts.
2. **Completeness** -- check the Table of Contents against the actual content. Are there sections promised but missing? Methods listed but not explained?
3. **Pitfalls** -- the "Common Pitfalls" section is the highest-value part of any reference file. If you've hit a real issue that's not documented, adding it helps everyone.
4. **Cross-references** -- when content in one file relates to another, add a cross-reference. Use bare filenames: "See `elements.md`" not "See `references/elements.md`".
5. **Line count** -- reference files over 500 lines should be considered for splitting. Check the CHANGELOG for examples of how splits were done (e.g., `config-general.md` split into two files at 431 lines each).

### Reference file conventions

**Heading hierarchy:**
```markdown
# File Title (H1, once per file)
## Major Section (H2)
### Subsection (H3)
#### Detail (H4, rare)
```

**Table of Contents** -- files over 200 lines should have a TOC after the introduction. Use descriptive format:
```markdown
## Contents

- [Section Name](#section-name) -- what this section covers
- [Another Section](#another-section) -- what this covers
```

**Code examples** -- every concept should have a code example. Prefer complete, copy-pasteable examples over fragments.

**Common Pitfalls format:**
```markdown
## Common Pitfalls

1. **Short description of the mistake** -- explanation of what goes wrong and how to fix it. Include wrong/right code when applicable.
```

**Cross-references** -- use bare filenames: `elements.md`, `controllers.md`. Not full paths.

**Documentation links** -- include official doc URLs at the top of each reference file when relevant.

### Updating the SKILL.md after changing a reference

If you add, remove, or rename a reference file:

1. Update the reference table in the skill's `SKILL.md`
2. Update any task routing examples that reference the file
3. If the line count changed significantly, update the README's skill description

## Skill Frontmatter

Every `skills/*/SKILL.md` opens with a YAML frontmatter block, and it's checked before every release:

- **`description`** -- required, 1-1024 characters (the [Agent Skills spec](https://agentskills.io/specification) limit).
- **`when_to_use`** -- optional. It's a Claude Code field, appended to the description in the skill listing. The combined text (`description + " - " + when_to_use`) must stay at or under 1536 characters, or Claude Code truncates it in the listing.
- **YAML string escaping** -- double-quoted frontmatter strings follow strict YAML escaping rules. A bare backslash escape that isn't valid YAML (e.g. `\u` outside a proper `\uXXXX` sequence) fails to parse even though it looks harmless in a plain-text editor.

Run the validator before opening a PR:

```bash
bash bin/validate-skills.sh
```

It parses every skill's frontmatter as strict YAML, rejects unknown keys, confirms `name` matches the skill's directory, and enforces both length limits above. `bin/release.sh` runs it automatically and refuses to release on failure.

## Release Process

Releases are cut with `bin/release.sh <version>`, e.g. `bin/release.sh 1.19.0`. It:

1. Runs `bash bin/validate-skills.sh` and aborts if any SKILL.md frontmatter fails.
2. Bumps the version in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
3. Bumps the user-facing version strings and the skill/reference-file/agent counts in the `craft-project-setup` sponsorship banner.
4. Stamps the matching CHANGELOG heading with today's date.

Before running it, write the CHANGELOG entry under a heading of the exact form `## X.Y.Z -- ` (two hyphens and a trailing space, no date yet) -- the stamping step only matches a heading written that way.

The script only edits files -- it does not commit, tag, or push. Review the diff, then:

```bash
git add .claude-plugin/ CHANGELOG.md
git commit -m "chore(release): v1.19.0"
git tag -a v1.19.0 -m "v1.19.0"
git push origin main v1.19.0
```

The `release-validation` GitHub Actions workflow fires on the tag push, confirms the manifest versions match the tag, and publishes the GitHub Release itself from the CHANGELOG section. **Never create the GitHub Release by hand** -- let the workflow do it, or the release notes will drift from what's actually tagged.

## Token Budget

Skill content loads into context whenever it triggers, so size is a real cost. Measure before and after a content change:

```bash
uv run --with tiktoken python3 evals/measure_tokens.py
```

It reports per-file and per-skill token counts (via tiktoken's `cl100k_base` encoding, the closest public approximation to Claude's tokenizer), separating the always-loaded listing cost (description + `when_to_use`, paid every session regardless of whether the skill triggers) from the on-demand cost (SKILL.md body plus references), and also covers agent preload costs. Run it before and after your change and compare against the latest `evals/snapshot-*.json` to see whether the change grew the budget meaningfully.

## Reporting Issues

> **Security issues don't go here.** If a skill would lead an agent to do something destructive or leak data, or a code example carries a real vulnerability, use [private vulnerability reporting](https://github.com/michtio/craftcms-claude-skills/security/advisories/new) instead. See the [Security Policy](../SECURITY.md) for scope.

### Bug reports

File a GitHub issue with:

- **What you asked Claude** -- the exact prompt
- **What happened** -- the incorrect output or behavior
- **What should have happened** -- the expected output
- **Which skill triggered** -- if visible in the status bar
- **Craft version** -- e.g., Craft 5.6.2

The most useful bug reports include the actual prompt and the actual wrong output. "It didn't work" is not actionable.

### Common issue categories

- **Wrong skill triggered** -- a prompt about Twig templates loaded `craftcms` instead of `craft-site`. This is a trigger keyword issue.
- **Outdated information** -- a reference file documents Craft 4 behavior that changed in Craft 5. Include the correct behavior and a source (doc URL, source code link).
- **Missing coverage** -- a Craft feature or pattern is not covered by any skill. Describe the feature and which skill it should belong to.
- **Cross-skill conflict** -- two skills give contradictory advice for the same scenario. Include both outputs.

### Feature requests

For new reference files, plugin references, or agent improvements:

- Describe the use case -- what you're trying to do
- Explain why existing coverage is insufficient
- Suggest which skill should own it
- If proposing a new plugin reference, confirm the plugin has a stable release for Craft 5

## Code Style for Reference Files

### Consistency checklist

Before submitting a PR that modifies reference files:

- [ ] Heading hierarchy is correct (H1 once, H2 for sections, H3 for subsections)
- [ ] Table of Contents present for files over 200 lines
- [ ] Common Pitfalls section exists and has at least 3 entries
- [ ] Code examples use Craft 5 APIs (not Craft 3/4 patterns)
- [ ] Code examples use `ddev` commands, not bare `php`/`composer`/`npm`
- [ ] Cross-references use bare filenames
- [ ] Documentation links are current (Craft 5.x, not 4.x)
- [ ] No duplicate content that exists in another reference file -- cross-reference instead
- [ ] Line count is reasonable (under 500 lines per file; split if larger)
- [ ] SKILL.md reference table updated if files changed
- [ ] README.md updated if skill-level changes were made
- [ ] `bash bin/validate-skills.sh` passes if any SKILL.md frontmatter changed

### What makes a good PR

- **Before/after examples** for skill improvements -- show what Claude produced before your change and what it produces after
- **Source validation** -- reference a specific Craft source file, doc page, or tested behavior
- **Focused scope** -- one skill or reference file per PR. Cross-cutting changes should explain why they span multiple files.
