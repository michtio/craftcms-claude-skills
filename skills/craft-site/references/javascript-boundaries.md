# JavaScript Boundaries Reference

> When to use Twig, Alpine/DataStar, or Vue. Decision tree for interactivity.

## Documentation

- Alpine.js: https://alpinejs.dev/
- DataStar: https://data-star.dev/
- Vue 3: https://vuejs.org/guide/introduction.html
- Pinia: https://pinia.vuejs.org/
- Craft Vite plugin: https://nystudio107.com/docs/vite/

## Common Pitfalls

- Reaching for Vue too early — if Alpine/DataStar can handle it, use that. Vue's bundle size and build complexity aren't justified for a toggle.
- Alpine state sharing — if you're syncing state between multiple Alpine components via `$dispatch` / `window`, you've outgrown Alpine. Move to Vue.
- Inline `<script>` data passing — global variables and inline scripts create implicit dependencies. Use `data-*` attributes.
- Mixing template engines — never put Twig syntax inside `.vue` files or Vue template syntax inside `.twig` files.
- Empty mount points — Craft serves server-rendered HTML. Vue mounts after load. Always render a skeleton in the mount element for SEO and perceived performance.
- Nesting Alpine inside Vue or vice versa — they can coexist on the same page but never nested within each other.

## Table of Contents

