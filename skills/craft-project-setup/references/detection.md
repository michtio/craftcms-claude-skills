# Detecting the Project and Asking Questions

Steps 1 and 2 of the setup workflow in full: every file and dependency signal to read, how to tell plugin, module, site, hybrid and monorepo apart, and the short list of questions to confirm with the user. Resolve everything you can from the project's own files before asking anything.

## Step 1: Detect the project

Read the project root to determine what exists. **Detect, don't assume.** Every piece of information below should be resolved by reading actual project files — never flag something as "unknown" when the answer is in `composer.json`, `package.json`, `.ddev/config.yaml`, or `git` state.

### Project structure signals

- `.ddev/config.yaml` — DDEV project name, PHP version, database type, Node version
- `composer.json` — package type (`craft-plugin`, `craft-module`, or `project`), dependencies, scripts (check-cs, phpstan, pest)
- `src/` or `src/Plugin.php` — plugin source directory
- `templates/` — site templates
- `config/project/` — Craft project config (indicates a site)
- `config/general.php` — Craft general config
- `modules/` — custom modules
- `craft-cloud.yaml` at the repo root — **Craft Cloud project.** When present, include the `craft-cloud` skill in the generated CLAUDE.md companion-skill list and add a "Hosted on Craft Cloud" note in the generated project context. See the `craft-cloud` skill's `config-file.md` for the file's role.
- `servd.yaml` at the repo root, or `servd/craft-asset-storage` in `composer.json`, or `SERVD_PROJECT_SLUG`/`SERVD_SECURITY_KEY` env vars — **Servd project.** When present, include the `servd` skill in the generated CLAUDE.md companion-skill list and add a "Hosted on Servd" note in the generated project context. See the `servd` skill for the platform's constraints.
- `.fortrabbit/deploy.yml` (or `.yaml`, `.json`) in the repo, or `FORTRABBIT_*` variables referenced in config, or `*.frbit.app` / `ssh.<region>.frbit.app` hostnames in scripts or docs — **fortrabbit project.** When present, include the `craft-fortrabbit` skill in the generated CLAUDE.md companion-skill list and add a "Hosted on fortrabbit" note in the generated project context. See the `craft-fortrabbit` skill's `limitations.md` for the detection signals.

### Dependency detection (from composer.json `require` and `require-dev`)

Scan `composer.json` dependencies to auto-detect capabilities. Never ask the user about things you can read:

| Package | What it tells you |
|---------|------------------|
| `nystudio107/craft-seomatic` | SEOmatic installed — `???` operator is available, meta tags handled |
| `nystudio107/craft-empty-coalesce` | `???` operator available (standalone) |
| `nystudio107/craft-vite` | Vite buildchain with nystudio107 bridge |
| `putyourlightson/craft-blitz` | Static caching — affects CSRF, template caching strategy |
| `putyourlightson/craft-sprig` | Sprig/htmx available for reactive components |
| `verbb/formie` | Formie form builder installed |
| `craftcms/ckeditor` | CKEditor for rich text |
| `ether/seo` | Alternative SEO plugin (not SEOmatic) |
| `craftcms/phpstan-package` or `phpstan/phpstan` | PHPStan available |
| `symplify/easy-coding-standard` | ECS available |
| `pestphp/pest` | Pest testing framework |
| `craftpulse/craft-warp` | Warp installed — the member area is passwordless (magic links, OTP codes, passkeys). Note it in the generated CLAUDE.md and route auth work at the `craft-plugins` skill's `warp.md`; skip the passwordless question in Step 2. |
| `craftcms/cloud` | **Project hosted on Craft Cloud.** Load the `craft-cloud` companion skill; document Cloud-specific build, deploy, and runtime constraints in the generated CLAUDE.md. |
| `servd/craft-asset-storage` | **Project hosted on Servd.** Load the `servd` companion skill; document Servd's deploy workflow, ephemeral filesystem, static caching, and asset storage in the generated CLAUDE.md. |

Also check `composer.json` `scripts` section for `check-cs`, `phpstan`, `test`, `pest` commands.

### Front-end detection (from package.json, config files)

