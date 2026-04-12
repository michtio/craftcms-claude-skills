# Plugin Vite — CP Asset Bundles with Vite

How to use Vite for building and serving JavaScript and CSS in Craft CMS 5 plugin control panel pages. This is separate from site-level Vite (covered in the `craft-site` skill's `vite-buildchain.md`).

## Documentation

- nystudio107/craft-plugin-vite: https://github.com/nystudio107/craft-plugin-vite
- Craft AssetBundle: https://craftcms.com/docs/5.x/extend/asset-bundles.html

Craft 5 does not have native Vite support for plugins. The built-in `Webpack` service is webpack-oriented. Plugins use `nystudio107/craft-plugin-vite` for Vite integration.

## Common Pitfalls

- **Declaring `$js`/`$css` on the AssetBundle** — when using VitePluginService, leave these empty. The service registers tags via the manifest. Declaring them causes double-loading.
- **Same dev server port across plugins** — each plugin needs a unique port (3005, 3006, 4000, etc.) to avoid conflicts during development.
- **Missing `VITE_PLUGIN_DEVSERVER` env var check** — without this env var, VitePluginService forces `useDevServer = false`. Safe default for production, but confusing during dev if you forget to set it.
- **Not registering `@vite/client`** — HMR requires the Vite client script. Some setups need explicit `register('@vite/client')` when the dev server is running.
- **Using `devServerPublic` URL for `devServerInternal`** — in Docker/DDEV, PHP pings the dev server from inside the container (e.g., `http://container-name:3005`), while the browser hits `http://localhost:3005`. These must be different.

## Architecture Overview

| Concern | Site Vite (front-end) | Plugin Vite (CP) |
|---------|----------------------|------------------|
| Composer package | `nystudio107/craft-vite` | `nystudio107/craft-plugin-vite` |
| PHP service | `ViteService` | `VitePluginService` (extends ViteService) |
| Config location | `config/vite.php` | Plugin's `ServicesTrait::config()` |
| Asset delivery | Direct from `web/dist/` | Through Yii2 AssetBundle + `cpresources/` |
| Dev server toggle | `useDevServer` in config | `VITE_PLUGIN_DEVSERVER` env variable |
| Twig access | `craft.vite.script()` | `craft.{pluginHandle}.register()` |

## Required Files

```
plugin-root/
├── composer.json                          # require nystudio107/craft-plugin-vite
├── buildchain/
│   ├── package.json                       # vite as devDependency
│   ├── vite.config.ts                     # build config
│   └── src/
│       ├── js/
│       │   └── MyPlugin.ts               # entry point
│       └── css/
│           └── app.css                    # styles (imported by entry)
└── src/
    ├── services/
    │   └── ServicesTrait.php              # VitePluginService registration
    ├── variables/
    │   └── MyPluginVariable.php           # Twig variable with ViteVariableTrait
    ├── web/assets/
    │   ├── dist/                          # Vite output (committed or built in CI)
    │   │   ├── manifest.json
    │   │   └── assets/
    │   │       ├── MyPlugin-[hash].js
    │   │       └── MyPlugin-[hash].css
    │   └── MyPluginCpAsset.php            # AssetBundle class
    └── templates/
        └── _layouts/
            └── plugin-cp.twig            # registers Vite assets
```

## Step-by-Step Setup

### 1. Composer Dependency

```json
{
    "require": {
        "nystudio107/craft-plugin-vite": "^5.0.0"
    }
}
```

### 2. AssetBundle

The AssetBundle declares the `sourcePath` pointing at the `dist/` directory. Do not declare `$js` or `$css` — VitePluginService handles registration via the manifest.

```php
use craft\web\AssetBundle;
use craft\web\assets\cp\CpAsset;

class MyPluginCpAsset extends AssetBundle
{
    public function init(): void
    {
        $this->sourcePath = '@myplugin/web/assets/dist';

        $this->depends = [
            CpAsset::class,
        ];

        parent::init();
    }
}
```

### 3. ServicesTrait Registration

Register VitePluginService as a component on the plugin:

```php
use nystudio107\pluginvite\services\VitePluginService;

trait ServicesTrait
{
    public static function config(): array
    {
        return [
            'components' => [
                'vite' => [
                    'class' => VitePluginService::class,
                    'assetClass' => MyPluginCpAsset::class,
                    'checkDevServer' => true,
                    'devServerInternal' => 'http://my-plugin-buildchain-dev:3005',
                    'devServerPublic' => 'http://localhost:3005',
                    'errorEntry' => 'src/js/MyPlugin.ts',
                    'useDevServer' => true,
                    'useForAllRequests' => false,
                ],
            ],
        ];
    }
}
```

**Key properties:**

| Property | Purpose |
|----------|---------|
| `assetClass` | The AssetBundle FQCN — maps manifest to `cpresources/` path |
| `useDevServer` | Master switch for dev server mode |
| `devServerPublic` | URL the browser hits for HMR (`http://localhost:PORT`) |
| `devServerInternal` | URL PHP pings from inside the container (differs in DDEV/Docker) |
| `checkDevServer` | Actually ping the dev server before assuming it's running |
| `errorEntry` | Entry point to inject on error pages (enables HMR on 500 pages) |
| `useForAllRequests` | Set `true` only if plugin assets load on front-end (e.g., SEOmatic previews) |

### 4. Vite Config

```typescript
import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
    base: command === 'serve' ? '' : '/dist/',
    build: {
        emptyOutDir: true,
        manifest: 'manifest.json',
        outDir: '../src/web/assets/dist',
        rollupOptions: {
            input: {
                app: 'src/js/MyPlugin.ts',
            },
        },
    },
    server: {
        host: '0.0.0.0',
        origin: 'http://localhost:' + process.env.DEV_PORT,
        port: parseInt(process.env.DEV_PORT),
        strictPort: true,
    },
}));
```

**Critical rules:**
- `manifest: 'manifest.json'` — required, VitePluginService reads it
- `outDir` points into `src/web/assets/dist` — matches the AssetBundle's `sourcePath`
- `base: '/dist/'` in production — VitePluginService overrides this at runtime with the actual `cpresources/` URL
- `base: ''` in serve mode — dev server serves from root

### 5. Twig Variable

Expose Vite methods to CP templates:

```php
use nystudio107\pluginvite\variables\ViteVariableInterface;
use nystudio107\pluginvite\variables\ViteVariableTrait;

class MyPluginVariable implements ViteVariableInterface
{
    use ViteVariableTrait;
}
```

Register on `CraftVariable::EVENT_INIT` in the plugin's `init()`:

```php
Event::on(CraftVariable::class, CraftVariable::EVENT_INIT,
    function(Event $event) {
        $event->sender->set('myPlugin', [
            'class' => MyPluginVariable::class,
            'viteService' => $this->vite,
        ]);
    }
);
```

### 6. CP Template Registration

```twig
{% extends "_layouts/cp" %}

{% block head %}
    {{ parent() }}
    {% set tagOptions = {
        'depends': [
            'myplugin\\web\\assets\\MyPluginCpAsset'
        ],
    } %}
    {{ craft.myPlugin.register('src/js/MyPlugin.ts', false, tagOptions, tagOptions) }}
{% endblock %}
```

The `depends` option ensures the AssetBundle is registered as a dependency, so Yii2's asset manager publishes the files and loads them in order.

**Alternative: register from PHP** (useful for assets that load on every CP page):

```php
Event::on(View::class, View::EVENT_BEFORE_RENDER_PAGE_TEMPLATE,
    function(TemplateEvent $event) {
        Craft::$app->getView()->registerAssetBundle(MyPluginCpAsset::class);
        MyPlugin::$plugin->vite->register('src/js/MyPlugin.ts');
    }
);
```

## Twig API

Available via `craft.{pluginHandle}.*`:

| Method | Returns | Purpose |
|--------|---------|---------|
| `register(path, asyncCss, scriptAttrs, cssAttrs)` | void | Register script/style tags on the View |
| `script(path, asyncCss, scriptAttrs, cssAttrs)` | Markup | Returns raw HTML string for inline output |
| `entry(path)` | string | Returns the URL for an entry point |
| `asset(path)` | string | Returns the URL for a static asset |
| `inline(path)` | Markup | Inlines file contents |
| `devServerRunning()` | bool | Whether the dev server is active |

## Dev Server in DDEV

For DDEV environments, the dev server runs in a separate container or is exposed via `web_extra_exposed_ports`. The split URL pattern handles the container-to-host difference:

- `devServerPublic`: `http://localhost:3005` — browser URL
- `devServerInternal`: `http://my-plugin-buildchain-dev:3005` — container-to-container URL

The `VITE_PLUGIN_DEVSERVER` environment variable is the master switch. If this env var does not exist (regardless of value), VitePluginService forces `useDevServer = false` and falls back to the built manifest. In production, no env var means no dev server — a safe default.

## TypeScript and Vue

**TypeScript** is fully supported. Entry points can be `.ts` files — Vite handles compilation.

**Vue 3** is supported with `@vitejs/plugin-vue`:

```typescript
import VuePlugin from '@vitejs/plugin-vue';

export default defineConfig({
    plugins: [VuePlugin()],
    resolve: {
        alias: {
            'vue': 'vue/dist/vue.esm-bundler.js',
        },
    },
});
```

**CSS imports:** Entry points import CSS directly (`import '../css/app.css'`). Vite extracts it into the manifest. VitePluginService generates the appropriate `<link>` tags.

## Script Load Events

VitePluginService adds an `onload` handler to all script tags that dispatches a custom event:

```javascript
document.addEventListener('vite-script-loaded', function(e) {
    if (e.detail.path === 'src/js/MyPlugin.ts') {
        // Initialize after script loads
    }
});
```

This is important because `type="module"` scripts load asynchronously — `document.ready` does not guarantee load order.

## Production Build

```bash
cd buildchain && npm run build
```

This generates `manifest.json` and hashed asset files in `src/web/assets/dist/`. Commit the `dist/` directory (or build in CI). VitePluginService reads the manifest from the published `cpresources/` path at runtime.
