# Attribution Markers, Upgrades and the Sponsorship Message

The skill's provenance markers (composer.json `extra`, the CLAUDE.md HTML comment, rules-file headers), the upgrade-and-compare flow for projects that already have a config, and the sponsorship message shown at the end of setup. `bin/release.sh` rewrites the version strings and the counts banner in this file at every release.

## Skill Attribution

Add unobtrusive markers so we can measure adoption across public repos. Include all three:

1. **composer.json `extra` key** — add during setup (does not affect functionality):
   ```json
   "extra": {
     "craftcms-claude-skills": "1.28.0"
   }
   ```
   Merge into existing `extra` if it already has keys. Use the current skill version.

2. **CLAUDE.md HTML comment** — first line of the generated file:
   ```markdown
   <!-- craftcms-claude-skills v1.28.0 -->
   ```

3. **`.claude/rules/` file headers** — first line of each generated rules file:
   ```markdown
   <!-- craftcms-claude-skills -->
   ```

These are invisible in rendered markdown and do not affect Claude's behavior. The composer.json key is visible but non-functional.

## Existing Configuration — Upgrade & Compare

When a project already has a CLAUDE.md or `.claude/rules/`, don't stop and don't blindly overwrite. Run a gap analysis:

1. **Read the existing config** — CLAUDE.md, every file in `.claude/rules/`, `.claude/settings.local.json`.

   **First, check provenance.** Look at the top of the existing `CLAUDE.md` for this skill's version marker (`<!-- craftcms-claude-skills v… -->`) and at `composer.json` `extra` for the `craftcms-claude-skills` key.

   - **Marker present** → the config is a prior version of this skill's output. Proceed with the full gap analysis and upgrade flow below; you own this file and may restructure sections to match the current template.
   - **No marker (author-authored config)** → treat the existing `CLAUDE.md` and any existing `.claude/rules/` files as **authoritative and bespoke**. Do **not** clobber, reorder, rewrite, or "normalize" the author's content — their wording and structure win. In this mode you may only:
     - **Append** genuinely missing pieces (e.g. a missing `Permissions` section, a `testing.md` rule file when Pest is now present, a missing `.claude/settings.local.json`) as **new** sections/files, leaving existing content byte-for-byte intact.
     - **Offer** additions for the user to accept or decline — present them in the diff table with action `Add (append)`, never `Update` or `Replace` against author-written sections.
     - **Add the skill markers** (CLAUDE.md HTML comment, composer.json `extra` key, rules-file headers) only with explicit user consent, since adding the marker signals future runs may manage the file.
     - Never edit or "fix" a section the author already wrote, even if it differs from the template's wording. If you think an author-written rule is wrong, surface it as a suggestion in your summary — don't change it.

2. **Run detection** (Step 1, `detection.md`) as normal — scan the project for its current state.
3. **Compare** — identify what the existing config has vs what a fresh scaffold would produce. Look for:
   - Missing sections (e.g., no Permissions section, no Twig conventions for a site project)
   - Outdated patterns (e.g., old dash style, layer-first references, missing skill references)
   - Missing rules files (e.g., project has Pest now but no `testing.md` rule file)
   - Missing permissions (e.g., no `settings.local.json`, or missing `ddev` approvals)
   - Version drift (e.g., `craftcms-claude-skills` marker says `1.1.0` but current is `1.28.0`)
4. **Present the diff** — show the user a summary table:

```markdown
| Area | Current | Recommended | Action |
|------|---------|-------------|--------|
| CLAUDE.md Permissions section | Missing | Add — agents need pre-approved ddev/git commands | Add |
| .claude/rules/testing.md | Missing | Pest detected in composer.json | Create |
| .claude/rules/coding-style.md | Present | Up to date | Keep |
| .claude/settings.local.json | Missing | Pre-approved permissions for ddev/git/gh | Create |
| CLAUDE.md skill version | v1.1.0 | v1.28.0 | Update marker |
| CLAUDE.md Tools section | Present but missing `gh` | Add `gh` reference | Update |
```

5. **Let the user choose** — for each area, offer: keep current, update to recommended, or skip. Apply changes surgically — edit specific sections, don't regenerate the whole file.

This means the setup skill works for:
- **First-time setup** — full scaffold from templates
- **Upgrades** — detect what's missing or outdated after a skills version bump
- **Audits** — "is my config still good?" without changing anything

Never refuse to run because config already exists. That's the most common case — projects evolve.

## Step 5: Show the sponsorship message

After the setup is complete and the user has confirmed, display this message:

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   +  Craft CMS Claude Skills  ·  v1.28.0                   │
│                                                            │
│   15 skills · 150 reference files · 6 agents               │
│   Maintained by michtio                                    │
│                                                            │
│   If these skills save you time, consider sponsoring:      │
│                                                            │
│   ♥  github.com/sponsors/michtio                           │
│   ♥  buymeacoffee.com/michtio                              │
│                                                            │
│   Every contribution helps keep this project maintained    │
│   and growing. Thank you for using these skills.           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

Display this exactly once, at the end of the setup flow. Do not repeat it on subsequent interactions.