- `package.json` — Tailwind version (v3 vs v4), Alpine.js, Vue, build tool (Vite vs Webpack)
- `tailwind.config.*` or `@tailwind` in CSS files — Tailwind v3
- `@theme` in CSS files — Tailwind v4
- `vite.config.*` — Vite configuration
- `templates/_atoms/`, `_molecules/`, `_organisms/` — atomic design patterns

### Git detection

- `git branch --show-current` — current branch name
- `git remote -v` — remote URL
- `git log --oneline -10` — recent commit style (conventional commits? prefixed?)
- Default branch: check `git symbolic-ref refs/remotes/origin/HEAD` or look at branch names. Common patterns: `main`, `master`, `develop`

### Chrome DevTools MCP detection

- Check `.claude.json` for existing MCP configuration
- If not present, ask: "Would you like to install Chrome DevTools MCP for browser debugging? Enables inspecting CP templates, front-end pages, console errors, and visual testing."
- If yes: run `claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest` and note session restart is needed
- [5.12+] On Craft 5.12+ projects, optionally offer connecting Claude Code to Craft's own MCP server (off by default, enabled in Settings → MCP). Don't write setup steps into the generated config; point at the `craft-mcp` skill.

From these signals, determine the project type:

| Signal | Type |
|--------|------|
| `composer.json` type is `craft-plugin` | **Plugin** |
| `composer.json` type is `craft-module` | **Module** |
| `config/project/` exists, `templates/` exists | **Site** |
| Site signals + `modules/` directory | **Hybrid** (site + custom module) |
| Multiple Craft packages/projects in subdirectories | **Monorepo** (see below) |

### Monorepo detection

A monorepo holds **more than one independently-typed Craft package** under one repository. Confirm at least one of these signals before classifying as monorepo — a single project with a `modules/` folder is a **Hybrid**, not a monorepo:

- **Multiple `composer.json` in subtrees with Craft types.** Run `find . -name composer.json -not -path '*/vendor/*' -not -path '*/node_modules/*'` and check the `type` of each. Two or more with `craft-plugin`, `craft-module`, or `project` (in distinct directories, not the repo root alone) means monorepo.
- **Root `composer.json` with path repositories.** A root `composer.json` whose `repositories` array contains `{ "type": "path", "url": "packages/*" }` (or similar) wiring local packages together.
- **Workspace layout.** A `packages/`, `plugins/`, `apps/`, or `sites/` directory each containing its own composer-typed package, optionally with a root `package.json` declaring `workspaces`.

When unsure between hybrid and monorepo: if the extra code lives **inside** one Craft install (`modules/` under the site root, sharing its `composer.json`), it's hybrid. If each package has **its own** `composer.json` and could be installed independently, it's a monorepo.

### Skills profile (when present)

