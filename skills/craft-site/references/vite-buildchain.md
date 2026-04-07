# Vite Buildchain Reference

> How the nystudio107 Vite plugin bridges Craft CMS and the Node.js build
> toolchain. Covers `config/vite.php`, `vite.config.ts`, asset loading in
> Twig, conditional per-page loading, and Tailwind v4 integration.

## Documentation

- nystudio107 Vite plugin: https://nystudio107.com/docs/vite/
- Craft CMS Vite integration: https://craftcms.com/docs/5.x/development/vite.html
- Vite build config: https://vite.dev/config/build-options
- Tailwind Vite plugin: https://tailwindcss.com/docs/installation/vite

## Common Pitfalls

- Confusing the two plugins — `nystudio107/craft-vite` is PHP (reads manifest,
  emits HTML tags). `@tailwindcss/vite` is Node (processes CSS at build time).
  They never overlap.
- Using `craft.vite.entry()` instead of `craft.vite.script()` — `entry()`
  returns a URL string only. `script()` returns complete `<script>` and
  `<link>` HTML tags with proper attributes.
- Mismatched paths between `vite.php` and `vite.config.ts` — `manifestPath`
  must point to the exact file that `build.manifest: true` generates.
  `serverPublic` must match `base` in production.
- Missing `@source` for templates — even though Tailwind v4.0.8+ auto-detects
  `.twig` files, explicit `@source` is cheap insurance against path changes.
- Loading Vue/search entry points on every page — use Twig blocks and multi-entry
  to load heavy JS only where needed.
- Forgetting `ViteRestart` for template changes — Vite's HMR doesn't watch
  `.twig` files by default. The restart plugin triggers a reload on template edits.

## Two Layers, Zero Overlap

The nystudio107 plugin and Tailwind's Vite plugin operate on completely
different layers:

| Layer | Package | What it does |
|-------|---------|-------------|
| **Build time (Node)** | `@tailwindcss/vite` | Processes CSS, scans for utility classes, outputs hashed files |
| **Request time (PHP)** | `nystudio107/craft-vite` | Reads `manifest.json`, generates `<script>` and `<link>` tags in Twig |

No special configuration needed to make them coexist. Drop `tailwindcss()`
into the `plugins` array alongside any other Vite plugins.

## `config/vite.php`

Lives in Craft's `config/` directory. Multi-environment aware (like `general.php`).
Tells the PHP plugin where to find Vite's output and how to reach the dev server.

```php
<?php

use craft\helpers\App;

return [
    'useDevServer'               => App::env('CRAFT_ENVIRONMENT') === 'dev',
    'manifestPath'               => '@webroot/dist/.vite/manifest.json',
    'devServerPublic'            => 'http://localhost:3000/',
    'serverPublic'               => App::env('PRIMARY_SITE_URL') . '/dist/',
    'errorEntry'                 => '',
    'cacheKeySuffix'             => '',
    'devServerInternal'          => '',
    'checkDevServer'             => false,
    'includeReactRefreshShim'    => false,
    'includeModulePreloadShim'   => true,
    'includeScriptOnloadHandler' => true,
    'criticalPath'               => '@webroot/dist/criticalcss',
    'criticalSuffix'             => '_critical.min.css',
];
```

### Key Settings

| Setting | Maps to | Purpose |
|---------|---------|---------|
| `manifestPath` | `build.outDir` + `.vite/manifest.json` | Where Vite writes the manifest in production |
| `serverPublic` | `base` option in production | Public URL prefix for built assets |
| `devServerPublic` | `server.origin` + `server.port` | URL the browser uses to reach the dev server |
| `checkDevServer` | — | Ping dev server before serving HMR URLs (enable for DDEV) |
| `devServerInternal` | — | Internal URL for the ping check (e.g., `http://localhost:3000` inside DDEV container) |

### DDEV Configuration

For DDEV setups, enable the dev server check so the plugin doesn't emit broken
HMR URLs when the dev server isn't running:

```php
'checkDevServer'  => true,
'devServerInternal' => 'http://localhost:3000',
```

## `vite.config.ts`

The Node-side build configuration. Lives at the project root (typically inside
`buildchain/` or alongside `package.json`).

```typescript
import tailwindcss from '@tailwindcss/vite'
import ViteRestart from 'vite-plugin-restart'

export default ({ command }) => ({
    base: command === 'serve' ? '' : '/dist/',
    build: {
        manifest: true,
        outDir: './web/dist/',
        rollupOptions: {
            input: {
                app: 'src/js/app.ts',
            },
        },
    },
    plugins: [
        tailwindcss(),
        ViteRestart({ reload: ['./cms/templates/**/*'] }),
    ],
    server: {
        host: '0.0.0.0',
        origin: 'http://localhost:3000',
        port: 3000,
        strictPort: true,
    },
})
```

