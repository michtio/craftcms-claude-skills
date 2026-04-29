# Object Templates

How Craft CMS 5's mini-template system works in CP settings fields: URI formats, asset subpaths, title formats, preview target URLs, and other settings that accept dynamic values. These are NOT regular Twig templates — they're short expressions evaluated against a specific element with a specific set of context variables. For regular Twig template conventions, see the craft-twig-guidelines skill. For URI routing and template paths, see `boilerplate-routing.md` in the craft-site skill.

## Documentation

- Object templates: https://craftcms.com/docs/5.x/system/object-templates.html
- Routing: https://craftcms.com/docs/5.x/system/routing.html

## Common Pitfalls

- Using `{authorId}` in an asset subpath inside a Matrix field — the context changes inside Matrix. `{authorId}` now refers to the nested entry (likely null), not the parent entry. Use `{owner.authorId}` or `{rootOwner.authorId}`.
- Assuming `{parent.uri}` needs a null guard in structure URI formats — Craft strips leading slashes and collapses double slashes, so `{parent.uri}/{slug}` works correctly for top-level entries (resolves to just `slug`).
- Using `{id}` in asset subpaths — `{id}` changes per draft. Use `{canonicalId}` for stable paths that survive draft/revision cycles.
- Thinking changing an asset subpath format moves existing files — it does not. Existing assets remain at their original filesystem path and become orphaned from the new subpath logic. Migration is manual.
- Expecting errors at save time — object templates are validated at **render time** (when an element is saved or asset is uploaded), not when the CP settings form is saved.

## Contents

- Two Syntaxes — `{attribute}` shortcut vs `{{ twig }}` full expressions
- Where Object Templates Are Used — URI format, title format, asset subpath, preview targets, more
- Context Variables — available attributes on elements, entries, custom fields, structures
- Nesting: owner and rootOwner — context changes in Matrix/CKEditor, the Matrix gotcha
- Structure URI Patterns — parent.uri handling, auto-update, date-based archives
- Asset Subpath Patterns — per-user bucketing, per-entry paths, inside Matrix
- Preview Target URLs — available tokens, canonical IDs for headless
- Date Formatting — Twig filters and PHP methods in templates
- Error Handling — what triggers errors, when validation happens

## Two Syntaxes

Object templates support two syntaxes that can be mixed freely:

### Shortcut: `{attribute}`

Simple property access. Craft transforms `{attribute}` into Twig internally before rendering:

```
{title}           →  {{ (_variables.title ?? object.title)|raw }}
{slug}            →  {{ (_variables.slug ?? object.slug)|raw }}
{section.handle}  →  {{ (_variables.section ?? object.section).handle|raw }}
```

Filters and method calls work in shortcut syntax:

```
{title|upper}              →  uppercase title
{postDate.format('Y')}     →  4-digit year from postDate
{postDate|date('Y-m-d')}   →  formatted date
```

Use shortcut syntax for simple attribute access. It's shorter and more readable.

### Full Twig: `{{ expression }}`

Full Twig expressions for math, conditionals, ternary operators, and complex logic:

```
{{ (authorId // 1000) }}          →  integer division for bucketing
{{ postDate|date('Y/m') }}        →  year/month path
{{ title ~ ' - ' ~ type.name }}   →  concatenation
{{ slug ?? 'untitled' }}          →  null coalescing
```

Use full Twig syntax when you need operators, conditionals, or complex expressions.

### How processing works

Both syntaxes go through `craft\web\View::renderObjectTemplate()`. The shortcut syntax is a preprocessor step — `View::normalizeObjectTemplate()` transforms `{single-brace}` patterns into `{{ double-brace }}` Twig, preserving existing `{{ }}` and `{% %}` blocks. The result is then rendered as standard Twig with the element as the `object` variable.

## Where Object Templates Are Used

| Setting | Location | Example |
|---------|----------|---------|
| **URI format** | Section site settings | `blog/{slug}` |
| **Title format** | Entry type settings (when title field is hidden) | `{author.fullName} - {postDate\|date('Y-m-d')}` |
| **Slug format** | Entry type settings | `{title}` (default) |
| **uiLabelFormat** | Entry type settings (5.9.0) | `{title} ({status})` |
| **Asset upload subpath** | Asset field "Upload Location" | `uploads/{owner.section.handle}/{owner.slug}` |
| **Asset filename format** | Volume settings | `{slug}-{width}x{height}` |
| **Preview target URL** | Section preview targets | `https://app.example.com/preview?token={token}&slug={slug}` |
| **Title translation key** | Entry type settings | Custom translation grouping |
| **Slug translation key** | Entry type settings | Custom translation grouping |