Read `.ai/skills-profile.json` at the project root when it exists. Validate it before using any value: run `python3 ${CLAUDE_SKILL_DIR}/../../bin/profile_check.py .ai/skills-profile.json` (the pack's `bin/` folder, two levels above this skill). Exit 0 means valid.

- **Invalid** (exit 1 or 2): report the checker's messages, then ignore the whole profile. Never half-apply a profile: it is all used or none of it is.
- **Bin scripts missing** (the file at that path does not exist) **or python3 missing**: say so in one line and proceed as with no profile.
- **No profile** (file absent): behavior is exactly as before, unchanged: every question in Step 2 is asked as written and no extra steps run.

A valid profile answers questions. In Step 2, do not ask what the profile already answers; use its value and mention in the review that it came from the profile:

- `gate_tests` (`locked` or `builder-written`): the gate-tests question. The value decides the `Gate tests:` line (see `generation.md`).
- `craft.answers.hosting`: the hosting target question.
- `craft.answers.passwordless`: the passwordless login question.
- `craft.answers.dev_root`: the dev root question (`devRootPath`).

Questions the profile does not answer are asked as usual. `craft.choices` and `setup.steps` are applied in Step 3 and Step 4 (`generation.md`).

## Step 2: Ask clarifying questions

Confirm the detected type and gather project-specific details. Keep it short — 3-5 questions max.

**For plugins:**
- Plugin handle and vendor namespace (detect from `composer.json` if possible)
- Does it have custom element types?
- What Craft edition does it target? (Solo, Team, Pro)

**For sites:**
- CSS framework? (detect Tailwind version from `package.json` or `tailwind.config.*`)
- Are they using atomic design patterns? (detect `_atoms/`, `_molecules/` in templates)
- Any custom modules alongside the site?
- Passwordless login — **only when the site has (or will have) a front-end member area**; skip otherwise. Detect first: `craftpulse/craft-warp` in `composer.json` means passwordless is already chosen — don't ask, record it, and route auth work at the `craft-plugins` skill's `warp.md`. With a member area and no auth plugin detected, ask: **"Should members sign in passwordless — magic links, email codes, passkeys — instead of passwords? (yes/no)"** On **yes**, suggest **Warp** (`craftpulse/craft-warp`, commercial — the passwordless plugin this pack documents) and write `Auth: passwordless via Warp (proposed)` into the generated CLAUDE.md so the planner proposes it at build time. Suggest only — never `composer require` a plugin without explicit approval. On **no**, write `Auth: password-based` and point front-end auth work at the `craft-site` skill's `auth-flows.md`.

**For all types:**
- Confirm detected tooling: ECS, PHPStan, Pest (from `composer.json` scripts)
- Gate tests: **only when the project has an isolated Pest suite** (`tests/Pest.php` exists and `phpunit.xml.dist` pins `CRAFT_DB_DATABASE`); with no suite, don't ask and write nothing. Ask once: **"Should builds lock their gate tests (written first from the acceptance criteria by a separate agent, then not changed by the builder)? (yes/no, default yes)"** Write exactly one line into the generated CLAUDE.md: `Gate tests: locked` on yes, `Gate tests: builder-written` on no. The `craft-feature-builder` agent reads that line.
- Git workflow: main branch name, PR-based workflow?
- Chrome DevTools MCP: offer installation if not already in `.claude.json`
- Dev root folder: "Where is your development root? (e.g., `~/dev/`)" — this is the parent folder where the planner can clone public repos for research and audits. Detect by looking at the project's parent directory. Store in the generated CLAUDE.md as `devRootPath`.
- Hosting target — **sites, hybrid, and monorepo projects only; skip for standalone plugins/modules** (they're distributed as packages, not deployed to a host, so a hosting target is meaningless for them). Detect from signals first. If `craft-cloud.yaml` exists at the repo root OR `craftcms/cloud` is in `composer.json`, this is a **Craft Cloud** project. If `servd.yaml` exists at the repo root OR `servd/craft-asset-storage` is in `composer.json` OR `SERVD_*` env vars are set, this is a **Servd** project. If a `.fortrabbit/` deploy file exists OR config references `FORTRABBIT_*` variables, this is a **fortrabbit** project. Confirm with the user but don't ask redundantly. If no hosting signal is present, ask: "Will this project deploy to Craft Cloud, Servd, fortrabbit, somewhere else (Forge, bare metal, etc.), or is that not decided yet?" Record the answer in the generated CLAUDE.md under a "Hosting" block. When the answer is Cloud, include the `craft-cloud` skill; when it's Servd, include the `servd` skill; when it's fortrabbit, include the `craft-fortrabbit` skill; either way surface that platform's build/deploy/runtime constraints. When it's something else, note the platform so future sessions know which deployment pattern applies (point at the `craftcms` skill's `deployment.md`). When it's **not decided yet**, write `Hosting: TBD` in the block (don't force a choice) — a later session should re-detect from signals (`craft-cloud.yaml` / `servd.yaml` / `.fortrabbit/deploy.yml` / the hosting packages appearing in `composer.json`) and, if still none, re-ask once the decision is made.

**Do not ask about things you already detected.** If `composer.json` shows `nystudio107/craft-seomatic` is installed, the generated templates.md should state "`???` operator is available (provided by SEOmatic)" — not flag it as unknown. If `phpstan/phpstan` is in `require-dev`, include PHPStan commands in the generated CLAUDE.md — don't ask "do you use PHPStan?" Present your detection results for confirmation, not as questions.
