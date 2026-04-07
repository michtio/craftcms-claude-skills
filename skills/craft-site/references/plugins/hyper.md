# Hyper

Flexible link field type by Verbb. Supports entries, URLs, emails, phone numbers, assets, categories, users, and custom link types. Each link type has its own field layout for additional fields. #2 Top Paid plugin on the store — used in 5/6 projects.

`verbb/hyper` — $19

## Documentation

- Docs: https://verbb.io/craft-plugins/hyper/docs
- GitHub: https://github.com/verbb/hyper

When unsure about a Hyper feature, `web_fetch` the docs.

## Common Pitfalls

- Treating the field value as a single link when `multipleLinks` is enabled — a Hyper field returns a `LinkCollection`. For single-link fields it proxies to the first link via `__get`, but for multi-link fields you must iterate.
- Using `{{ link }}` expecting text — string casting returns the URL, not the link text. Use `link.getText()` or `link.linkText` for the display text.
- Not checking for empty links — editors can leave Hyper fields empty. Always null-check before accessing properties.
- Hardcoding `target="_blank"` in templates — Hyper handles this via the `newWindow` property. Use `link.getLinkAttributes()` which includes `target` and `rel` automatically.
- Forgetting that `__call` returns null for missing properties — Hyper intentionally doesn't throw errors for missing properties on links, making templates more forgiving. But this means typos in property names silently return null.

## Link Types

| Type | Class | Link Value |
|------|-------|------------|
| Entry | `links\Entry` | Craft entry element |
| URL | `links\Url` | Arbitrary URL |
| Email | `links\Email` | Email address → `mailto:` |
| Phone | `links\Phone` | Phone number → `tel:` |
| Asset | `links\Asset` | Craft asset element |
| Category | `links\Category` | Craft category element |
| User | `links\User` | Craft user element |
| Custom | `links\Custom` | Custom link type with custom fields |
| Site | `links\Site` | Link to a Craft site |
| Embed | `links\Embed` | oEmbed URL |

Plugin-specific types: `FormieForm`, `Product` (Commerce), `ShopifyProduct`, `CalendarEvent`.

## Twig API

### Single Link Field

```twig
{% set link = entry.myLinkField %}

{% if link and link.getUrl() %}
    <a {{ link.getLinkAttributes({ class: 'btn btn-primary' }, true) }}>
        {{ link.getText() ?? 'Read more' }}
    </a>
{% endif %}
```

### Key Properties and Methods

```twig
{{ link.getUrl() }}              {# Full URL (with urlSuffix if set) #}
{{ link.getText() }}             {# Link text (from linkText field) #}
{{ link.getLinkTitle() }}         {# Title attribute value #}
{{ link.getAriaLabel() }}        {# Aria-label value #}
{{ link.getClasses() }}          {# CSS classes string #}
{{ link.getNewWindow() }}        {# Boolean — opens in new tab? #}
{{ link.getCustomAttributes() }} {# Array of custom key/value attributes #}
{{ link.linkValue }}             {# Raw link value (URL, element ID, etc.) #}
{{ link.linkText }}              {# Raw link text #}
{{ link }}                       {# String cast → URL #}
```

### `getLinkAttributes()` (Recommended)

Returns all link attributes as an array or rendered string — includes `href`, `target`, `rel`, `class`, `title`, `aria-label`, and custom attributes:

```twig
{# As rendered HTML attribute string #}
<a {{ link.getLinkAttributes({}, true) }}>{{ link.getText() }}</a>

{# With additional classes merged in #}
<a {{ link.getLinkAttributes({ class: 'btn' }, true) }}>{{ link.getText() }}</a>

{# As array for manual control #}
{% set attrs = link.getLinkAttributes() %}
<a href="{{ attrs.href }}" class="{{ attrs.class ?? '' }}">
    {{ link.getText() }}
</a>
```

### Multiple Links Field

```twig
{% for link in entry.myLinksField %}
    {% if link.getUrl() %}
        <a {{ link.getLinkAttributes({ class: 'nav-link' }, true) }}>
            {{ link.getText() }}
        </a>
    {% endif %}
{% endfor %}
```

### Element Link — Accessing the Linked Element

For Entry, Asset, Category, and User link types:

```twig
{% set link = entry.myLinkField %}
{% if link.getElement() %}
    {# Access the linked entry/asset/category directly #}
    {{ link.getElement().title }}
    {{ link.getElement().url }}
{% endif %}
```

### Checking Link Type

```twig
{% if link.type == 'Entry' %}
    {# Entry-specific rendering #}
{% elseif link.type == 'Url' %}
    {# External URL rendering #}
{% endif %}
```

## Integration with Button Atom

Hyper pairs naturally with the button atom pattern. The link field provides URL, text, target, and aria-label — the atom handles rendering:

```twig
{# Pass Hyper link data to button atom #}
{% if link and link.getUrl() %}
    {% include '_atoms/button' with {
        url: link.getUrl(),
        label: link.getText() ?? 'Read more',
        ariaLabel: link.getAriaLabel() ?? null,
        newWindow: link.getNewWindow() ?? false,
    } only %}
{% endif %}
```

## GraphQL

Hyper fields expose link data via GraphQL with type-specific fields for each configured link type.

## Pair With

- **Colour Swatches** — combine link + colour for themed CTAs
