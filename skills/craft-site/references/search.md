# Search

How Craft CMS 5's search system works for site builders: search syntax, Twig search queries, search indexing, configuration, and rebuilding. For extending search with custom searchable attributes (plugin development), see the craftcms skill's `elements.md`. For advanced search needs (Typesense, Algolia, Meilisearch), consider dedicated search service plugins.

## Documentation

- Search: https://craftcms.com/docs/5.x/system/searching.html
- Element queries: https://craftcms.com/docs/5.x/development/element-queries.html

## Common Pitfalls

- Enabling `subLeft` in `defaultSearchTermOptions` — forces `LIKE '%term%'` on every search, destroying performance on large datasets. Use only when absolutely needed for specific queries.
- Expecting search to find 1-2 character words — MySQL's default `innodb_ft_min_token_size` is 3. Words shorter than this are not indexed. Configure in MySQL, not Craft.
- Not rebuilding the search index after content modeling changes — new fields marked as searchable need `resave` with `--update-search-index` to populate the index.
- Passing raw user input to `.search()` without understanding enumeration risk — search syntax allows field-targeted queries (`body:secret`) that may reveal content structure.

## Contents

- [Search Syntax](#search-syntax)
- [Search in Twig](#search-in-twig)
- [Search Configuration](#search-configuration)
- [Search Indexing](#search-indexing)
- [Rebuilding the Search Index](#rebuilding-the-search-index)
- [Score and Ranking](#score-and-ranking)

## Search Syntax

Users and template queries can use these search operators:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `term` | Contains word | `salty` |
| `term1 term2` | Contains both (AND) | `salty dog` |
| `term1 OR term2` | Contains either | `salty OR sweet` |
| `-term` | Does not contain | `salty -dog` |
| `"exact phrase"` | Contains exact phrase | `"salty dog"` |
| `field:term` | Field contains word (substring) | `body:salty` |
| `field::term` | Field contains exact word | `body::salty` |
| `field::"exact phrase"` | Field contains exact phrase | `body::"salty dog"` |
| `-field:*` | Field is empty | `-body:*` |
| `field:*` | Field is not empty | `body:*` |
| `*term` | Ends with (wildcard left) | `*alty` |
| `term*` | Starts with (wildcard right) | `salt*` |
| `*term*` | Contains substring | `*alt*` |

`field` refers to the field handle (e.g., `body`, `summary`, `title`).

## Search in Twig

### Basic search

```twig
{% set results = craft.entries()
    .section('blog')
    .search(query)
    .all() %}
```

When `.search()` is used, results are ordered by search score by default.

### Search form

```twig
{# search/_form.twig #}
<form action="{{ url('search') }}" method="get">
    <input type="search"
           name="q"
           value="{{ craft.app.request.getQueryParam('q') }}"
           placeholder="Search...">
    <button type="submit">Search</button>
</form>
```

### Search results page

```twig
{# search/index.twig #}
{% set query = craft.app.request.getQueryParam('q') %}

{% if query %}
    {% set results = craft.entries()
        .search(query)
        .orderBy('score')
        .limit(20)
        .all() %}

    {% if results | length %}
        {% for entry in results %}
            <article>
                <h2><a href="{{ entry.url }}">{{ entry.title }}</a></h2>
                {% if entry.summary is defined and entry.summary %}
                    <p>{{ entry.summary | striptags | truncate(200) }}</p>
                {% endif %}
            </article>
        {% endfor %}
    {% else %}
        <p>No results found for "{{ query }}".</p>
    {% endif %}
{% endif %}
```

### Combining search with other filters

```twig
{% set results = craft.entries()
    .section('blog')
    .relatedTo(category)
    .search(query)
    .all() %}
```

Search works alongside all other query parameters. The `.search()` param adds a score-based ordering and keyword matching filter.

### Paginated search results

```twig
{% set query = craft.app.request.getQueryParam('q') %}

{% paginate craft.entries()
    .search(query)
    .limit(10) as pageInfo, results %}

{% for entry in results %}
    {# ... #}
{% endfor %}

{% include '_partials/pagination' with { pageInfo: pageInfo } only %}
```

### Multi-element search

```twig
{# Search across entries and assets #}
{% set entries = craft.entries().search(query).all() %}
{% set assets = craft.assets().search(query).all() %}
```

There is no built-in cross-element-type search query. Search each type separately and merge/interleave results in Twig if needed.

## Search Configuration

### General config settings

In `config/general.php`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `defaultSearchTermOptions` | `[]` | Default options applied to all search queries |

Options within `defaultSearchTermOptions`:

| Option | Default | Effect |
|--------|---------|--------|
| `subLeft` | `false` | Match beginning of words (`%term`). **Expensive.** |
| `subRight` | `true` | Match end of words (`term%`). Safe default. |
| `exclude` | `false` | Negate the term |
| `exact` | `false` | Require exact word match |

```php
// Only enable subLeft when you really need it
->defaultSearchTermOptions(['subLeft' => true])
```

### Search component config

In `config/app.php`:

```php
'components' => [
    'search' => [
        'useFullText' => true,        // MySQL only, ignored on PostgreSQL
        'minFullTextWordLength' => 3,  // Must match MySQL's innodb_ft_min_token_size
    ],
],
```

`useFullText` enables MySQL's FULLTEXT index for search. When `true`, Craft uses `MATCH() AGAINST()` queries. When `false`, falls back to `LIKE` queries (slower on large datasets).

`minFullTextWordLength` must match your MySQL server's `innodb_ft_min_token_size` setting. If MySQL is configured for minimum 4-character words but Craft thinks it's 3, short searches silently return no results.

## Search Indexing

### How indexing works

Craft stores search keywords in the `searchindex` table:

| Column | Purpose |
|--------|---------|
| `elementId` | The indexed element |
| `siteId` | Site context |
| `attribute` | Attribute or field handle |
| `fieldId` | Field ID (null for native attributes) |
| `keywords` | Normalized keyword text |

When an element is saved, Craft clears and rebuilds all search index rows for that element. Keywords are normalized (lowercased, stripped of punctuation) before insertion.

### What is indexed by default

| Element Type | Default Indexed Attributes |
|-------------|--------------------------|
| Entries | `title`, `slug` |
| Assets | `filename`, `extension`, `kind` |
| Users | `username`, `firstName`, `lastName`, `fullName`, `email` |
| Tags/Categories | `title` |

Custom fields are indexed when "Use this field's values as search keywords" is enabled in the field layout designer.

### Making custom fields searchable

In the field layout designer (CP), click a field's gear icon and enable "Use this field's values as search keywords." This setting is per-field-layout-element, not per-field — the same field can be searchable in one layout and not in another.

After enabling, resave affected elements to populate the index.

## Rebuilding the Search Index

| Command | When to Use |
|---------|-------------|
| `ddev craft resave/entries --update-search-index` | After enabling search on existing fields |
| `ddev craft resave/entries --section=blog --update-search-index` | Rebuild for a specific section |
| `ddev craft resave/entries --update-search-index --queue` | Async rebuild via queue |
| `ddev craft search/reindex` | Full rebuild of entire search index (after changing search component config) |

`resave` with `--update-search-index` is selective — only re-indexes the specified elements. `search/reindex` truncates and rebuilds the entire search index.

## Score and Ranking

Search results include a relevance score that determines default ordering. Approximate relative weights (varies by search mode and Craft version):

| Match Type | Approximate Weight |
|-----------|-------------------|
| Title match | Very high |
| Exact word match | Very high |
| Phrase match | High |
| Substring match | Medium |
| Body match | Base |

### Ordering by score

```twig
{# Results ordered by relevance (default when .search() is used) #}
{% set results = craft.entries().search(query).all() %}

{# Explicit score ordering #}
{% set results = craft.entries().search(query).orderBy('score').all() %}

{# Override: order by date instead of score #}
{% set results = craft.entries().search(query).orderBy('postDate DESC').all() %}
```

### Accessing search scores

Each element in search results has a `searchScore` attribute:

```twig
{% for entry in results %}
    {# searchScore is a float, higher = more relevant #}
    {# Only populated when .search() is used in the query — null otherwise #}
    <p>{{ entry.title }} (score: {{ entry.searchScore }})</p>
{% endfor %}
```

### When to use a dedicated search service

Craft's built-in search is adequate for most sites. Consider a dedicated service (Typesense, Algolia, Meilisearch) when you need:

- Fuzzy matching and typo tolerance
- Faceted search and filtering
- Search across 100k+ elements with sub-100ms response
- Autocomplete/suggestions
- Synonym handling
