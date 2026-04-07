# Field Types Reference

All 26 built-in field types in Craft CMS 5 with settings, Twig access, and query syntax.

## Documentation

- Field types index: https://craftcms.com/docs/5.x/reference/field-types/
- Custom fields system: https://craftcms.com/docs/5.x/system/fields.html

Use `web_fetch` on specific field type doc pages for full setting details.

## Text & Input

### Plain Text

Returns `string|null`. Settings: UI mode (normal/enlarged), placeholder, character limit, byte limit, monospaced font, allow line breaks (textarea with configurable rows).

```twig
{{ entry.myField }}
{% if entry.myField|length > 100 %}...{% endif %}
```

Query: `.myField('value')`, `.myField('PASTEL-*')` (wildcards), `.myField(':empty:')`, `.myField(':notempty:')`.

### Email

Returns `string|null`. Validates email format automatically.

```twig
<a href="mailto:{{ entry.myField }}">{{ entry.myField }}</a>
```

### Link (replaced URL field in 5.3)

Returns `LinkData|null`. Supports URL, Asset, Category, Email, Entry, Phone, SMS link types. Settings: allowed link types, custom label, target/rel/ARIA attributes (5.6.0+).

```twig
{# Full <a> tag with all attributes #}
{{ entry.myField.link }}

{# Individual properties #}
{{ entry.myField.value }}     {# raw URL/value #}
{{ entry.myField.label }}     {# link text #}
{{ entry.myField.type }}      {# 'url', 'entry', 'asset', etc. #}
{{ entry.myField.element }}   {# related element when linking to entry/asset #}
{{ entry.myField.target }}    {# '_blank' or null #}
```

## Number & Money

### Number

Returns `int|float|null`. Settings: min/max, step size, decimal points, prefix/suffix.

```twig
{{ entry.myField }}
{{ entry.myField|number }}  {# formatted with locale #}
```

Query: `.myField('>= 100')`, `.myField('< 50')`.

### Money

Returns `Money\Money|null`. Stored as integers in minor units ($123.45 → 12345).

```twig
{{ entry.myField|money }}     {# formatted: $123.45 #}
{{ entry.myField.amount }}    {# raw: 12345 #}
{{ entry.myField.currency }}  {# Currency object #}
```

**Use `|money` not `|currency`.** Query uses natural values: `.myField('>= 123.45')`.

### Range

Returns `int|float|null`. Same as Number but renders as a slider in the CP.

## Date & Time

### Date/Time

Returns `DateTime|null`. Stored in UTC. Settings: date only or date+time, minute increment, min/max date.

```twig
{{ entry.myField|date('F j, Y') }}
{{ entry.myField|datetime('short') }}
{{ entry.myField|atom }}                {# ISO 8601 #}
{{ entry.myField|timestamp }}           {# Unix timestamp #}
<time datetime="{{ entry.myField|atom }}">{{ entry.myField|date('M j') }}</time>
```

Query: `.myField('>= 2025-01-01')`, `.myField('< now')`, `.myField(['and', '>= 2025-01-01', '< 2025-07-01'])`.

### Time

Returns `DateTime|null`. Stored as `H:i` string, hydrated to DateTime.

```twig
{{ entry.myField|time('short') }}
```

## Option Fields

### Single Option (Dropdown / Radio Buttons / Button Group)

All return `SingleOptionFieldData|null`.

```twig
{{ entry.myField.value }}   {# stored value #}
{{ entry.myField.label }}   {# display label #}
{{ entry.myField }}          {# outputs value #}

{# Comparison #}
{% if entry.myField.value == 'featured' %}
```

Radio Buttons support "other" option (5.5.0+). Button Group supports icon/color options (5.7.0+).

### Multi Option (Checkboxes / Multi-Select)

Return `MultiOptionsFieldData`.

```twig
{% for option in entry.myField %}
    {{ option.label }} ({{ option.value }})
{% endfor %}

{# Check for specific value #}
{% if entry.myField.contains('vegan') %}
```

## Toggle & Visual

### Lightswitch

Returns `bool`. Settings: default value, ON/OFF labels.

```twig
{% if entry.myField %}Featured{% endif %}
```

**Gotcha:** Elements without an explicit value use the field default. This can unexpectedly exclude entries from other sections. Use strict matching: `.myField({ value: true, strict: true })`.

### Color

Returns `ColorData|null`. Settings: predefined palette (5.6.0+), allow custom colors.

```twig
{{ entry.myField }}        {# hex: #ff0000 #}
{{ entry.myField.hex }}
{{ entry.myField.rgb }}    {# rgb(255,0,0) #}
{{ entry.myField.hsl }}
{{ entry.myField.luma }}   {# 0-1 luminance for contrast decisions #}
```

