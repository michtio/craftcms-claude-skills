# Content Modeling Patterns

Strategic patterns for common Craft CMS 5 project types. Each pattern shows
which sections, entry types, fields, and relation strategies to use.

## Blog

### Sections

- **Blog** (Channel) — URI: `blog/{slug}`, template: `blog/_entry`
- **Topics** (Structure, 2 levels max) — replaces categories. URI: `topics/{slug}`
- **Authors** (Channel, no URI) — if authors need more than User profiles

### Entry Types

- **Post** — title, featured image (Assets), excerpt (Plain Text), body (Matrix), topics (Entries → Topics), related posts (Entries → self)
- **Topic** — title, description (Plain Text), topicIcon (Icon or Assets)

### Matrix: Body Content

Entry types for body Matrix: Rich Text (CKEditor), Image (Assets + caption), Video (Link field), Quote (Plain Text + attribution), Code Block (Plain Text, monospaced), CTA (heading + text + Link field)

### Twig Pattern

```twig
{# blog/_entry.twig #}
{% set image = entry.featuredImage.eagerly().one() %}
{% set topics = entry.topics.eagerly().all() %}

{% for block in entry.bodyContent.all() %}
    {% include '_blocks/' ~ block.type.handle ignore missing only %}
{% endfor %}
```

### Key Decisions

- Topics as Structure (not categories) — gives you drafts, custom fields, URLs
- Related Posts as self-referential Entries field — manual curation beats algorithmic
- Body as Matrix — flexible per-post layout without template complexity

---

## Portfolio / Case Studies

### Sections

- **Projects** (Channel) — URI: `work/{slug}`
- **Services** (Structure) — URI: `services/{parent.uri}/{slug}`
- **Clients** (Channel, no URI) — referenced from projects

### Entry Types

- **Project** — title, client (Entries → Clients), services (Entries → Services), gallery (Assets, multiple), description (Matrix or CKEditor), project URL (Link), year (Number), featured (Lightswitch)
- **Client** — title, logo (Assets), website (Link)
- **Service** — title, description (Plain Text), serviceIcon (Icon)

### Key Decisions

- Clients as separate section — one client, many projects. Query `craft.entries.section('projects').relatedTo({ targetElement: client, field: 'client' })` for all projects by a client
- Services as Structure — supports parent/child grouping (Design → UI Design, Brand Design)
- Featured Lightswitch — filters homepage showcase: `craft.entries.section('projects').featured(true)`

---

## Multi-Site Corporate

### Site Configuration

Plan sites and groups first. Example: site group "English" (en-us, en-gb), site group "French" (fr-fr, fr-be).

### Sections

- **Pages** (Structure) — URI: `{parent.uri}/{slug}`, propagation: all sites
- **News** (Channel) — URI: `news/{slug}`, propagation: per site group
- **Team** (Channel) — propagation: all sites (same people across all sites)
- **Locations** (Channel) — propagation: all sites
- **Site Settings** (Single, no URI) — `preloadSingles`, propagation: all sites (hard-coded)

### Field Translation Methods

| Field | Translation |
|-------|-------------|
| Title | Per site (different per language) |
| Slug | Per site |
| Body content | Per site |
| Featured image | Not translatable (same image across sites) |
| Reference number / date | Not translatable |
| SEO meta | Per site |

### Key Decisions

- Configure propagation **before** creating any content
- Set field translation methods **before** populating fields
- Use site groups to share content within language families
- Site Settings single for footer text, social links, contact info — per-site translated
- News per site group — English sites share news, French sites share their own

---

## Entries-as-Taxonomy (Replacing Categories)

Categories, tags, and globals are being unified into entries over three versions. See the SKILL.md "Entrification" section for the full timeline, CLI commands, and migration details.

### Before (Categories)

```
Category Group: "Topics"
├── Technology
│   ├── AI
│   └── Web Development
├── Design
└── Business
```

### After (Structure Section)

```
Section: "Topics" (Structure, max levels: 2)
Entry Type: "Topic"
Fields: description, topicIcon, featured image, SEO fields
URI: topics/{slug}
```

The conversion preserves all content and relations. Craft 5.9.0 added **custom entry index pages** to solve the sidebar organization concern — you can now group entry sections in the CP sidebar just like category groups used to appear.

---

## CKEditor Content Patterns