### Configuration Rules

- `base` must match `serverPublic` in `vite.php` (production path prefix).
- `manifest: true` is required — the PHP plugin reads it.
- `outDir` must be web-accessible — typically `web/dist/`.
- `ViteRestart` watches `.twig` files for full-page reload on template changes.
- No nystudio107 npm package appears here. The PHP plugin reads the manifest;
  it never touches the Vite build.

### CSS Entry Point

Import your CSS from the JS entry point:

```typescript
// src/js/app.ts
import '../css/app.pcss'

// Alpine, DataStar, or global utilities
import Alpine from 'alpinejs'
Alpine.start()
```

Vite processes the CSS import through `@tailwindcss/vite`, extracts it to a
hashed `.css` file in production, and the nystudio107 plugin generates the
`<link>` tag from the manifest.

## Loading Assets in Twig

### `craft.vite.script()`

The primary function. Outputs complete `<script>` and `<link>` HTML tags.

```twig
{{ craft.vite.script('src/js/app.ts', false) }}
```

**Parameters:**
1. Entry point path (must match a key in `rollupOptions.input`)
2. Async CSS — `true` (default) uses `media="print" onload` pattern; `false`
   loads CSS synchronously (prevents FOUC)

**In dev mode:** Emits a `<script type="module">` pointing at the dev server.
HMR handles updates.

**In production:** Reads the manifest, resolves hashed filenames, generates
`<script type="module">`, `<link rel="modulepreload">` for chunks, and
`<link rel="stylesheet">` for extracted CSS.

### Placement

`<script type="module">` is inherently deferred (non-blocking). Place
`craft.vite.script()` in `<head>`:

```twig
{# _boilerplate/_layouts/base-html-layout.twig #}
{%- block headLinks -%}
    {{ parent() }}
    {{ craft.vite.script('src/js/app.ts', false) }}
{%- endblock -%}
```

### `craft.vite.entry()` vs `craft.vite.script()`

| Function | Returns | Dev server | Use case |
|----------|---------|-----------|----------|
| `script()` | Full HTML tags (`<script>`, `<link>`) | Yes, emits dev server URLs | Standard asset loading |
| `entry()` | URL string only | No, production manifest only | Manual tag construction |

Use `script()` for everything unless you need to construct tags manually.

## Conditional Per-Page Loading

Not every page needs every script. Define multiple entry points and load them
selectively via Twig blocks.

### Multiple Entry Points

```typescript
// vite.config.ts
rollupOptions: {
    input: {
        app: 'src/js/app.ts',
        search: 'src/js/apps/search.ts',
        contact: 'src/js/apps/contact.ts',
    },
},
```

### Twig Block Pattern

The layout chain defines a `pageJs` block. Views override it to load
page-specific entry points:

```twig
{# _boilerplate/_layouts/base-html-layout.twig #}
{%- block headLinks -%}
    {{ parent() }}
    {{ craft.vite.script('src/js/app.ts', false) }}
{%- endblock -%}

{%- block bodyJs -%}
    {%- block pageJs -%}{%- endblock -%}
{%- endblock -%}
```

```twig
{# _views/view--page-search.twig (or the router dispatching to it) #}
{%- block pageJs -%}
    {{ craft.vite.script('src/js/apps/search.ts') }}
{%- endblock -%}
```

### Loading Rules

- **Global assets** (`app.ts` with Alpine/DataStar, base CSS) load on every
  page via the layout.
- **Feature apps** (Vue search, contact forms) load only on pages that need
  them via `{% block pageJs %}`.
- Each Vue mini-app gets its own entry point. Never bundle all Vue features
  into one entry — that loads the search app on the contact page.
- The `app.ts` entry is always synchronous CSS (`false`) to prevent FOUC.
  Feature entries can use async CSS (`true`) since they're supplementary.

## Tailwind v4 Integration

Tailwind's Vite plugin sits in the `plugins` array — no further configuration:

```typescript
plugins: [
    tailwindcss(),
    ViteRestart({ reload: ['./cms/templates/**/*'] }),
],
```

The `@source` directive in your CSS entry point handles template scanning:

```css
@import "tailwindcss";
@source "../../cms/templates";
```

For the full CSS entry point structure with brand tokens and `@theme inline`,
see `design-tokens.md` in the `tailwind-v4` skill.

## Plugin Buildchains Are Different

Craft CMS **plugins** ship pre-built assets through Yii2 AssetBundle classes —
a completely separate architecture from the site-level Vite setup. Plugins use
`nystudio107/craft-plugin-vite` (different Composer package) with isolated dev
servers guarded by a `VITE_PLUGIN_DEVSERVER` env variable.

The site's Tailwind build has no interaction with plugin asset bundles. For
plugin development buildchain setup, see the `craftcms` skill.
