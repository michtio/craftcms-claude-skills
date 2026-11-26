# Field Types Reference

All built-in field types in Craft CMS 5 with settings, Twig access, and query syntax. CKEditor (the primary rich text field) is a first-party plugin — see `content-patterns.md` for CKEditor content modeling patterns.

## Contents

- [Settings Every Field Has](#settings-every-field-has) (Default Tip / Default Warning)
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

## Settings Every Field Has

- **Default Tip / Default Warning** [5.12+]: a tip or warning shown under the field in every layout it's placed in (project config keys `tip` and `warning` on the field; `new PlainText(['tip' => '…', 'warning' => '…'])` from a migration or `saveField()`). A Tip or Warning set on the field layout element overrides it; left blank, the layout element falls back to the default, translated with the `site` category. The layout designer shows the defaults as placeholders. Before 5.12: set the tip or warning on each field layout element.

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

### Link [5.3+] (replaces the URL field)

Returns `LinkData|null`. Supports URL, Asset, Category, Email, Entry, Phone, SMS link types. Settings: allowed link types, custom label, target/rel/ARIA attributes [5.6+].

Serialising a `LinkData` value (`toArray()`, an Element API transformer that returns the raw value, `|json_encode`) [changed 5.11] yields a full array: `type`, `value`, `url`, `label`, `filename`, `link`, `attributes`, `defaultLabel`, `elementType`, `elementId`, `elementSiteId`, `elementTitle`. Before 5.11 the array was sparse, so API code had to call `getUrl()`/`getLabel()`/`getElement()` itself — keep doing that when the project must run on both.

The Url field is [deprecated 5.3] and is now an alias for Link.

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

Returns `int|float|null`. Same as Number but renders as a slider in the CP. [5.5+] Settings: min/max, step size, decimal points.

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

Radio Buttons support "other" option [5.5+]. Button Group supports icon/color options [5.7+].

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

Returns `ColorData|null` (`craft\fields\data\ColorData`). Settings: predefined palette [5.6+] (palette colours can be translucent [5.12+]), allow custom colors, allow opacity for custom colors (`allowCustomAlpha`, default off) [5.12+], GraphQL Mode (`fullGraphqlData`) [5.12+].

```twig
{{ entry.myField }}                {# hex: #ff0000, or #ff000080 when translucent [changed 5.12] #}
{{ entry.myField.hex }}            {# same as above #}
{{ entry.myField.getHex(false) }}  {# always 6-digit, every version #}
{{ entry.myField.rgb }}            {# rgb(255,0,0); ignores alpha #}
{{ entry.myField.hsl }}            {# ignores alpha #}
{{ entry.myField.luma }}           {# 0-1 luminance; ignores alpha #}

{# [5.12+] alpha-aware output #}
{{ entry.myField.alpha }}          {# 0.5 (1.0 for opaque) #}
{{ entry.myField.rgba }}           {# rgba(255,0,0,0.5) #}
{{ entry.myField.hsla }}
{{ entry.myField.oklch }}          {# oklch(... / 0.5); alpha part only when < 1 #}
{{ entry.myField.rgbChannels }}    {# 255 0 0, for rgb(var(--x) / 50%) #}
{{ entry.myField.contrastColor }}  {# #000000 or #ffffff (WCAG 2, ignores alpha) #}
{{ entry.myField.contrastRatio('#ffffff') }}  {# 1-21; PHP: getContrastRatio() #}
```

**Alpha and storage** [changed 5.12]: values are normalized to lowercase hex; 3/4-digit shorthand is expanded and a fully opaque `ff` alpha is stripped, so opaque colours stay 6-digit and only translucent ones are stored as `#rrggbbaa`. Existing values don't change, and nothing turns 8-digit until an editor picks a translucent palette colour or a field allows opacity. Before 5.12: always `#rrggbb`. A translucent value submitted from a front-end form or GraphQL mutation is rejected unless it's a palette colour or the field allows custom opacity.

**What breaks with 8-digit hex** [changed 5.12]:

- Appending alpha by concatenation: `{{ entry.brand }}80`, `entry.brand.hex ~ '1a'`, or `|slice(1)` to strip the `#` all produce an invalid 10-digit colour. Use `style="--brand: {{ entry.brand.rgbChannels }}"` with `rgb(var(--brand) / 50%)` in CSS, or `entry.brand.rgba` [5.12+]. `entry.brand.getHex(false) ~ '80'` works on every version.
- `<input type="color" value="{{ entry.brand }}">` accepts only `#rrggbb`: use `getHex(false)`.
- HTML email, JS libraries, SVG attributes and regexes like `/^#[0-9a-f]{6}$/` that expect six digits: use `getHex(false)` plus a separate opacity, or `rgba`.
- `rgb`, `hsl`, `luma` and the contrast helpers ignore alpha, so a translucent colour renders opaque and `contrastColor` is computed as if it were opaque. Use `rgba`/`hsla` when alpha matters.
- Supporting older releases [5.12+]: `alpha`, `rgba`, `hsla`, `oklch`, `rgbChannels`, `contrastColor` and `contrastRatio()` don't exist before 5.12 (with Dev Mode on, strict variables make them throw). `getHex(false)` is safe everywhere (older `getHex()` ignores the extra argument).

**GraphQL Mode** [5.12+]: Full data (a `ColorData` object) is the default for fields created in 5.12, including fields created through `saveField()` or migrations without `fullGraphqlData`; existing fields stay Hex only (a string, which can be 8-digit). A headless query written as `{ brandColor }` against a new field fails with "must have a selection of subfields". Before 5.12: always a hex string. See the `craftcms` skill's `graphql.md` (Field Type GraphQL Modes).

### Icon

Returns `IconData|null` (`craft\fields\data\IconData`) [5.8+]. Properties: `name` (string, e.g., `'heart'`), `styles` (array of available Font Awesome styles; empty for custom icons) and `set` [5.12+] (`null` for Font Awesome, otherwise the set handle). Methods [5.12+]: `getSvg()` (`icon.svg`, a sanitized SVG string or `null` if the icon no longer exists) and `getKeywords()` (`icon.keywords`).

Settings: `includeProIcons` (bool, Font Awesome Pro icons; applies only when Font Awesome is selected), `iconSets` [5.12+] (which sets the picker offers; defaults to `['fontawesome']`, shown only when a custom set is registered).

**Custom icon sets** [5.12+]:

- `customIconPath` [5.12+] in `config/general.php` (env `CRAFT_CUSTOM_ICON_PATH`), for example `->customIconPath('@root/icons')`, registers a set with handle `custom`. Only `*.svg` files directly in that directory count; the filename without `.svg` is the icon name.
- Plugins and modules register sets through `Icons::EVENT_REGISTER_ICON_SETS`. Handles match `/^[a-zA-Z][\w\-]*$/`; `fontawesome` is reserved.
- Existing Icon fields keep offering Font Awesome only until the field's Icon Sets setting is edited (a project config change).
- Custom-set icons are stored as `set:name` (`custom:rocket`); Font Awesome icons stay a bare name. `{{ entry.myField }}` still prints only the name, without the set.
- Renaming or deleting an SVG orphans stored values: `svg` returns `null` and nothing validates it.

[5.12+] Before 5.12: Font Awesome only, stored as the bare name, with only `name` and `styles`.

```twig
{# Icon name (IconData stringifies to the name, without the set) #}
{{ entry.myField }}            {# 'heart' #}
{{ entry.myField.name }}       {# 'heart' #}

{# Available Font Awesome styles #}
{{ entry.myField.styles|join(', ') }}   {# 'solid, regular, light' #}

{# Render either kind [5.12+]: branch on the set #}
{% set icon = entry.myField %}
{% if icon and icon.set is null %}
    {{ tag('i', { class: 'fa-solid fa-' ~ icon.name, aria: { hidden: 'true' } }) }}
{% elseif icon %}
    {{ icon.svg|raw }}
{% endif %}

{# Font Awesome only (every version, or fields without custom sets) #}
{% if entry.myField %}
    {{ svg("@appicons/#{entry.myField.name}.svg") }}
{% endif %}
```

Templates that assume Font Awesome (`'fa-solid fa-' ~ name`, `svg("@appicons/…")`) break for custom-set icons [changed 5.12]: they output a non-existent class or find no file. Branch on `set` as above. In templates that also run before 5.12, write `entry.myField.set ?? null` (the property doesn't exist there). `icon.svg` returns a plain string, so it needs `|raw`; it carries `aria-hidden="true"`.

Query: queryable as a string, `.myField('heart')`, `.myField(':notempty:')`. Custom-set icons are stored with their prefix, so query `.myField('custom:rocket')`. GraphQL: Full data mode adds `set`, `svg` and `keywords` [5.12+]; name-only mode can't distinguish sets.

### Country

Returns `Country|null`. Stored as two-letter code.

```twig
{{ entry.myField }}        {# 'BE' #}
{{ entry.myField.name }}   {# 'Belgium' (5.3.0+) #}
```

## Relational Fields

All relational fields return **element queries** (not arrays). Each access returns a fresh query copy.

Properties common to all relation fields (Entries, Assets, Categories, Tags, Users):

- `viewMode` — display mode in the CP: `'list'`, `'list-inline'`, `'thumbs'`, `'cards'`, `'cards-grid'` [5.9+]
- `allowSelfRelations` (bool) — allow an element to relate to itself
- `localizeRelations` (bool) — maintain separate relations per site
- `defaultPlacement` [5.7+] — `'beginning'` or `'end'` for newly added relations

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

File kinds for "allowed file types" include **Markdown** [5.12+] (`markdown`: `.md`, `.markdown`), and both extensions are in the default `allowedFileExtensions`. Projects that override `allowedFileExtensions` don't get them; add them to `extraAllowedFileExtensions` instead. Before 5.12: `.md` uploads were rejected by default and had kind `unknown`.

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

Settings: `staticRows` (bool) [5.5+] — predefined rows that can't be added/removed, only edited. `maxRows` / `minRows` — limit number of rows.

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

### Content Block [5.8+]

Returns a single nested `ContentBlock` element (`craft\elements\ContentBlock`). Always exactly one per element — not repeatable. Ideal for reusable field groups (SEO metadata, banner config).

View modes: `grouped` (default, fields in a bordered group), `pane` (fields in a pane), `inline` (fields rendered inline with parent).

```twig
{{ entry.myContentBlock.metaTitle }}
{{ entry.myContentBlock.metaDescription }}
```

Cannot be nested within other Content Block fields.

## Matrix Configuration

### Entry Types in Matrix

Select from globally-defined entry types or create new ones. Entry types can be organized into named groups [5.8+]. Local name/handle overrides available [5.6+].

### Entry Type Per-Usage Overrides [5.6+]

When an entry type is used in a section or Matrix field, its name, handle, and description can be overridden for that specific context. The original entry type is unchanged — the override only applies in that section/field. This allows one entry type to serve different semantic roles in different contexts.

[changed 5.10.14] An overridden handle also changes which element partial renders. After: `entry.render()` checks `_partials/entry/{overriddenHandle}.twig` before `_partials/entry/{originalHandle}.twig`. Before 5.10.14: from 5.10.4 the overridden handle was respected but not prioritized, and before 5.10.4 it was ignored and only the original handle was looked up (craftcms/cms#18968). When supporting both, keep the partial under the original handle. See the `craft-site` skill's `element-partials.md`.

### View Modes

| Mode | Best For | Since |
|------|----------|-------|
| **Blocks** | Page builders, inline editing. Classic collapse/expand + drag reorder. | 5.0.0 |
| **Cards** | Read-only overview. Double-click opens slideout editor. | 5.0.0 |
| **Cards Grid** | Media galleries, visual content. Grid layout of cards. | [5.9+] |
| **Index** | Large datasets (100+ entries). Search, sort, filter, table toggle. | 5.0.0 |

### Matrix Properties

- `enableVersioning` (bool) [5.7+] — version nested entries alongside owner (blocks mode) or independently (cards/index)
- `pageSize` (int) — pagination for index view mode
- `defaultTableColumns` (array) — columns shown in table view
- `defaultIndexViewMode` (string) [5.5+] — default view in index mode
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

### Versioning [5.7+]

Controlled by `enableVersioning`. Blocks view mode: nested entries versioned alongside owner. Cards/Index modes: independent versioning via slideout editor when enabled.
