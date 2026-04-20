# Agents

Five specialized sub-agents, each with a dedicated model and tool scope. Agents are invoked from within Claude Code to handle specific types of work. They load relevant skills automatically and enforce project conventions.

## When to Use Agents

Use agents when work is scoped and repeatable. A single conversation can delegate to multiple agents -- plan with the planner, build with the builder, review with the reviewer.

| Situation | Agent |
|-----------|-------|
| Breaking a feature into implementation steps | `craft-planner` |
| Building a new plugin feature (elements, services, controllers) | `craft-feature-builder` |
| Building site templates, components, or content architecture | `craft-site-builder` |
| Investigating a bug or unexpected behavior | `craft-debugger` |
| Reviewing code before merge | `craft-code-reviewer` |

For complex work (more than 3 steps), always plan first, then build. The planner's output feeds directly into the builder.

---

## craft-planner

**Model:** Opus (complex reasoning)
**Tools:** Read, Grep, Glob (read-only)
**Skills loaded:** `craftcms`

Breaks large tasks into scoped implementation steps that can each be completed in a single session.

### What it does

1. Reads the high-level requirement
2. Identifies all affected areas (elements, queries, services, controllers, migrations, templates, project config, tests)
3. Maps dependencies -- what must be built first
4. Breaks work into steps of roughly equal size
5. Writes the plan to `docs/plans/{feature-name}.md`

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

**Model:** Opus (complex multi-file work)
**Tools:** Read, Write, Edit, Bash, Grep, Glob, TaskCreate, TaskUpdate, TaskList
**Skills loaded:** `craftcms`, `craft-php-guidelines`, `craft-garnish`

Builds production-quality plugin code following project architecture. Receives implementation plans and executes them layer by layer.

### The Build-Verify Gate Pattern

This is the core discipline. Each layer must pass its gate before the next layer starts. The builder never writes five files and verifies at the end -- that compounds debugging complexity.

**Gate order for plugin work:**

1. **Migration** -- `ddev craft migrate/up` succeeds, schema exists
2. **Record / Model** -- class resolves, `ddev craft` doesn't throw on boot
3. **Service** -- minimal method callable via Craft CLI or Pest test
4. **Controller** -- actual request (`curl` or browser) returns expected response
5. **CP templates** -- edit/index pages render without Twig errors
6. **Tests** -- `ddev craft pest/test` green
7. **Simplification pass** -- collapse nesting, remove debug artifacts, verify PHPDocs
8. **Final verification** -- `ddev composer check-cs` + `ddev composer phpstan` clean

A gate is "I ran the thing and saw it work." If a gate fails, the builder stops and fixes before moving on. It never plasters over a failed gate.

### Mandatory todo list

When a plan has more than 3 steps, the builder creates a todo list before writing any code. One todo per plan step. A step is marked `completed` only after its verification gate passes -- never batch-completed.

### Prevention rules

The builder enforces 14 rules that the reviewer will flag if violated:

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
Build the Job Listings element type following the plan in docs/plans/job-listings.md
```

---

## craft-site-builder

**Model:** Opus (complex multi-file work)
**Tools:** Read, Write, Edit, Bash, Grep, Glob, TaskCreate, TaskUpdate, TaskList
**Skills loaded:** `craft-site`, `craft-twig-guidelines`, `craft-content-modeling`

Builds site templates, content architecture, and component systems following atomic design principles.

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

**Model:** Sonnet (focused, single-concern)
**Tools:** Read, Write, Edit, Bash, Grep, Glob
**Skills loaded:** `craftcms`, `craft-php-guidelines`

Systematic bug investigation with a hypothesis-driven approach.

### Debugging workflow

1. **Reproduce** -- understand the exact steps, read error logs and queue failures
2. **Hypothesize** -- form 2-3 possible explanations before reading code
3. **Investigate** -- read relevant code, check `storage/logs/`, run targeted tests
4. **Isolate** -- write a minimal failing test that captures the bug
5. **Fix** -- make the smallest change that fixes the issue
6. **Verify** -- run ECS, PHPStan, and the full test suite

### Craft-specific investigation points

The debugger knows where to look for common Craft issues:

- **Element not found?** Check site context -- queue workers run in primary site. Try `->site('*')->status(null)`.
- **Project config drift?** Compare YAML with database via `ddev craft project-config/diff`.
- **Migration failed?** Check for stale mutex locks in `cache` table.
- **Queue job failing silently?** Check `ddev craft queue/info` and Craft logs for TTR timeouts.
- **Element status wrong?** Status is computed from dates/conditions, not stored -- check `getStatus()`.

### Rules

- Always writes a regression test before fixing
- Explains reasoning at each step
- Never fixes a symptom without finding the root cause
- States what has been ruled out if the cause is not found

### Example delegation

```
The sync queue job is failing silently on the staging server. No errors
in the queue log, but entries aren't being updated. Investigate.
```

---

## craft-code-reviewer

**Model:** Sonnet (focused, single-concern)
**Tools:** Read, Grep, Glob (read-only)
**Skills loaded:** `craftcms`, `craft-php-guidelines`, `craft-garnish`

Code review with a structured findings report. Read-only -- it never modifies files.

### Review workflow

1. Identify changed files via `git diff`
2. Read each changed file thoroughly
3. Check against the 19-item checklist
4. Generate a findings report grouped by severity

### Report format

- **Critical** (must fix before merge) -- security issues, data integrity risks, broken conventions
- **Important** (should fix) -- missing PHPDocs, incomplete `@throws`, architectural violations
- **Suggestions** (nice to have) -- naming improvements, simplification opportunities, test coverage gaps

### The 19-item checklist

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

### Example delegation

```
Review the changes in the job-listings branch before I open a PR.
```

---

## Prevention/Detection Parity

The builder and reviewer are designed as complementary pairs. The builder's 14 prevention rules map to the reviewer's 19 checklist items. Everything the builder prevents, the reviewer detects -- and vice versa.

This means code built by the `craft-feature-builder` agent passes the `craft-code-reviewer` agent's checklist with zero findings if the builder followed its own rules. The overlap is intentional: if the builder misses something (it sometimes does), the reviewer catches it.

## Agent Composition Patterns

### Plan then build

The most common pattern. Plan first to break down complexity, then build layer by layer.

```
1. Delegate to craft-planner: "Plan the implementation of..."
2. Review the plan, adjust if needed
3. Delegate to craft-feature-builder: "Build following the plan in docs/plans/..."
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
