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

### Count-Only Eager Loading

`count: true` in the criteria batches one `COUNT` per source element instead of
loading the related elements. The result is stored separately from eager-loaded
elements and is **only readable through `getEagerLoadedElementCount()`**:

```twig
{% set entries = craft.entries.section('blog').with([
    ['comments', { count: true }],
]).all() %}

{% for entry in entries %}
    {{ entry.getEagerLoadedElementCount('comments') }} comments   {# batched #}
    {{ entry.comments.count() }}                                 {# one COUNT query per entry #}
{% endfor %}
```

`entry.comments.count()` does not see the eager-loaded count: `ElementQuery::count()`
only consults eager-loaded counts when the query itself is `.eagerly()`, and the
cached-result shortcut only exists when the elements (not just the count) were
loaded. `getEagerLoadedElementCount()` returns `null` when nothing was loaded for
that handle. Two batched alternatives that need no special getter:

- `.with(['comments'])` loads the elements; `entry.comments.count()` then counts the cached result.
- `entry.comments.eagerly().count()` batches a count lazily across the query result (stored under its own `eagerly:comments` alias, so it does not reuse a `.with()` count).

### Link Fields Cannot Be Eager-Loaded

`craft\fields\Link` implements `RelationalFieldInterface` (so `relatedTo({ targetElement: page, field: 'ctaLink' })`
works for element links) but not `EagerLoadingFieldInterface`. `Element::eagerLoadingMap()`
skips it, so `.with(['ctaLink'])` and `.with(['ctaLink.image'])` load nothing, silently, and
the field value is still a `LinkData` object (no query to `.eagerly()`). Each `link.element`
runs its own query, memoised per link value for the request, so a listing of 50 entries
with distinct link targets is 50 queries. When a listing renders the linked element's
content (title, image, summary), use an Entries/Assets field, or collect the targets
yourself:

```twig
{% set ids = entries|map(e => e.ctaLink.element.id ?? null)|filter(id => id) %}
{% set targets = craft.entries.id(ids).indexBy('id').all() %}
```

Rendering only `link.url` and `link.label` is fine: those come from the stored value
without loading the element.

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

1. **Native attributes** — `.eagerly()` doesn't work for `author`, `uploader`, `photo`; they return the element, not a query. Use `.with()`. Exception: since Craft 5.8.0, `entry.author` and `entry.authors` batch themselves. The first access on an entry that came from a multi-result query eager-loads `authors` for every entry in that result (`Entry::getAuthors()`), so a plain `entry.author` inside a loop is one query, with or without `.with(['author'])`. Nothing further down is batched: `entry.author.photo` is still one query per author, so keep `.with(['author.photo'])` when you render author photos.
2. **`limit`, `offset`, `orderBy` before Craft 5.12** — filters such as `.type()`, `.status()` or `.relatedTo()` are passed to the batch query. `limit`, `offset` and `orderBy` are not (they live on Yii's base query, so `ElementQuery::getCriteria()` drops them). Inside a loop, `post.topics.eagerly().limit(3).all()` silently returns every topic. On a single-entry page it returns 3, because `.eagerly()` only batches when the source came from a multi-result query. Use `.with([['topics', {limit: 3}]])` or slice in Twig (`|slice(0, 3)`). Craft 5.12 applies all three to `.eagerly()` (#19994).
3. **One result per field handle** — every `.eagerly()` call on the same field shares the alias `eagerly:<handle>`. `block.children.eagerly().type('cta').all()` followed by `block.children.eagerly().type('quote').all()` returns the CTA set both times. Name each variant: `.eagerly('ctaChildren')`, `.eagerly('quoteChildren')`.
4. **Transform preloading** — No `withTransforms` equivalent. Use `.with()`.
5. **Auto-injected single entries** — `preloadSingles` entries aren't part of the query chain.
6. **Link fields** — no eager loading at all, lazy or upfront (see above).

## Eager-Loadable Native Attributes

| Attribute | Element Types |
|-----------|--------------|
| `author` / `authors` | Entries (self-batching across the query result since 5.8.0; `.with()` still needed for nested paths such as `author.photo`) |
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
- **Reading a `count: true` eager load through the field** — `entry.field.count()` ignores it and runs a `COUNT` per entry. Read it with `entry.getEagerLoadedElementCount('field')`, or eager-load the elements instead.
- **Putting a Link field in `.with()`** — it loads nothing and raises nothing. Link fields are not eager-loadable; see "Link Fields Cannot Be Eager-Loaded".
- **Dropping `.with(['author.photo'])` because `author` self-batches** — the batching stops at the authors. Author photos, addresses and custom user fields still need `.with()`.
