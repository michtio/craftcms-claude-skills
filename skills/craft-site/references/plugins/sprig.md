# Sprig

Reactive Twig component framework by PutYourLightsOn. Lets you create components that re-render themselves on user-triggered events (clicks, input changes, form submissions) via AJAX — no JavaScript required. Built on htmx. Enables live search, load more, pagination, filtering, tabs, and form submissions without page refreshes. 13K+ installs.

`putyourlightson/craft-sprig` — Free (MIT)

## Documentation

- Full docs: https://putyourlightson.com/plugins/sprig
- Cookbook: https://putyourlightson.com/sprig/cookbook
- GitHub: https://github.com/putyourlightson/craft-sprig

When unsure about a Sprig attribute or function, `WebFetch` the docs page. The cookbook has ready-to-use patterns for common scenarios.

## Core Concept

A Sprig component is a Twig template that:
1. Lives in `templates/_components/` (convention, not requirement)
2. Is rendered with `{{ sprig('_components/my-component') }}`
3. Has a single root element
4. Re-renders itself via AJAX when elements with the `sprig` attribute are triggered

The `sprig` attribute on an element makes it "reactive" — on its trigger event (click by default, change for inputs), it sends an AJAX request that re-renders the component with updated variables.

## Common Pitfalls

- **Multiple root elements** — a Sprig component must have a single root HTML element. Everything must be wrapped in one container.
- **Not initializing variables with defaults** — every variable used in the component must have a default: `{% set query = query ?? '' %}`. Without this, the first render fails because the variable doesn't exist yet.
- **Using `{% js %}` / `{% css %}` / `{% html %}` tags** — these don't re-render during Sprig AJAX requests. Use `sprig.registerJs()` instead for JavaScript.
- **Variables named like Twig globals** — Sprig disallows variables named the same as Twig globals (e.g., `craft`, `currentSite`). Use unique names.
- **Missing `s-target` and `s-swap`** — without these, the entire component re-renders. Be explicit about what gets swapped for performance.
- **Not using `s-trigger` with delay on inputs** — without `delay:300ms`, every keystroke fires a request. Always debounce text inputs.
- **Expecting full-page Twig context** — Sprig components render in isolation. They don't have access to entry variables from the parent page. Pass what you need as initial variables.
- **Caching Sprig components** — Sprig components should not be statically cached (Blitz). Use `{% cache %}` sparingly and exclude Sprig component markup. Use `{{ sprig.htmxScript }}` outside cached blocks.

## Creating a Component

### Include in a Template

```twig
{# In your page template #}
{{ sprig('_components/search') }}

{# With initial variables #}
{{ sprig('_components/load-more', { limit: 5, section: 'news' }) }}

{# With HTML attributes (third parameter) #}
{{ sprig('_components/search', {}, {
    'id': 'main-search',
    'class': 'search-widget',
    's-trigger': 'load, refresh',
}) }}
```

### Component Template

```twig
{#--- _components/search ---#}

{# Always set defaults — these variables won't exist on first render #}
{% set query = query ?? '' %}

<div>
    <input
        sprig
        s-trigger="keyup changed delay:300ms"
        s-target="#results"
        type="text"
        name="query"
        value="{{ query }}"
        placeholder="Search..."
    >

    <div id="results">
        {% if query %}
            {% set entries = craft.entries.search(query).limit(10).all() %}
            {% for entry in entries %}
                <a href="{{ entry.url }}">{{ entry.title }}</a>
            {% endfor %}
            {% if not entries|length %}
                <p>No results found.</p>
            {% endif %}
        {% endif %}
    </div>
</div>
```

## Sprig Attributes (`s-*`)

All attributes are prefixed with `s-` (Sprig's namespace over htmx's `hx-`).

| Attribute | Description | Example |
|-----------|-------------|---------|
| `sprig` | Makes element reactive (required on trigger elements) | `<button sprig>` |
| `s-trigger` | Event that fires the request | `s-trigger="keyup changed delay:300ms"` |
| `s-target` | CSS selector of element to swap | `s-target="#results"` |
| `s-swap` | How to swap content | `s-swap="outerHTML"`, `innerHTML`, `beforeend`, etc. |
| `s-val:*` | Pass a variable value with the request | `s-val:page="{{ page + 1 }}"` |
| `s-vals` | Pass multiple variables as JSON | `s-vals='{{ { a: 1, b: 2 }|json_encode }}'` |
| `s-method` | HTTP method | `s-method="post"` |
| `s-action` | Craft controller action to invoke | `s-action="contact-form/send"` |
| `s-replace` | Shorthand for `s-target` + `s-swap="innerHTML"` | `s-replace="#results"` |
| `s-select` | Select specific content from response | `s-select="#partial"` |
| `s-push-url` | Push URL to browser history | `s-push-url="true"` |
| `s-confirm` | Confirmation prompt before request | `s-confirm="Are you sure?"` |
| `s-disable` | Disable element during request | `s-disable` |
| `s-indicator` | Show element during request | `s-indicator="#spinner"` |
| `s-sync` | Synchronize requests between elements | `s-sync="closest form:abort"` |
| `s-boost` | Boost all links/forms in element | `s-boost="true"` |