## Context Variables

The element being saved is the context object. All public properties and custom field values are available.

### Available on all elements

| Variable | Type | Notes |
|----------|------|-------|
| `{title}` | `string` | Element title |
| `{slug}` | `string` | URL slug |
| `{id}` | `int` | Element ID — changes per draft |
| `{uid}` | `string` | Element UID |
| `{canonicalId}` | `int` | Canonical element ID — stable across drafts/revisions |
| `{canonicalUid}` | `string` | Canonical UID — stable across drafts/revisions |
| `{status}` | `string` | Current status |
| `{dateCreated}` | `DateTime` | Creation date |
| `{dateUpdated}` | `DateTime` | Last update date |

### Available on entries

| Variable | Type | Notes |
|----------|------|-------|
| `{postDate}` | `DateTime` | Post date |
| `{expiryDate}` | `?DateTime` | Expiry date (null if none) |
| `{authorId}` | `int` | Author user ID |
| `{author}` | `User` | Author element — chainable: `{author.fullName}`, `{author.email}` |
| `{section}` | `Section` | Section object — `{section.handle}`, `{section.name}` |
| `{type}` | `EntryType` | Entry type — `{type.handle}`, `{type.name}` |

### Custom fields

All custom field handles are available as `{fieldHandle}`. The value is whatever the field's `normalizeValue()` returns:

```
{myTextField}                     →  string value
{myDateField|date('Y-m-d')}      →  formatted date
{myDropdownField.value}           →  dropdown option value
{myDropdownField.label}           →  dropdown option label
```

Relation fields return element queries, not elements — use `.one().title` or similar for resolved values.

### Structure elements

| Variable | Type | Notes |
|----------|------|-------|
| `{parent}` | `?Element` | Parent element in structure (null at top level) |
| `{parent.uri}` | `?string` | Parent's URI (null at top level) |
| `{parent.title}` | `?string` | Parent's title |
| `{level}` | `int` | Nesting depth (1 = top level) |

## Nesting: owner and rootOwner

When an element is nested inside another (Matrix entries, CKEditor nested entries), the context variables refer to the **nested entry itself**, not the parent. Use `owner` and `rootOwner` to access parent elements.

### owner (immediate parent)

Available on nested entries. Returns the full parent element with all its attributes and custom fields.

```
{owner.title}              →  parent entry's title
{owner.slug}               →  parent entry's slug
{owner.authorId}           →  parent entry's author ID
{owner.section.handle}     →  parent entry's section handle
{owner.myCustomField}      →  parent entry's custom field value
```

### rootOwner (top-level ancestor, since 5.4.0)

For deeply nested elements (Matrix inside Matrix, etc.), `rootOwner` walks the ownership chain to the top-level canonical entry.

```
{rootOwner.title}          →  top-level entry's title
{rootOwner.authorId}       →  top-level entry's author ID
{rootOwner.section.handle} →  top-level entry's section
```

For non-nested elements, `rootOwner` returns the element itself.

### The Matrix gotcha

When you move a field from a top-level entry into a Matrix field, all `{attribute}` references change meaning:

| Expression | Top-level entry | Inside Matrix |
|-----------|----------------|---------------|
| `{authorId}` | Entry's author | Matrix nested entry's author (likely null) |
| `{section.handle}` | Entry's section | Matrix nested entry's section |
| `{slug}` | Entry's slug | Matrix nested entry's slug |
| `{id}` | Entry's ID | Matrix nested entry's ID |

**Fix:** prefix with `owner.` for parent attributes, or `rootOwner.` for deeply nested:

```
# Before (top-level asset subpath):
{{ (authorId // 1000) }}/{authorId}/{canonicalId}

# After (inside Matrix):
{{ (owner.authorId // 1000) }}/{owner.authorId}/{owner.canonicalId}

# Inside Matrix-in-Matrix:
{{ (rootOwner.authorId // 1000) }}/{rootOwner.authorId}/{rootOwner.canonicalId}
```

## Structure URI Patterns

### Basic patterns

```
# Channel (flat)
blog/{slug}

# Structure (hierarchical)
{parent.uri}/{slug}

# Structure with section prefix
services/{parent.uri}/{slug}
```

