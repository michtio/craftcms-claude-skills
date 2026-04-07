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
- **Topic** — title, description (Plain Text), icon (Icon or Assets)

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
- **Service** — title, description (Plain Text), icon (Icon)

### Key Decisions

- Clients as separate section — one client, many projects. Query `craft.entries.section('projects').relatedTo({ targetElement: client, field: 'client' })` for all projects by a client
- Services as Structure — supports parent/child grouping (Design → UI Design, Brand Design)
- Featured Lightswitch — filters homepage showcase: `craft.entries.section('projects').myFeatured(true)`

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
Fields: description, icon, featured image, SEO fields
URI: topics/{slug}
```

### Migration

```bash
ddev craft entrify/categories topics
```

This converts the category group to a section, categories to entries, and
category fields to entries fields. Existing relations are preserved.

### Entries Field Configuration

For hierarchical selection (mimicking categories field behavior), enable
**Maintain Hierarchy** on the Entries field. This auto-selects ancestors when
a nested entry is chosen.

### Tags Replacement

For flat taxonomies where editors created terms on-the-fly, use a Channel
section. The on-the-fly creation UX is not yet available for Entries fields —
this is the one area where the legacy Tags field still has a UX advantage.

---

## Content Architecture Decision Tree

```
Does the content need its own URL?
├── Yes → Section (Single, Channel, or Structure)
└── No
    ├── Is it a one-off value (footer text, site name)?
    │   └── Single with no URI + preloadSingles
    ├── Is it flexible/repeatable within a page?
    │   └── Matrix field
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
