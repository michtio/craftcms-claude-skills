# Field Types Reference

All built-in field types in Craft CMS 5 with settings, Twig access, and query syntax. CKEditor (the primary rich text field) is a first-party plugin — see `content-patterns.md` for CKEditor content modeling patterns.

## Contents

- [Text & Input](#text--input) (Plain Text, Email, Link)
- [Number & Money](#number--money) (Number, Money, Range)
- [Date & Time](#date--time) (Date/Time, Time)
- [Option Fields](#option-fields) (Dropdown, Radio, Button Group, Checkboxes, Multi-Select)
- [Toggle & Visual](#toggle--visual) (Lightswitch, Color, Icon, Country)
- [Relational Fields](#relational-fields) (Entries, Assets, Categories, Tags, Users)
- [Structured Data](#structured-data) (Matrix, Table, JSON, Addresses, Content Block)
- [Matrix Configuration](#matrix-configuration) (entry types, view modes, nesting, versioning)

## Documentation

- Field types index: https://craftcms.com/docs/5.x/reference/field-types/
- Custom fields system: https://craftcms.com/docs/5.x/system/fields.html

Use `WebFetch` on specific field type doc pages for full setting details.

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

The Url field is deprecated since 5.3.0 and is now an alias for Link.

Extensible via `EVENT_REGISTER_LINK_TYPES` — plugins can register custom link types (e.g., internal route links, tel with extensions).

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

Returns `int|float|null`. Same as Number but renders as a slider in the CP. Since 5.5.0. Settings: min/max, step size, decimal points.

```twig
{{ entry.myField }}
```

Query: same as Number — `.myField('>= 50')`.

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

Returns `IconData|null` (`craft\fields\data\IconData`). Two properties: `name` (string, e.g., `'heart'`, `'arrow-right'`) and `styles` (array of available Font Awesome styles). Stored as a string in the database — the `styles` array is reconstructed at runtime from Craft's icon index.

Settings: `includeProIcons` (bool, whether to show Font Awesome Pro icons in the picker).

```twig
{# Icon name (IconData stringifies to the name) #}
{{ entry.myField }}            {# 'heart' #}
{{ entry.myField.name }}       {# 'heart' #}

{# Available styles #}
{{ entry.myField.styles|join(', ') }}   {# 'solid, regular, light' #}

{# Render as FontAwesome element #}
{{ tag('i', { class: 'fa-solid fa-' ~ entry.myField.name }) }}

{# Render as inline SVG from Craft's icon set #}
{% if entry.myField %}
    {{ svg("@appicons/#{entry.myField.name}.svg") }}
{% endif %}
```

Query: queryable as a string — `.myField('heart')`, `.myField(':notempty:')`.

### Country

Returns `Country|null`. Stored as two-letter code.

```twig
{{ entry.myField }}        {# 'BE' #}
{{ entry.myField.name }}   {# 'Belgium' (5.3.0+) #}
```

## Relational Fields

All relational fields return **element queries** (not arrays). Each access returns a fresh query copy.

Properties common to all relation fields (Entries, Assets, Categories, Tags, Users):

- `viewMode` — display mode in the CP: `'list'`, `'list-inline'`, `'thumbs'`, `'cards'`, `'cards-grid'` (since 5.9.0)
- `allowSelfRelations` (bool) — allow an element to relate to itself
- `localizeRelations` (bool) — maintain separate relations per site
- `defaultPlacement` (5.7.0) — `'beginning'` or `'end'` for newly added relations

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

Settings: `staticRows` (bool, 5.5.0) — predefined rows that can't be added/removed, only edited. `maxRows` / `minRows` — limit number of rows.

```twig
{% for row in entry.myField %}
    {{ row.columnHandle }}
{% endfor %}

{# Check if empty #}
{% if entry.myField|length %}
```

### JSON

Returns `array|null`. Raw JSON editor in the CP. Useful for storing structured data that doesn't fit other field types (API payloads, configuration blobs, custom metadata).

```twig
{{ entry.myField|json_encode }}
{% set data = entry.myField %}
{{ data.someKey }}
```

Query: not queryable by content.

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

Returns a single nested `ContentBlock` element (`craft\elements\ContentBlock`). Always exactly one per element — not repeatable. Ideal for reusable field groups (SEO metadata, banner config).

View modes: `grouped` (default, fields in a bordered group), `pane` (fields in a pane), `inline` (fields rendered inline with parent).

```twig
{{ entry.myContentBlock.metaTitle }}
{{ entry.myContentBlock.metaDescription }}
```

Cannot be nested within other Content Block fields.

## Matrix Configuration

### Entry Types in Matrix

Select from globally-defined entry types or create new ones. Entry types can be organized into named groups (5.8.0+). Local name/handle overrides available (5.6.0+).

### Entry Type Per-Usage Overrides (5.6.0+)

When an entry type is used in a section or Matrix field, its name, handle, and description can be overridden for that specific context. The original entry type is unchanged — the override only applies in that section/field. This allows one entry type to serve different semantic roles in different contexts.

### View Modes

| Mode | Best For | Since |
|------|----------|-------|
| **Blocks** | Page builders, inline editing. Classic collapse/expand + drag reorder. | 5.0.0 |
| **Cards** | Read-only overview. Double-click opens slideout editor. | 5.0.0 |
| **Cards Grid** | Media galleries, visual content. Grid layout of cards. | 5.9.0 |
| **Index** | Large datasets (100+ entries). Search, sort, filter, table toggle. | 5.0.0 |

### Matrix Properties

- `enableVersioning` (bool, 5.7.0) — version nested entries alongside owner (blocks mode) or independently (cards/index)
- `pageSize` (int) — pagination for index view mode
- `defaultTableColumns` (array) — columns shown in table view
- `defaultIndexViewMode` (string, 5.5.0) — default view in index mode
- `createButtonLabel` (string) — customize the "New entry" button text

Matrix entries can have their own URI formats and templates per site (5.0.0) — enabling nested entries to have independent URLs.

### Nesting

Matrix fields can contain entry types that themselves have Matrix fields. Use different view modes at each level to keep the UI manageable. Cards/Index modes open nested entries in slideouts.

### Twig Patterns

```twig
{# Basic block rendering #}
{% for block in entry.contentBlocks.all() %}
    {% include '_blocks/' ~ block.type.handle ignore missing only %}
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

Controlled by `enableVersioning`. Blocks view mode: nested entries versioned alongside owner. Cards/Index modes: independent versioning via slideout editor when enabled.