### How parent.uri handles top-level entries

When a structure entry has no parent, `{parent.uri}` resolves to an empty/undefined value. Craft normalizes URI output by:
1. Stripping leading slashes
2. Stripping trailing slashes
3. Collapsing consecutive slashes (`//` → `/`)

This means `{parent.uri}/{slug}` at the top level renders as `/{slug}`, which becomes `slug` after normalization. **No null guard is needed.**

### Explicit null guard (optional)

If you want to be explicit or add a static prefix for top-level entries:

```
{{ parent.uri is defined and parent.uri ? parent.uri ~ '/' : '' }}{slug}
```

This is functionally identical to `{parent.uri}/{slug}` but makes the intent clearer.

### Descendant URI auto-update

When a parent entry's slug or position changes, Craft automatically re-renders all descendant URIs. This happens via the `UpdateElementSlugsAndUris` queue job, which recursively walks the structure. No manual intervention needed.

### Date-based archive URIs

```
# Year archive
news/{postDate|date('Y')}/{slug}

# Year/month archive
news/{postDate|date('Y/m')}/{slug}

# Year/month/day archive
news/{{ postDate|date('Y/m/d') }}/{slug}
```

## Asset Subpath Patterns

Asset subpath templates evaluate against the **element the asset field is attached to** — the entry containing the field, not the asset itself.

### Common patterns

```
# Static path
uploads/

# Per-section organization
{section.handle}/{slug}/

# Per-author bucketing (for filesystem performance with many users)
{{ (authorId // 1000) }}/{authorId}/

# Per-entry with canonical ID (draft-safe)
entries/{canonicalId}/

# Per-entry with slug
{section.handle}/{slug}/
```

### Inside Matrix

When the asset field is inside a Matrix, the context element is the **Matrix nested entry**. Use `owner` to access the parent entry:

```
# Parent entry's section and slug
{owner.section.handle}/{owner.slug}/

# Root entry's author bucketing (Matrix inside Matrix)
{{ (rootOwner.authorId // 1000) }}/{rootOwner.authorId}/
```

### What triggers "Invalid subpath" errors

`Assets::resolveSubpath()` throws `InvalidSubpathException` when:
- Template rendering fails (Twig syntax error)
- Rendered result is empty after trimming
- Result contains whitespace
- Result contains double slashes (`//`)
- Any path segment matches a temporary slug

These errors occur at **upload time**, not when the field settings are saved.

### Changing subpaths does NOT move files

Existing assets remain at their original filesystem path. The new subpath format only applies to future uploads. To migrate existing assets, you need a custom script or the `index-assets` console command after manually moving files.

## Preview Target URLs

Preview target URL templates have access to the **full element** as context. Common pattern for headless:

```
https://frontend.example.com/api/preview?token={token}&slug={slug}
```

| Token | Purpose |
|-------|---------|
| `{url}` | Element's canonical URL |
| `{slug}` | Element's slug |
| `{id}` | Element ID (changes per draft) |
| `{uid}` | Element UID |
| `{canonicalId}` | Canonical element ID (stable across drafts) |
| `{canonicalUid}` | Canonical UID (stable across drafts) |
| `{token}` | Preview token — required for headless preview |

Use `{canonicalId}` and `{canonicalUid}` instead of `{id}`/`{uid}` because preview targets are often evaluated against drafts, and you want the source element's identifiers.

## Date Formatting

Dates in object templates use Twig's `date` filter or PHP's `format()` method:

```
# Twig filter (in {{ }} or shortcut)
{postDate|date('Y-m-d')}
{{ postDate|date('Y/m') }}

# PHP method (shortcut only)
{postDate.format('Y')}
```

Common format tokens: `Y` (4-digit year), `m` (2-digit month), `d` (2-digit day), `H` (24h hour), `i` (minute).

## Error Handling

| When | What happens |
|------|-------------|
| Nonexistent attribute (`{nonexistent}`) | Silently resolves to empty string |
| Twig syntax error | Runtime error at render time |
| Null value in path | Empty string, may trigger "Invalid subpath" if result is empty |
| Invalid subpath (whitespace, `//`, empty) | `InvalidSubpathException` at upload time |
| URI format produces empty string | Element gets no URI (intentional for some elements) |

Template validation happens at **render time**, not at **settings save time**. Test your templates by saving an element or uploading an asset — don't assume a successful settings save means the template is correct.
