# Agents

Six specialized sub-agents, each with a dedicated model, effort level, and tool scope. Agents are invoked from within Claude Code to handle specific types of work. Each preloads its core skills on every run (startup at most 48 KB, about 12K tokens, checked by `bin/agent_budget.py`) and loads the rest on demand through the Skill tool, and enforces project conventions.

Models are set with the `opus` / `sonnet` aliases, so agents follow each family to its current version instead of pinning one. Builders list both `TodoWrite` and the `Task*` tools because a background subagent keeps only `TodoWrite`, while a foreground one inherits whichever the main session has. Agents with a browser-verification step list `mcp__chrome-devtools`; it resolves only when Chrome DevTools MCP is installed (see the `ddev` skill). Plugin subagents ignore `hooks`, `mcpServers`, and `permissionMode`, so none are set. See the [subagents docs](https://code.claude.com/docs/en/sub-agents) for the frontmatter fields.

## When to Use Agents

Use agents when work is scoped and repeatable. A single conversation can delegate to multiple agents -- plan with the planner, build with the builder, review with the reviewer.

| Situation | Agent |
|-----------|-------|
| Breaking a feature into implementation steps | `craft-planner` |
| Building a new plugin feature (elements, services, controllers) | `craft-feature-builder` |
| Building site templates, components, or content architecture | `craft-site-builder` |
| Investigating a bug or unexpected behavior | `craft-debugger` |
| Reviewing code before merge | `craft-code-reviewer` |
| Deep review of a high-stakes change (release branch, security-sensitive code, migrations, multi-service flows) | `craft-code-reviewer-deep` |

For complex work (more than 3 steps), always plan first, then build. The planner's output feeds directly into the builder.

Every agent works from the project's Craft version. It uses the version line the skills print in a Craft project, or reads `composer.lock` / the `craftcms/cms` constraint itself, and compares that version with the pack's version tags (`[5.12+]`, `[changed 5.12]`) before it uses, plans, flags or approves an API. Below a tag, builders use the `Before 5.x:` alternative or make a constraint bump explicit, and reviewers flag the API unless the constraint or a `version_compare` guard covers it. Below the minimum safe version, they say so once. MCP work (tools, OAuth resources, connecting an AI client) loads the `craft-mcp` skill (Craft 5.12+).

---

## craft-planner

**Model:** Opus (`high` effort)
**Tools:** Read, Grep, Glob, Bash, WebFetch, Skill (read-only on the project — Bash for `git`/`gh` research and clones into the research folder)
**Skills preloaded:** `craftcms` (others on demand: `craft-pest`, `craft-content-modeling`, `craft-garnish`, `craft-plugins`, `craft-cloud`, `servd`, `craft-fortrabbit`, `craft-mcp`)

Breaks large tasks into scoped implementation steps that can each be completed in a single session.

### What it does

1. Reads the high-level requirement
2. Identifies all affected areas (elements, queries, services, controllers, migrations, templates, project config, tests)
3. Maps dependencies -- what must be built first
4. Breaks work into steps of roughly equal size
5. Requires an approved PRD (`prd.md`) first, then returns `plan.md`, headed with its intended path `specs/YYYY-MM-DD-<slug>/plan.md` (or a git-ignored folder for a public package), for the caller to save (the planner has no Write tool)

### Plan format

Each step includes:
- Files to create or modify (exact paths)
- Dependencies on previous steps
- Which `ddev craft make` command to scaffold with
- A **verification gate** -- a runnable command with expected outcome (not "looks right")
- Estimated complexity: small (< 15 min), medium (15-30 min), large (30-45 min)

### Rules

- Each step's verification gate must be a runnable command. "Check that it works" is not a gate -- `ddev craft migrate/up` succeeds and shows the new table" is a gate.
- Steps are ordered so each layer can be verified before the next depends on it: migrations before records, records before services, services before controllers.
- No step may require a later step to verify itself.
- Architectural decisions are surfaced as explicit decision points, not buried as assumptions.
- Multi-site implications and project config impacts are flagged.
- Auth level is asked upfront: public, any user, admin, or permission-gated.

### Example delegation

```
Plan the implementation of a Job Listings custom element type with
department relations, salary range, and a full CP edit page.
```

---

## craft-feature-builder

**Model:** Opus (`high` effort)
**Tools:** Read, Write, Edit, Bash, Grep, Glob, Skill, Agent, WebFetch, TodoWrite, TaskCreate, TaskUpdate, TaskList, ToolSearch, `mcp__chrome-devtools`
**Skills preloaded:** `craftcms`, `craft-php-guidelines` (on demand: `craft-pest` before the first test, `craft-garnish` for CP JavaScript, `ddev`)

Builds production-quality plugin code following project architecture. Receives implementation plans and executes them layer by layer.

Every new test runs red before its code and green after; the hand-back lists both, with the failure reason. Before hand-writing a helper it checks Craft's helpers, services and response formats (CSV via `Response::FORMAT_CSV`), `Craft::createGuzzleClient()` and the packages in `composer.lock`, and names anything it wrote that already existed. See [Checker gate](#checker-gate-builders) for the last step.

### The Build-Verify Gate Pattern

This is the core discipline. Each layer must pass its gate before the next layer starts. The builder never writes five files and verifies at the end -- that compounds debugging complexity.

**Gate order for plugin work:**

1. **Migration** -- `ddev craft migrate/up` succeeds, schema exists
2. **Record / Model** -- class resolves, `ddev craft` doesn't throw on boot
3. **Service** -- its Pest test, written alongside it, is green (`--filter=MyServiceTest`)
4. **Controller** -- its HTTP test is green; permission-gated users get 403
5. **CP templates** -- edit/index pages render without Twig errors
6. **Full suite** -- every test green, not just the new ones
7. **Simplification pass** -- collapse nesting, remove debug artifacts, verify PHPDocs
8. **Final verification** -- `ddev composer check-cs` + `ddev composer phpstan` clean

Pest always runs from the plugin's own root, because craft-pest-core reads the plugin's `phpunit.xml.dist` `<env>` database pins from the working directory. A run from the host project root (including `ddev craft pest -- --configuration=…`) tests against the development database. See the `craft-pest` skill's `references/isolation.md`.

```bash
# Plugin inside a host project
ddev exec --dir /var/www/html/vendor/{vendor}/{plugin} vendor/bin/pest
# Plugin with its own DDEV project
ddev exec --dir /var/www/html vendor/bin/pest
```

A gate is "I ran the thing and saw it work." If a gate fails, the builder stops and fixes before moving on. It never plasters over a failed gate.

### Mandatory todo list

When a plan has more than 3 steps, the builder creates a todo list (TodoWrite or the Task tools, whichever its run has) before writing any code. One todo per plan step. A step is marked `completed` only after its verification gate passes -- never batch-completed.

### Prevention rules

The builder enforces these rules that the reviewer will flag if violated:

- `andWhere()` not `where()` on element queries
- No hardcoded site IDs
- `$allowAnonymous` lists specific actions, never blanket `true`
- No `$e->getMessage()` returned to anonymous users
- Permission handles as class constants
- Cached badge counts in `getCpNavItem()`
- `Gc::EVENT_RUN` for cleanup, not synchronous hooks
- Conditional asset bundle registration
- No `|raw` on admin content in `<style>`/`<script>`
- All query properties wired in `beforePrepare()`
- Twig extension functions return, not echo
- `addSelect()` not `select()`, `site('*')` in queue workers
- `Db::parseParam()` for user input
- Idempotent migrations with `muteEvents`
- No improvised CP UI — copy the core/vendor idiom and cite the template matched
- Restructures re-verify standing behavioral decisions, not just routes/tests

### Simplification pass

After all gates pass, the builder does one sweep on files it just wrote (while context is fresh):
- Collapse nesting with early returns
- Remove temporary debug variables
- Simplify conditionals (`match` over `switch`)
- Delete dead code and unused imports
- Verify section headers and PHPDocs
- Re-run ECS and PHPStan

### Example delegation

```
Build slice S1 of specs/2026-10-09-job-listings/plan.md (approved, PRD approved).
Requirements R1-R3; acceptance criteria AC1-AC4 in prd.md.
Gate: ddev craft migrate/up succeeds and the JobListingServiceTest Pest filter is green.
```

---

## craft-site-builder

**Model:** Opus (`high` effort)
**Tools:** Read, Write, Edit, Bash, Grep, Glob, Skill, Agent, WebFetch, TodoWrite, TaskCreate, TaskUpdate, TaskList, ToolSearch, `mcp__chrome-devtools`
**Skills preloaded:** `craft-site`, `craft-twig-guidelines`, `craft-content-modeling` (on demand: `craft-plugins`, `craft-cloud`, `servd`, `craft-fortrabbit`, `craft-mcp`, `ddev`)

Builds site templates, content architecture, and component systems following atomic design principles. Reuses existing components and Craft's Twig helpers before writing new ones, and ends with the [checker gate](#checker-gate-builders).

### The Build-Verify Gate Pattern (Site Edition)

Adapted for site work, but the same discipline applies -- verify each layer before composing the next.

**Gate order for site work:**

1. **Content model** -- sections, entry types, fields created. Verified in CP.
2. **Sample content** -- at least one entry per type exists for rendering
3. **Atoms** -- render standalone in a scratch template without errors
4. **Molecules** -- render with real atom compositions, props flow correctly
5. **Organisms / layouts** -- full-page render succeeds, no Twig errors
6. **Routes / views** -- actual page load returns expected HTML
7. **Eager loading audit** -- Elements Panel shows no N+1 on relational fields
8. **Responsive / a11y check** -- after content renders correctly

### What it does well

- Plans content models and presents them as decision tables before implementing
- Builds atoms before molecules before organisms (never top-down)
- Enforces `only` on every `{% include %}`
- Uses `.eagerly()` on every relational field in loops
- Applies atomic design naming (by visual treatment, not parent context)
- Uses `collect({})` for props and class collections
- Handles Matrix block rendering with `ignore missing`

### What it never does

- Install plugins without approval
- Write PHP plugin/module code (that's `craft-feature-builder`)
- Skip eager loading on relational fields
- Use macros for UI components
- Hardcode content that should come from fields

### Example delegation

```
Build the blog listing and detail templates with a card component,
topic filtering, and pagination.
```

---

## craft-debugger

**Model:** Sonnet (`high` effort)
**Tools:** Read, Write, Edit, Bash, Grep, Glob, Skill, WebFetch, ToolSearch, `mcp__chrome-devtools`
**Skills preloaded:** `craftcms`, `craft-php-guidelines`, `craft-pest` (on demand: `craft-garnish`, `craft-site`, `craft-twig-guidelines`, `ddev`, `craft-cloud`, `servd`, `craft-fortrabbit`, `craft-mcp`, `craft-plugins`)

Systematic bug investigation with a hypothesis-driven approach.

### Debugging workflow

1. **Reproduce** -- understand the exact steps, read error logs and queue failures
2. **Hypothesize** -- form 2-3 possible explanations before reading code
3. **Investigate** -- read relevant code, check `storage/logs/`, run targeted tests
4. **Isolate** -- write a minimal failing test that captures the bug
5. **Fix** -- make the smallest change that fixes the issue
6. **Verify** -- regression test red before the fix and green after, then ECS, PHPStan, and the full test suite (run from the plugin's own root)

### Craft-specific investigation points

The debugger knows where to look for common Craft issues:

- **Element not found?** Check site context -- queue workers run in primary site. Try `->site('*')->status(null)`.
- **Project config drift?** Compare YAML with database via `ddev craft project-config/diff`.
- **Migration failed?** Check for stale mutex locks in `cache` table.
- **Queue job failing silently?** Check `ddev craft queue/info` and Craft logs for TTR timeouts.
- **Element status wrong?** Status is computed from dates/conditions, not stored -- check `getStatus()`.

### Rules

- Always writes a regression test before fixing
- Backs every conclusion with evidence (file:line, log line, test output)
- Never fixes a symptom without finding the root cause
- States what has been ruled out if the cause is not found

### Example delegation

```
The sync queue job is failing silently on the staging server. No errors
in the queue log, but entries aren't being updated. Investigate.
```

---

## craft-code-reviewer

**Model:** Sonnet (`high` effort)
**Tools:** Read, Grep, Glob, Bash, Skill, ToolSearch, `mcp__chrome-devtools` (read-only — Bash for `git diff`/`log`/`show`/`blame` only)
**Skills preloaded:** `craftcms`, `craft-php-guidelines` (loaded by diff type: `craft-twig-guidelines` + `craft-site` for Twig, `craft-garnish` for CP JS, `craft-pest` for tests, `craft-cloud` for Cloud projects, `craft-plugins` for named plugins)

Code review with a structured findings report. Read-only -- it never modifies files.

### Review workflow

1. Identify changed files via `git diff`
2. Classify the diff and load the skills it needs
3. Read each changed file thoroughly
4. Check against the checklist
5. Generate a findings report grouped by severity

### Report format

- **Critical** (must fix before merge) -- security issues, data integrity risks, broken conventions
- **Important** (should fix) -- missing PHPDocs, incomplete `@throws`, architectural violations, new branches without tests
- **Suggestions** (nice to have) -- naming improvements, simplification opportunities

It reports every issue that could cause incorrect behaviour, a security gap, data loss, or a test failure, including uncertain ones marked `Verify:`, and omits only style preferences no skill states as a rule.

### The checklist

**Security (5 checks):**
1. `$allowAnonymous` uses specific action names, never blanket `true`
2. Exception messages never returned to anonymous users
3. `|raw` in CP templates reviewed for XSS
4. Permission handles match between registration and checking
5. `Db::parseParam()` for user input

**Query safety (5 checks):**
6. `addSelect()` not `select()`
7. `andWhere()` not `where()`
8. No hardcoded site IDs
9. All query class properties wired in `beforePrepare()`
10. `site('*')` in queue workers

**Performance (4 checks):**
11. `getCpNavItem()` badge counts are cheap
12. No synchronous cleanup in `init()`
13. `defineSources()` uses aggregate queries
14. Asset bundles registered conditionally

**Code quality (5 checks):**
15. PHPDoc completeness on every class, method, property
16. Section headers present and correct
17. Early returns, `match` over `switch`
18. Twig extensions return (not echo), delegate to services
19. Migration safety: idempotent, `muteEvents`

### CP JavaScript checks (when JS files are in scope)

- Classes extend `Garnish.Base`
- Listeners use `addListener()`, not jQuery `.on()`
- Non-button elements use `activate` event, not `click`
- Key codes use Garnish constants
- ESC handling through `uiLayerManager`
- Webpack uses externals for Garnish
- `destroy()` calls `this.base()`
- Deprecated APIs flagged

### Test checks (when tests are in scope)

- `craft-pest` isolation checklist: `RefreshesDatabase` bound, DB pins present, suite invoked from the plugin's own root. A suite that can reach a real database is **Critical**.
- New branches without tests, or tests that would pass with the change reverted, are **Important**.

### Example delegation

```
Review the changes in the job-listings branch before I open a PR.
```

---

## craft-code-reviewer-deep

**Model:** Opus (`high` effort), orchestrating `craft-review-checker` agents (Sonnet; security on Opus)
**Tools:** Read, Grep, Glob, Bash, Skill, Agent (read-only: Bash for `git diff`/`log`/`show`/`blame`, plus PHPStan and ECS in check mode through DDEV)
**Skills preloaded:** none (it orchestrates; it and its checkers load `craft-php-guidelines`, `craft-twig-guidelines`, `craft-pest`, `craft-site`, `craft-garnish`, `craft-mcp`, `craft-plugin-release`, `craft-cloud`, `servd`, `craft-fortrabbit` or `craft-plugins` when the diff reaches them)

The deep-review counterpart to `craft-code-reviewer`, for release branches, security-sensitive code, large architectural changes, migrations and multi-service flows. Depth comes from separate checkers with one job each, from evidence and from a challenge round, not from one long think.

### How a review runs

1. **Triage.** Reads the diff stat and log, sorts changed files by area, finds the governing Craft version, and picks a mode.
2. **Static checks.** Runs PHPStan and ECS (check mode only) when the project configures them, and keeps the lines for changed files. Pest runs only when you ask for it, because a suite can write to a database.
3. **Checkers.** Starts `craft-review-checker` agents in parallel: conventions and security always, plus at most two of performance, migrations, CP JavaScript, release and hosting, depending on what the diff touches.
4. **Challenge.** Every Critical and Important finding goes to one fresh challenger checker, which upholds it, refutes it with a file:line or Craft source citation, or marks it unsure. Refuted findings are dropped (and listed), unsure ones are reported as **disputed** with both arguments.
5. **Report.** One merged report. At most 5 agents per review.

**Single pass:** a diff under 200 changed lines in one area, or a session where agents cannot start agents (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`), gets one review by the orchestrator itself, with the same lenses and no challenge round.

### What the lenses cover

- **Conventions:** semantic correctness (empty arrays, soft-deleted parents, drafts, disabled sites), plugin lifecycle, architecture, untested branches and test isolation, PHPDocs and section headers.
- **Security:** request data traced controller → service → element → DB, permission checks before model population, TOCTOU, CSRF, output escaping, SQL from input, secrets, MCP tools and OAuth resources.
- **Performance:** N+1 at production volume (including queries in services called from loops), eager loading, caches, queue batching, indexes.
- **Migrations:** large tables, batching, locking and transactions, project-config writes, rollback, idempotent installs, single-worker assumptions.
- **CP JavaScript:** Garnish patterns, cleanup, keyboard, focus and ARIA.
- **Release and hosting:** version bumps, changelog dates, tags, release workflows, Cloud, Servd and fortrabbit constraints, named third-party plugins.

### Discipline

No runtime bug from generic framework intuition: claims about state staleness, DI timing or cache lifecycle must trace through Craft's Yii2 source, or they become a "Verify:" suggestion. A finding backed by PHPStan or ECS ranks above one that is not.

### Report format

First line: the mode, the checkers used, the number of agents started and the static-check summary. Then Critical / Important / Suggestions, then "Dropped after challenge". With a spec named in the brief, a per-R-id table. Read-only; never modifies files.

### Example delegation

```
Deep-review the release/1.6.0 branch before tagging: it touches migrations,
the asset filesystem, and the permission layer.
```

---

## craft-review-checker

**Model:** Sonnet (`high` effort); the deep reviewer runs the security lens on Opus
**Tools:** Read, Grep, Glob, Bash, Skill (read-only)
**Skills preloaded:** `craftcms` (others on demand, per lens)

One lens of a deep review, started by `craft-code-reviewer-deep` (or by a builder, see below) with a lens brief, the Craft version, the files and the static-check lines for them. Also answers challenge rounds: upholds, refutes with a citation, or marks a finding unsure. It starts at about 14 KB (the everyday reviewer starts at about 39 KB), so each extra lens stays cheap. Not for direct use. It never has the `Agent` tool, so teams never nest further.

### Checker gate (builders)

Before handing back, `craft-feature-builder` and `craft-site-builder` size their diff and start one `craft-review-checker`:

| Diff | Checker |
|---|---|
| Under 50 changed lines, nothing sensitive | Skipped, and the hand-back says so |
| Under 50 lines, touching controllers, permissions, request input, migrations, `\|raw`/`attr()` output, MCP or OAuth, or `config/` | Security lens only |
| 50 lines or more | Security and conventions |

A Critical finding is fixed, gates re-run, and the fix re-checked; Important findings are fixed or listed. When agents cannot start agents (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`), the hand-back says the checker did not run.

### Agent caps

Every agent that can start agents declares a cap, checked in CI by `bin/agent_budget.py`: at most 5 for the deep reviewer, 3 for each builder, 0 for every agent without the `Agent` tool. The cap line in the agent file reads `At most N agents per <run|review>`; a missing line or a cap above 5 fails the build.

---

## Prevention/Detection Parity

The builder and reviewer are designed as complementary pairs. The builder's prevention rules map to the reviewer's checklist items. Everything the builder prevents, the reviewer detects -- and vice versa.

This means code built by the `craft-feature-builder` agent passes the `craft-code-reviewer` agent's checklist with zero findings if the builder followed its own rules. The overlap is intentional: if the builder misses something (it sometimes does), the reviewer catches it.

## Agent Composition Patterns

### Plan then build

The most common pattern. Plan first to break down complexity, then build layer by layer.

```
1. Write and approve the PRD: specs/{date-slug}/prd.md
2. Delegate to craft-planner: "Plan the implementation of specs/{date-slug}/prd.md"
3. Review and approve the returned plan, save it as specs/{date-slug}/plan.md
4. Delegate to craft-feature-builder, one slice at a time: "Build slice S1 of specs/{date-slug}/plan.md: R ids, their acceptance criteria, the verification gate"
```

### Build then review

After building, get a second opinion.

```
1. Delegate to craft-feature-builder: "Build the webhook controller..."
2. Delegate to craft-code-reviewer: "Review the changes in the webhook branch"
3. Fix any findings from the review
```

### Debug then fix

When something breaks, investigate before patching.

```
1. Delegate to craft-debugger: "The sync job is failing silently..."
2. Debugger identifies root cause and writes regression test
3. If fix is complex, delegate to craft-feature-builder for the implementation
```

### Full cycle

For significant features:

```
1. craft-planner -- break down the feature
2. craft-feature-builder -- implement layer by layer
3. craft-code-reviewer -- review before merge
4. craft-debugger -- investigate if anything breaks in staging
```
