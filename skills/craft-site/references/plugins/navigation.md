# Navigation

Menu management plugin by Verbb. Create and manage navigation menus with drag-and-drop, nested structures, custom fields on nodes, multi-site support, and a rich Twig rendering API. The standard navigation solution for Craft CMS — 20,000+ active installs.

`verbb/navigation` — $19

## Documentation

- Docs: https://verbb.io/craft-plugins/navigation/docs
- Rendering: https://verbb.io/craft-plugins/navigation/docs/template-guides/rendering-nodes
- Custom fields: https://verbb.io/craft-plugins/navigation/docs/get-started/custom-fields
- GitHub: https://github.com/verbb/navigation

When unsure about a Navigation feature, `web_fetch` the docs.

## Common Pitfalls

- Querying nodes without `.all()` or `.one()` — `craft.navigation.nodes()` returns an element query, not results. Always call `.all()` to execute it.
- Not using `.level()` for flat menus — without it, nested child nodes are included. Use `.level(1)` for top-level only.
- Forgetting `.eagerly()` on node element fields — if nodes have custom relation fields, eager-load them to avoid N+1 queries.
- Rendering with `craft.navigation.render()` then fighting the HTML — the render function outputs complete `<ul><li>` markup. If you need custom HTML, query nodes and build your own markup instead.
- Not handling external URLs vs entry-linked nodes — some nodes link to entries (have an element), others are manual URLs. Template code must handle both.
- Caching navigation without invalidation — navigation rarely changes, but when it does, cached markup is stale. Use `{% cache %}` with a key, or use Blitz which auto-invalidates.

## Twig API

### Quick Render (Default Markup)

```twig
{{ craft.navigation.render('mainNav') }}
```

Outputs a complete `<nav><ul><li>` structure with nested children. Good for prototyping, but you'll want custom rendering for production.

### Render with Options

```twig
{{ craft.navigation.render('mainNav', {
    id: 'main-navigation',
    class: 'nav-list',
    ulClass: 'nav-list__items',
    liClass: 'nav-list__item',
    aClass: 'nav-list__link',
    activeClass: 'is-active',
    ulAttributes: { 'data-nav': 'main' },
}) }}
```

### Custom Rendering (Recommended)

Query nodes and build your own markup for full control:

```twig
{% set nodes = craft.navigation.nodes()
    .handle('mainNav')
    .level(1)
    .all() %}

<nav aria-label="Main navigation">
    <ul class="flex gap-6">
        {% for node in nodes %}
            <li>
                <a href="{{ node.url }}"
                   class="nav-link {{ node.active ? 'is-active' : '' }}"
                   {{ node.newWindow ? 'target="_blank" rel="noopener noreferrer"' }}
                   {{ node.active ? 'aria-current="page"' }}>
                    {{ node.title }}
                </a>

                {# Nested children #}
                {% if node.hasDescendants %}
                    <ul class="submenu">
                        {% for child in node.children %}
                            <li>
                                <a href="{{ child.url }}"
                                   class="submenu-link {{ child.active ? 'is-active' : '' }}">
                                    {{ child.title }}
                                </a>
                            </li>
                        {% endfor %}
                    </ul>
                {% endif %}
            </li>
        {% endfor %}
    </ul>
</nav>
```

### Node Properties

```twig
{{ node.title }}              {# Node label #}
{{ node.url }}                {# Full URL #}
{{ node.active }}             {# Boolean — is this node or a descendant active? #}
{{ node.isCurrent }}          {# Boolean — is this exact node active? #}
{{ node.newWindow }}          {# Boolean — opens in new tab? #}
{{ node.classes }}            {# Custom CSS classes #}
{{ node.customAttributes }}   {# Custom key/value attributes #}
{{ node.type }}               {# Node type (e.g., 'craft\elements\Entry') #}
{{ node.element }}            {# Linked Craft element (entry, category, etc.) or null #}
{{ node.hasDescendants }}     {# Boolean — has children? #}
{{ node.children }}           {# Child nodes array #}
{{ node.level }}              {# Nesting level (1 = top) #}
{{ node.parent }}             {# Parent node or null #}
```

### Querying Nodes

```twig
{# All top-level nodes for a nav #}
{% set nodes = craft.navigation.nodes()
    .handle('mainNav')
    .level(1)
    .all() %}

{# Specific nav for a specific site #}
{% set nodes = craft.navigation.nodes()
    .handle('footerNav')
    .siteId(currentSite.id)
    .all() %}

{# With eager-loaded custom fields #}
{% set nodes = craft.navigation.nodes()
    .handle('mainNav')
    .with(['icon'])
    .all() %}
```

### Active State Detection

Navigation automatically detects which node matches the current URL:

```twig
{% for node in nodes %}
    {# node.active — true if this node OR any descendant matches current URL #}
    {# node.isCurrent — true only if THIS node matches current URL #}
    <a href="{{ node.url }}"
       class="{{ node.active ? 'is-active' : '' }}"
       {{ node.isCurrent ? 'aria-current="page"' }}>
        {{ node.title }}
    </a>
{% endfor %}
```

## Node Types

| Type | Description |
|------|-------------|
| Entry | Links to a Craft entry (URL auto-syncs) |
| Category | Links to a Craft category |
| Asset | Links to a Craft asset |
| URL | Manual URL (internal or external) |
| Custom | Custom node type via plugin |

Entry-linked nodes automatically update their URL when the entry's slug changes. Manual URL nodes are static.

## Custom Fields on Nodes

Navigation nodes support custom field layouts. Add fields in CP → Navigation → Settings → Field Layout. Common additions:

- **Icon field** — FontAwesome class or asset for nav icons
- **Subtitle field** — secondary text for mega-menu items
- **Image field** — thumbnails for visual navigation

Access in templates:

```twig
{% if node.icon %}
    <i class="{{ node.icon }}"></i>
{% endif %}
{{ node.title }}
{% if node.subtitle %}
    <span class="text-sm text-gray-500">{{ node.subtitle }}</span>
{% endif %}
```

## Console Commands

```bash
# Resave all navigation nodes
ddev craft resave/navigation-nodes
```

## GraphQL

```graphql
{
  navigationNodes(navHandle: "mainNav", level: 1) {
    title
    url
    level
    newWindow
    classes
    children {
      title
      url
    }
  }
}
```

## Pair With

- **Blitz** — cache navigation globally. Blitz auto-invalidates when nav nodes change.
- **Hyper** — for in-content links alongside structural navigation.
