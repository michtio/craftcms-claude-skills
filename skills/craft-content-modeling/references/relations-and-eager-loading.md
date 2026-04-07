# Relations & Eager Loading

How content connects in Craft CMS 5 — relatedTo queries, eager loading with
`.with()`, and lazy eager loading with `.eagerly()`.

## Documentation

- Relations: https://craftcms.com/docs/5.x/system/relations.html
- Eager loading: https://craftcms.com/docs/5.x/development/eager-loading.html
- Element queries: https://craftcms.com/docs/5.x/development/element-queries.html

## Relation Basics

Every relation has a **source** (element with the relational field) and a
**target** (the selected element). Relations are stored in a `relations` table.

Accessing a relational field returns a **new element query** each time — parameters
don't persist between accesses:

```twig
{# These are two separate queries #}
{% set query = entry.relatedEntries %}
{% set all = entry.relatedEntries.all() %}
```

## relatedTo() — Four Shapes

### 1. Simple (bidirectional)

Finds elements related in **either** direction:

```twig
{% set related = craft.entries.relatedTo(myEntry).all() %}
{% set related = craft.entries.relatedTo(42).all() %}
```

### 2. Array of elements (OR logic)

Related to **any** of the given elements:

```twig
{% set recipes = craft.entries.relatedTo([protein, veggie]).all() %}
```

### 3. AND logic

Related to **all** of the given elements:

```twig
{% set recipes = craft.entries.relatedTo(['and', protein, veggie]).all() %}
```

### 4. Directional hash

Specify the relationship direction:

```twig
{# "Given this source, find its targets" #}
{% set targets = craft.entries.relatedTo({
    sourceElement: recipe,
}).all() %}

{# "Given this target, find what points to it" #}
{% set sources = craft.entries.relatedTo({
    targetElement: ingredient,
}).all() %}

{# Scope to a specific field #}
{% set sources = craft.entries.relatedTo({
    targetElement: category,
    field: 'topics',
}).all() %}

{# Matrix relations use dot notation #}
{% set sources = craft.entries.relatedTo({
    targetElement: image,
    field: 'contentBlocks.photos',
}).all() %}
```

### Compound Criteria

```twig
{# Must be related to origin AND any of the proteins #}
{% set results = craft.entries
    .relatedTo(origin)
    .andRelatedTo(proteins)
    .all() %}

{# Exclude elements related to allergen #}
{% set safe = craft.entries
    .relatedTo(category)
    .notRelatedTo(allergen)
    .all() %}
```

## Eager Loading with .with()

Batch-loads related elements upfront, solving the N+1 query problem. Use on
**listing pages** where you display related content for multiple entries.

### Basic Usage

```twig
{% set entries = craft.entries.section('blog').with([
    'featuredImage',
    'topics',
    'author',
]).all() %}

{# Access as normal — data is already loaded #}
{% for entry in entries %}
    {{ entry.featuredImage.one().getUrl('thumb') }}
{% endfor %}
```

### With Criteria

Add query criteria to eager-loaded relations:

```twig
{% set entries = craft.entries.with([
    ['relatedArticles', { limit: 3, orderBy: 'postDate DESC' }],
    ['featuredImage', { withTransforms: ['hero', 'thumb'] }],
]).all() %}
```

### Nested Eager Loading

Dot notation for relations within relations:

```twig
{% set entries = craft.entries.with([
    'topics',
    'topics.thumbnail',
    'author',
    'author.photo',
]).all() %}
```

### Matrix Eager Loading

Prefix with entry type handle for Matrix nested relations:

```twig
{% set entries = craft.entries.with([
    'contentBlocks',
    'contentBlocks.image:photos',
    'contentBlocks.quote:author',
]).all() %}
```

### Transform Eager Loading

Pre-generate image transforms:

```twig
{% set entries = craft.entries.with([
    ['heroImage', { withTransforms: ['large', 'thumb'] }],
]).all() %}
```

## Lazy Eager Loading with .eagerly()

New in Craft 5. Defers batch-loading to the point of use — simpler API,
works in partials without upstream coordination.

```twig
{% set posts = craft.entries.section('news').all() %}
{% for post in posts %}
    {% set image = post.featuredImage.eagerly().one() %}
    {% for topic in post.topics.eagerly().all() %}
        {% set icon = topic.thumbnail.eagerly().one() %}
    {% endfor %}
{% endfor %}
```

### When to use which

| Scenario | Use |
|----------|-----|
| You know exactly which relations are needed | `.with()` |
| Relations are accessed in reusable partials | `.eagerly()` |
| You need transform preloading | `.with()` + `withTransforms` |
| Mixed — some known upfront, some in partials | Combine both |

### .eagerly() Limitations

1. **Native attributes** — `.eagerly()` doesn't work for `author`, `uploader`, `photo`. Use `.with()`.
2. **Custom criteria on relations** — `.eagerly()` loads all related elements. Use `.with()` to filter/limit.
3. **Entry-type scoping in Matrix** — `.eagerly()` can't scope by entry type. Use `.with()` with type-prefixed paths.
4. **Transform preloading** — No `withTransforms` equivalent. Use `.with()`.
5. **Auto-injected single entries** — `preloadSingles` entries aren't part of the query chain.

## Eager-Loadable Native Attributes

| Attribute | Element Types |
|-----------|--------------|
| `author` / `authors` | Entries |
| `uploader` | Assets |
| `photo` | Users |
| `addresses` | Users |
| `parent` / `ancestors` | Structure entries, categories |
| `children` / `descendants` | Structure entries, categories |
| `localized` | All elements |
| `drafts` / `revisions` | All elements |
| `currentRevision` | All elements |
| `owner` / `primaryOwner` | Nested entries |

## Common Pitfalls

- **Forgetting `.eagerly()` in loops** — the #1 performance mistake. Every relational field inside a `{% for %}` should use `.eagerly()` or be covered by an upstream `.with()`.
- **Using `.relatedTo(entry)` when you mean `.relatedTo({ sourceElement: entry })`** — the simple form is bidirectional. If you only want one direction, use the hash form.
- **Not scoping `.relatedTo()` to a field** — without `field: 'myField'`, it matches relations via ANY field. This gives unexpected results when multiple relation fields exist.
- **Eager loading transforms without `withTransforms`** — images load but transforms aren't pre-generated, causing on-demand generation.
- **Deeply nested `.with()` paths** — `'a.b.c.d.e'` works but generates complex queries. Keep nesting to 2-3 levels max.