### `s-val:*` Naming

HTML attributes are case-insensitive. Use kebab-case — Sprig converts to camelCase:

```twig
<button sprig s-val:my-custom-page="5">
{# In the re-rendered template: myCustomPage == 5 #}
{% set myCustomPage = myCustomPage ?? 1 %}
```

## Sprig Variable (`sprig.*`)

Available inside Sprig component templates:

| Property/Method | Returns | Description |
|----------------|---------|-------------|
| `sprig.isRequest` | `bool` | Whether this is a Sprig AJAX request (not initial render) |
| `sprig.isInclude` | `bool` | Whether component was included (not direct request) |
| `sprig.isSuccess` | `bool` | Whether a controller action succeeded |
| `sprig.isError` | `bool` | Whether a controller action failed |
| `sprig.isBoosted` | `bool` | Whether request was boosted |
| `sprig.isHistoryRestoreRequest` | `bool` | History restore request |
| `sprig.htmxScript` | `string` | htmx script tag (use when loading outside cached blocks) |
| `sprig.triggerRefresh(selector)` | — | Trigger a refresh on another component |
| `sprig.triggerRefreshOnLoad(selector)` | — | Trigger refresh on page load |
| `sprig.triggerEvents(events)` | — | Trigger client-side events |
| `sprig.swapOob(selector, template, vars?)` | — | Swap out-of-band content |
| `sprig.registerJs(js)` | — | Register JS to execute after htmx settles |

## Common Patterns

### Load More

```twig
{#--- _components/load-more ---#}
{% set offset = offset ?? 0 %}
{% set limit = limit ?? 5 %}
{% set entries = craft.entries.section('news').offset(offset).limit(limit).all() %}
{% set total = craft.entries.section('news').count() %}

{% for entry in entries %}
    <article>{{ entry.title }}</article>
{% endfor %}

{% if total > offset + entries|length %}
    <button sprig
        s-val:offset="{{ offset + limit }}"
        s-target="this"
        s-swap="outerHTML"
    >
        Load more
    </button>
{% endif %}
```

### Filter with Form

```twig
{#--- _components/filter ---#}
{% set category = category ?? '' %}

<select sprig name="category">
    <option value="">All categories</option>
    {% for cat in craft.categories.group('topics').all() %}
        <option value="{{ cat.slug }}" {{ cat.slug == category ? 'selected' }}>
            {{ cat.title }}
        </option>
    {% endfor %}
</select>

<div id="results">
    {% set query = craft.entries.section('articles') %}
    {% if category %}
        {% set query = query.relatedTo(craft.categories.slug(category).one()) %}
    {% endif %}
    {% for entry in query.all() %}
        <a href="{{ entry.url }}">{{ entry.title }}</a>
    {% endfor %}
</div>
```

### Post to Controller Action

```twig
{#--- _components/contact ---#}
{% if sprig.isSuccess %}
    <p>Message sent!</p>
{% elseif sprig.isError %}
    {% if errors is defined %}
        {% for error in errors %}
            <p class="error">{{ error|first }}</p>
        {% endfor %}
    {% endif %}
{% else %}
    <form sprig s-method="post" s-action="contact-form/send">
        <input type="text" name="fromName" value="{{ fromName ?? '' }}">
        <input type="email" name="fromEmail" value="{{ fromEmail ?? '' }}">
        <textarea name="message">{{ message ?? '' }}</textarea>
        <button type="submit">Send</button>
    </form>
{% endif %}
```

## Blitz Compatibility

Sprig components inject dynamic content via AJAX and are inherently incompatible with full-page static caching. Strategies:

1. **Include Sprig components outside cached blocks** — use Blitz's `{{ craft.blitz.getUri() }}` or exclude specific URIs
2. **Use `s-trigger="load"` for dynamic islands** — render a placeholder in the static page, let Sprig hydrate on load
3. **Ensure htmx loads outside cache** — output `{{ sprig.htmxScript }}` in an uncached block

## Pair With

- **Blitz** — dynamic islands within cached pages using `s-trigger="load"`
- **Formie** — alternative form rendering approach. Use Sprig when you need custom AJAX form behavior beyond what Formie provides
- **DataStar** — newer hypermedia alternative. Sprig = htmx-based, DataStar = signals-based. Choose one per project.