- [The Decision Tree](#the-decision-tree)
- [Twig Only (Default)](#twig-only-default)
- [Alpine.js / DataStar (UI State)](#alpinejs--datastar-ui-state)
- [Vue 3 (Application State)](#vue-3-application-state)
- [Coexistence Rules](#coexistence-rules)
- [Consent-Gated Embeds](#consent-gated-embeds)

## The Decision Tree

```
Is there client-side state?
├── NO → Twig only (server-rendered, zero JS)
└── YES → Is it UI state or application state?
    ├── UI STATE (toggles, visibility, simple interactions)
    │   → Alpine.js or DataStar
    │   Examples: mobile menu, accordion, tabs, dropdown, modal, tooltip
    └── APPLICATION STATE (data fetching, filtering, real-time)
        → Vue 3 (+ Pinia for stores)
        Examples: search, filtering, paginated lists, dashboards, forms with validation
```

### Definition of Terms

- **UI state:** visibility toggles, open/close, active tab, scroll position. The HTML exists in the DOM (server-rendered by Twig). JS decorates it.
- **Application state:** data loaded from APIs, filtered/sorted/paginated collections, form state across steps. Vue owns the DOM — Twig provides the mount point.

## Twig Only (Default)

The default for everything. No JavaScript unless proven necessary.

```twig
{# Standard component — zero JS, fully server-rendered #}
{%- tag 'article' with { class: classes.implode(' ') } -%}
    {%- include '_atoms/images/image--responsive' with {
        image: props.get('image'),
        preset: 'teaser',
    } only -%}
    <div class="p-4">
        {%- include '_atoms/texts/text--h3' with {
            content: props.get('heading'),
        } only -%}
    </div>
{%- endtag -%}
```

## Alpine.js / DataStar (UI State)

Twig renders the full HTML. Alpine or DataStar adds behavior via attributes.
Both fill the same role — pick one per project, don't mix them.

### Alpine.js

The established choice. Uses `x-*` attributes for directives.

```twig
{# Alpine: mobile navigation #}
<nav x-data="{ open: false }" class="lg:hidden">
    {%- include '_atoms/buttons/button--hamburger' with {
        label: 'Toggle menu',
    } only -%}

    <div x-show="open"
         x-transition
         x-cloak
         class="fixed inset-0 z-50 bg-brand-surface">

        <button @click="open = false" class="absolute top-4 right-4">
            {%- include '_atoms/icons/icon--fa' with {
                icon: 'fa-solid fa-xmark',
                label: 'Close menu',
            } only -%}
        </button>

        <ul class="flex flex-col gap-4 p-8">
            {%- for item in props.get('items') -%}
                <li>
                    {%- include '_atoms/links/link--navigation' with {
                        text: item.title,
                        url: item.url,
                        active: item.active ?? false,
                    } only -%}
                </li>
            {%- endfor -%}
        </ul>
    </div>
</nav>
```

```twig
{# Alpine: accordion #}
<div x-data="{ active: null }">
    {%- for item in props.get('items') -%}
        <div class="border-b border-brand-muted">
            <button @click="active = active === {{ loop.index }} ? null : {{ loop.index }}"
                    class="w-full text-left py-4 flex justify-between"
                    :aria-expanded="active === {{ loop.index }}">
                {{ item.heading }}
                <i class="fa-solid fa-chevron-down transition-transform"
                   :class="active === {{ loop.index }} && 'rotate-180'"
                   aria-hidden="true"></i>
            </button>
            <div x-show="active === {{ loop.index }}"
                 x-collapse>
                <div class="pb-4">
                    {{ item.content }}
                </div>
            </div>
        </div>
    {%- endfor -%}
</div>
```

### DataStar

The modern alternative. Uses HTML-native `data-*` attributes and signals for
reactivity. Lighter weight, SSE-driven updates, no custom directive syntax.
DataStar is the successor to tools like Sprig — it handles server-side
reactivity through SSE without requiring a Craft plugin.

```twig
{# DataStar: mobile navigation #}
<nav data-signals="{ open: false }" class="lg:hidden">
    <button data-on-click="$open = !$open">
        {%- include '_atoms/icons/icon--fa' with {
            icon: 'fa-solid fa-bars',
            label: 'Toggle menu',
        } only -%}
    </button>

    <div data-show="$open"
         class="fixed inset-0 z-50 bg-brand-surface">

        <button data-on-click="$open = false" class="absolute top-4 right-4">
            {%- include '_atoms/icons/icon--fa' with {
                icon: 'fa-solid fa-xmark',
                label: 'Close menu',
            } only -%}
        </button>

        <ul class="flex flex-col gap-4 p-8">
            {%- for item in props.get('items') -%}
                <li>
                    {%- include '_atoms/links/link--navigation' with {
                        text: item.title,
                        url: item.url,
                        active: item.active ?? false,
                    } only -%}
                </li>
            {%- endfor -%}
        </ul>
    </div>
</nav>
```

### When Alpine vs DataStar

| Consideration | Alpine.js | DataStar |
|--------------|-----------|----------|
| Syntax | `x-*` custom directives | `data-*` HTML-native attributes |
| Reactivity | Client-side signals | Client-side signals + SSE for server updates |
| Bundle | ~15KB | ~12KB |
| Ecosystem | Mature, large plugin ecosystem | Newer, growing |
| Server updates | Requires separate AJAX/fetch | Built-in via SSE (`data-on-load`) |

Both handle the same use cases: toggles, accordions, tabs, modals, tooltips,
dropdowns, form validation feedback. Pick one per project based on team
familiarity and whether you need SSE-driven server updates.

## Vue 3 (Application State)

Vue owns its DOM subtree. Twig provides mount points and initial data.

### Mount Point Pattern

Twig renders the mount element with initial config as JSON:

```twig
{# In a view or organism #}
<div id="search-app"
     data-config="{{ {
         endpoint: alias('@searchUrl'),
         index: currentSite.handle ~ '_entries',
         filters: availableFilters,
     }|json_encode|e('html_attr') }}">

    {# Skeleton/loading state — replaced by Vue on mount #}
    <div class="animate-pulse space-y-4">
        <div class="h-48 bg-brand-muted rounded-lg"></div>
        <div class="h-4 bg-brand-muted rounded w-3/4"></div>
    </div>
</div>
```

### Vue Entry Point

```typescript
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import SearchApp from '../vue/apps/SearchApp.vue';

const element = document.getElementById('search-app');
if (element) {
    const config = JSON.parse(element.dataset.config);
    const app = createApp(SearchApp, { config });
    app.use(createPinia());
    app.mount(element);
}
```

### Vite Multi-Entry

Each Vue feature gets its own entry point, loaded only on pages that need it.
See `vite-buildchain.md` for the full Vite setup and conditional loading pattern.

```typescript
// vite.config.ts
export default defineConfig({
    build: {
        rollupOptions: {
            input: {
                app: 'src/js/app.ts',
                search: 'src/js/apps/search.ts',
            },
        },
    },
});
```

```twig
{# Load Vue app entry only on pages that need it #}
{%- block pageJs -%}
    {{ craft.vite.script('src/js/apps/search.ts') }}
{%- endblock -%}
```

### Vue Project Structure

```
src/js/
├── app.ts                    # Main: Alpine/DataStar setup, global utilities
├── apps/                     # Vue mini-app entry points (one per feature)
│   └── search.ts
├── composables/              # Shared Vue composables
├── interfaces/               # TypeScript interfaces
├── stores/                   # Pinia stores
├── utils/                    # Shared utilities
└── vue/
    ├── _atoms/               # Vue atomic components (mirror Twig structure)
    ├── _molecules/
    ├── _organisms/
    └── apps/                 # Vue app root components
```

Vue components mirror the Twig atomic structure and use the same Tailwind classes
and brand tokens. They're the client-rendered equivalent of their Twig counterparts.

### Data Handoff Rules: Twig → Vue

- Pass initial data via `data-*` attributes (JSON-encoded).
- Vue reads on mount. After mount, Vue owns all state.
- **Never** embed Twig variables inside Vue template syntax.
- **Never** use inline `<script>` blocks to pass data.
- **Never** let Vue reach outside its mount element to read DOM content.

## Coexistence Rules

1. **Alpine/DataStar and Vue can coexist** on the same page. Alpine/DataStar handles site chrome (nav, accordions). Vue handles feature SPAs (search, filtering).
2. **Never nest** Alpine/DataStar inside a Vue-mounted element or vice versa.
3. **Communication** between Alpine/DataStar and Vue: use custom events on `document`.
4. **One Alpine instance per element.** Never nest `x-data` inside another `x-data` (use Alpine stores instead).
5. **Vue mini-apps, not Vue SPAs.** Each feature gets its own entry point and mount point. Never mount Vue on `<body>` or `<main>`.

## Consent-Gated Embeds

```twig
{# Alpine version #}
<div x-data="{ consent: false }"
     @consent-granted.window="consent = true">
    <template x-if="consent">
        {%- include '_atoms/embeds/embed--video' with {
            embed: props.get('embed'),
        } only -%}
    </template>
    <template x-if="!consent">
        <div class="bg-brand-muted p-8 text-center rounded-lg">
            <p>Accept cookies to view this video.</p>
            <button @click="$dispatch('open-consent')" class="underline">
                Manage cookie preferences
            </button>
        </div>
    </template>
</div>
```
