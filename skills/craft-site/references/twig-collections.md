# Twig Collections Reference

> `collect()` method reference for Craft CMS Twig templates.
> Craft CMS exposes Laravel's Collection class to Twig via the `collect()` function.

## Documentation

- Laravel Collections: https://laravel.com/docs/11.x/collections
- Craft element queries: https://craftcms.com/docs/5.x/development/element-queries.html
- Twig arrow functions: https://twig.symfony.com/doc/3.x/templates.html#arrow-functions

## Common Pitfalls

- `.all()` returns arrays, `.collect` returns Collections — use `.collect` when you need Collection methods.
- Arrow functions in Twig have no multiline support — keep them as single expressions.
- `merge()` overwrites keys — if you merge `{ color: 'new' }` into a collection with a `color` key, the old value is gone. This is the intended override mechanism.
- `implode()` joins null values as empty strings, producing extra spaces — harmless for HTML class attributes (browsers normalize whitespace). Use `classes.filter(v => v).implode(' ')` for pristine output if needed.
- Collections are immutable — `merge()`, `filter()`, etc. return new Collections. Reassign: `set classes = classes.merge({})`.

## Creating Collections

```twig
{# From a hash (most common — props and classes) #}
{%- set props = collect({
    heading: heading ?? null,
    content: content ?? null,
    utilities: utilities ?? null,
}) -%}

{# From an array #}
{%- set items = collect(['one', 'two', 'three']) -%}

{# From a query result #}
{%- set entries = craft.entries.section('blog').collect -%}
```

## Methods Used in Templates

### Accessing Values

| Method | Description | Example |
|--------|-------------|---------|
| `get(key)` | Get value by key, null if missing | `props.get('heading')` |
| `get(key, default)` | Get value with fallback | `props.get('size', 'text-base')` |
| `first` | First item | `entries.first` |
| `last` | Last item | `entries.last` |
| `count` | Number of items | `entries.count` |
| `isEmpty` | True if empty | `props.get('items').isEmpty` |
| `isNotEmpty` | True if not empty | `entries.isNotEmpty` |

### Transforming

| Method | Description | Example |
|--------|-------------|---------|
| `merge(hash)` | Merge values (overwrites existing keys) | `props.merge({ color: 'bg-red-500' })` |
| `map(arrow)` | Transform each item | `entries.map(e => e.title)` |
| `pluck(key)` | Extract single field | `entries.pluck('title')` |
| `implode(glue)` | Join values as string | `classes.implode(' ')` |
| `join(glue)` | Alias for implode | `items.join(', ')` |
| `values` | Reset keys to sequential | `collection.values` |
| `keys` | Get all keys | `props.keys` |
| `flatten` | Flatten nested arrays | `nested.flatten` |

### Filtering

| Method | Description | Example |
|--------|-------------|---------|
| `filter(arrow)` | Keep items matching condition | `classes.filter(v => v)` |
| `reject(arrow)` | Remove items matching condition | `items.reject(i => i.isEmpty)` |
| `where(key, value)` | Filter by key-value | `entries.where('type', 'article')` |
| `whereIn(key, values)` | Filter by key in array | `entries.whereIn('sectionId', [1, 2])` |
| `unique` | Remove duplicates | `tags.unique` |
| `contains(value)` | Check if value exists | `items.contains('featured')` |

### Sorting

| Method | Description | Example |
|--------|-------------|---------|
| `sort` | Sort ascending | `items.sort` |
| `sortBy(key)` | Sort by field | `entries.sortBy('title')` |
| `sortByDesc(key)` | Sort descending by field | `entries.sortByDesc('postDate')` |
| `reverse` | Reverse order | `items.reverse` |

### Slicing

| Method | Description | Example |
|--------|-------------|---------|
| `take(n)` | First n items | `entries.take(3)` |
| `skip(n)` | Skip first n items | `entries.skip(1)` |
| `slice(start, length)` | Subset | `entries.slice(0, 5)` |
| `chunk(size)` | Split into groups | `entries.chunk(3)` |
| `groupBy(key)` | Group by field | `entries.groupBy('section')` |

### Checking

| Method | Description | Example |
|--------|-------------|---------|
| `has(key)` | Key exists | `props.has('icon')` |
| `contains(value)` | Value exists in collection | `tags.contains('featured')` |
| `every(arrow)` | All items match | `items.every(i => i > 0)` |
| `some(arrow)` | Any item matches | `items.some(i => i == 'active')` |

## Arrow Functions in Twig

Twig supports arrow functions for Collection methods:

```twig
{# Single parameter #}
entries.map(e => e.title)
entries.filter(e => e.heroImage.exists())
entries.sortBy(e => e.postDate)

{# With index/key #}
items.filter((value, key) => key != 'utilities')

{# Chaining #}
entries
    .filter(e => e.heroImage.exists())
    .sortByDesc(e => e.postDate)
    .take(6)
    .map(e => {
        title: e.title,
        url: e.url,
        image: e.heroImage.one(),
    })
```

## Common Patterns

### Props Collection

```twig
{# Standard props pattern #}
{%- set props = collect({
    heading: heading ?? null,
    content: content ?? null,
    button: button ?? null,
    image: image ?? null,
    utilities: utilities ?? null,
}) -%}

{# Access #}
props.get('heading')
props.get('size', 'text-base')

{# Merge additional props in variant #}
{%- set props = props.merge({
    icon: icon ?? null,
    badge: badge ?? null,
}) -%}
```

### Class Collection (Named Keys)

```twig
{# Build classes with named concerns #}
{%- set classes = collect({
    layout: 'flex flex-col gap-4',
    color: 'bg-brand-surface text-brand-heading',
    spacing: 'p-6',
    radius: 'rounded-lg',
    shadow: 'shadow-md',
    utilities: props.get('utilities'),
}) -%}

{# Render #}
class="{{ classes.implode(' ') }}"

{# Override a slot #}
{%- set classes = classes.merge({ color: 'bg-brand-primary text-brand-on-primary' }) -%}

{# Filter out null/empty values before imploding #}
class="{{ classes.filter(v => v).implode(' ') }}"
```

### Entry Queries as Collections

```twig
{# Use .collect instead of .all() for Collection methods #}
{%- set articles = craft.entries
    .section('blog')
    .limit(10)
    .eagerly()
    .collect
-%}

{# Now use Collection methods #}
{%- set featured = articles.filter(a => a.featured).first -%}
{%- set rest = articles.reject(a => a.featured).take(6) -%}
{%- set tags = articles.pluck('tags').flatten.unique -%}
```

### Building Data Structures

```twig
{# Build navigation items from entries #}
{%- set items = craft.entries
    .section('pages')
    .level(1)
    .collect
    .map(e => collect({
        title: e.title,
        url: e.url,
        active: craft.app.request.url == e.url,
        children: e.children.collect.map(c => collect({
            title: c.title,
            url: c.url,
        })),
    }))
-%}
```

### Conditional Class Composition

```twig
{# Classes that vary based on props #}
{%- set classes = collect({
    layout: 'grid gap-4',
    columns: props.get('columns') == 2 ? 'lg:grid-cols-2' : 'lg:grid-cols-3',
    color: props.get('inverted') ? 'bg-brand-primary text-brand-on-primary' : 'bg-brand-surface',
    utilities: props.get('utilities'),
}) -%}
```