CKEditor with nested entries is the primary rich text solution in Craft 5. It replaces Redactor and supports inline structured content.

### When to Use CKEditor vs Matrix

| Content need | CKEditor | Matrix |
|-------------|----------|--------|
| Long-form article with occasional media/embeds | Yes — natural writing flow | Overkill |
| Page builder with drag-reorder blocks | No — blocks aren't reorderable in CKEditor | Yes — blocks view mode |
| Rich text with inline CTAs, quotes, code blocks | Yes — nested entries as chunks | Possible but clunky |
| Data grid or repeating structured records | No | Yes — index view mode |
| Media gallery | No | Yes — cards-grid view mode |

### Nested Entry Types for CKEditor

Define entry types specifically for CKEditor nested content. Common patterns:

- **Image Block** — Assets field + caption (Plain Text) + credit (Plain Text)
- **Code Block** — Plain Text (monospaced) + codeLanguage (Dropdown)
- **CTA Block** — heading (Plain Text) + body (Plain Text) + Link field
- **Quote** — body (Plain Text) + attribution (Plain Text)
- **Video Embed** — Link field (URL type)
- **Info Box** — body (CKEditor, simple config) + style (Dropdown: info/warning/tip)

Give each entry type a distinctive **icon** and **color** so editors can identify them in the "+" menu.

### Front-End Rendering: The Chunks Pattern

CKEditor field values are iterable as "chunks" — alternating between HTML markup and nested entries:

```twig
{% for chunk in entry.articleBody %}
    {% if chunk.type == 'markup' %}
        <div class="prose">{{ chunk }}</div>
    {% elseif chunk.type == 'entry' %}
        {% include '_partials/entry/' ~ chunk.entry.type.handle ignore missing only %}
    {% endif %}
{% endfor %}
```

Create partial templates at `_partials/entry/{entryTypeHandle}.twig` for each nested entry type.

For simple output without chunks (no nested entries, or all nested entries use default rendering):

```twig
{{ entry.articleBody }}
```

### HTML Purifier

CKEditor content passes through HTML Purifier server-side. Configs live as JSON in `config/htmlpurifier/`. Key points:

- Custom CSS classes from the Styles plugin must be allowed in the Purifier config or they get stripped
- Media embeds require `URI.SafeIframeRegexp` for allowed domains
- The Purifier config is independent of CKEditor's client-side sanitization — both layers run

### Migration Commands

```bash
ddev craft ckeditor/convert/redactor              # Convert Redactor fields to CKEditor
ddev craft ckeditor/convert/matrix <fieldHandle>   # Convert Matrix field to CKEditor with nested entries
```

The Matrix conversion assigns all entry types to the new CKEditor field and generates a content migration.

---

## Content Architecture Decision Tree

```
Does the content need its own URL?
├── Yes → Section (Single, Channel, or Structure)
└── No
    ├── Is it a one-off value (footer text, site name)?
    │   └── Single with no URI + preloadSingles
    ├── Is it rich text with occasional structured content?
    │   └── CKEditor field with nested entries
    ├── Is it flexible/repeatable within a page?
    │   ├── Rich text with occasional structured blocks → CKEditor with nested entries
    │   └── Structured, reorderable blocks → Matrix field
    ├── Is it a single reusable field group (SEO, banner)?
    │   └── Content Block field (5.8.0+)
    └── Is it referenced from multiple places?
        └── Separate section + Entries relation field

Is the content hierarchical?
├── Yes → Structure section
└── No → Channel section

Does a Matrix field have 15+ entry types?
└── Yes → Split into multiple Matrix fields or separate sections

Will the content be queried independently across the site?
├── Yes → Separate section (not Matrix)
└── No → Matrix is fine
```

## Common Anti-Patterns

- **"God Matrix"** — one Matrix field with every content block type. Split into purpose-specific Matrix fields (body content, sidebar widgets, page header).
- **Duplicating data** — storing the same information in two places instead of using Entries relation fields.
- **Flat structure when hierarchy exists** — using a Channel with a "parent" Entries field instead of a Structure section with native hierarchy.
- **Over-relying on Globals** — globals lack drafts, revisions, preview. Use Singles.
- **Not planning for editors** — the content model should make sense to content authors, not just developers. Use clear entry type names, field instructions, and field layout tabs.