### Icon

Returns icon data from FontAwesome set.

```twig
{{ tag('i', { class: 'fa-solid fa-' ~ entry.myField.name }) }}
```

### Country

Returns `Country|null`. Stored as two-letter code.

```twig
{{ entry.myField }}        {# 'BE' #}
{{ entry.myField.name }}   {# 'Belgium' (5.3.0+) #}
```

## Relational Fields

All relational fields return **element queries** (not arrays). Each access returns a fresh query copy.

### Entries

Returns `EntryQuery`. Sources filter by section. Settings: Maintain Hierarchy, Branch Limit, Min/Max Relations, View Mode.

```twig
{% set related = entry.myField.all() %}
{% set first = entry.myField.one() %}
{% set count = entry.myField.count() %}
{% set exists = entry.myField.exists() %}

{# With additional criteria #}
{% set recent = entry.myField.orderBy('postDate DESC').limit(3).all() %}

{# Eager loading in loops #}
{% set items = entry.myField.eagerly().all() %}
```

### Assets

Returns `AssetQuery`. Sources filter by volume. Settings: restrict upload location, allowed file types, min/max.

```twig
{% set image = entry.myField.one() %}
{% if image %}
    <img src="{{ image.getUrl('thumb') }}" alt="{{ image.alt }}">
{% endif %}

{# Multiple images #}
{% for image in entry.myField.all() %}
    {{ image.getImg('gallery') }}
{% endfor %}
```

### Categories (legacy — use Entries field for new projects)

Returns `CategoryQuery`. Single source group. Selecting a nested category auto-selects ancestors.

### Tags (legacy — use Entries field for new projects)

Returns `TagQuery`. Single source group. Authors create tags on-the-fly.

### Users

Returns `UserQuery`. Sources filter by user group.

```twig
{% set author = entry.myField.one() %}
{% if author %}
    {{ author.fullName }} — {{ author.email }}
{% endif %}
```

## Structured Data

### Matrix

Returns `EntryQuery` of nested entries. The most powerful field type — see detailed section below.

### Table

Returns `array` of row arrays. Column types: checkbox, color, date, dropdown, email, lightswitch, multi-line text, number, single-line text, time, URL, row heading.

```twig
{% for row in entry.myField %}
    {{ row.columnHandle }}
{% endfor %}

{# Check if empty #}
{% if entry.myField|length %}
```

### Addresses

Returns `AddressQuery`. Owned by parent element (not relational).

```twig
{% set address = entry.myField.one() %}
{{ address|address }}           {# formatted output #}
{{ address.addressLine1 }}
{{ address.locality }}
{{ address.countryCode }}
```

### Content Block (5.8.0+)

Returns a single nested `Entry`. Always exactly one entry per element — not repeatable. Ideal for reusable field groups (SEO metadata, banner config).

```twig
{{ entry.myContentBlock.metaTitle }}
{{ entry.myContentBlock.metaDescription }}
```

Cannot be nested within other Content Block fields.

## Matrix Configuration

### Entry Types in Matrix

Select from globally-defined entry types or create new ones. Entry types can be organized into named groups (5.8.0+). Local name/handle overrides available (5.6.0+).

### View Modes

| Mode | Best For |
|------|----------|
| **Blocks** | Page builders, inline editing. Classic collapse/expand + drag reorder. |
| **Cards** | Read-only overview. Double-click opens slideout editor. |
| **Card Grid** (5.9.0+) | Media galleries, visual content. |
| **Index** | Large datasets (100+ entries). Search, sort, filter, table toggle. |

### Nesting

Matrix fields can contain entry types that themselves have Matrix fields. Use different view modes at each level to keep the UI manageable. Cards/Index modes open nested entries in slideouts.

### Twig Patterns

```twig
{# Basic block rendering #}
{% for block in entry.contentBlocks.all() %}
    {% include '_blocks/' ~ block.type.handle ignore missing %}
{% endfor %}

{# Filter by type #}
{% set images = entry.contentBlocks.type('image').all() %}

{# Eager load nested relations #}
{% set blocks = entry.contentBlocks.with(['image:photos']).all() %}

{# Check if Matrix field has content #}
{% if entry.contentBlocks.exists() %}

{# Access owner from inside a nested entry #}
{{ entry.owner.title }}
```

### Versioning (5.7.0+)

Blocks view mode: nested entries versioned alongside owner. Cards/Index modes: independent versioning via slideout editor when enabled.
