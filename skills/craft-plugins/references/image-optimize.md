# ImageOptimize

Responsive image variants and transform optimization by nystudio107. Does two separate things:

1. **Optimizes every native Craft transform.** When the transform method is Craft, it hooks transform generation and runs command-line optimizers (jpegoptim, optipng, svgo, gifsicle) and variant creators (cwebp) on each transform file Craft writes. No template changes are needed, and the plugin's settings decide which tools run.
2. **The OptimizedImages field.** Added to an Asset Volume's field layout, it pre-generates a set of responsive variants, a placeholder and a colour palette per asset, and stores the URLs in the asset's content. Twig helpers render `<img>` / `<picture>` from it.

Transform methods: Craft (local GD/Imagick), imgix, Sharp JS, Thumbor. The last three are separate packages (`nystudio107/craft-imageoptimize-imgix`, `-sharp`, `-thumbor`) that ImageOptimize's `composer.json` requires, so they are always installed.

`nystudio107/craft-imageoptimize` — $59. This reference is verified against **5.0.8** (Craft 5, `develop-v5`, tagged 2026-08-06) and the 5.0.0 transform-method packages.

## Documentation

- Overview: https://nystudio107.com/docs/image-optimize/
- Configuration: https://nystudio107.com/docs/image-optimize/configuring.html
- Using (Twig): https://nystudio107.com/docs/image-optimize/using.html
- Advanced: https://nystudio107.com/docs/image-optimize/advanced.html

Source (the timing and cost claims below come from here):

- Event hooks: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/ImageOptimize.php
- Optimizers, variant creators, URL handling: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/services/Optimize.php
- OptimizedImages field data, placeholders: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/services/OptimizedImages.php and https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/services/Placeholder.php
- Field save hook: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/fields/OptimizedImages.php
- Craft transform method: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/imagetransforms/CraftImageTransform.php
- Settings and defaults: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/models/Settings.php and https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/config.php
- Resave job: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/jobs/ResaveOptimizedImages.php
- Console commands: https://github.com/nystudio107/craft-imageoptimize/blob/5.0.8/src/console/controllers/OptimizeController.php
- Transform methods: https://github.com/nystudio107/craft-imageoptimize-imgix/blob/5.0.0/src/imagetransforms/ImgixImageTransform.php, https://github.com/nystudio107/craft-imageoptimize-sharp/blob/5.0.0/src/imagetransforms/SharpImageTransform.php, https://github.com/nystudio107/craft-imageoptimize-thumbor/blob/5.0.0/src/imagetransforms/ThumborImageTransform.php
- Craft side (`craftcms/cms` at ref=5.11.5.1): https://github.com/craftcms/cms/blob/5.11.5.1/src/imagetransforms/ImageTransformer.php, https://github.com/craftcms/cms/blob/5.11.5.1/src/queue/Queue.php, https://github.com/craftcms/cms/blob/5.11.5.1/src/services/TemplateCaches.php
- Craft config: https://craftcms.com/docs/5.x/reference/config/general.html#generatetransformsbeforepageload and https://craftcms.com/docs/5.x/reference/config/general.html#runqueueautomatically

When unsure about an ImageOptimize feature, read the source at the installed tag (`vendor/nystudio107/craft-imageoptimize/src/`) before the docs. The docs still carry Craft 3-era wording in places, and see [Docs vs Source](#docs-vs-source).

## Common Pitfalls

- Adding the OptimizedImages field to a Section field layout instead of the Asset Volume field layout — the field must be on the Asset Volume. It generates variants for the asset itself.
- Forgetting to call `.render()` on tag builders — `.imgTag()` and `.pictureTag()` return builder objects, not HTML strings. Chain `.render()` at the end.
- Not running `ddev craft image-optimize/optimize/create` after changing a field's variants on a site where `automaticallyResaveImageVariants` is off — existing assets keep their old variants.
- Missing `--force` when adding WebP variants after the fact — Craft does not recreate a transform file that already exists, so no `.webp` is written next to it.
- Using ImageOptimize on Craft Cloud — Craft Cloud handles transforms via Cloudflare Images at the edge. ImageOptimize is for self-hosted or imgix/Sharp/Thumbor setups. Don't use both. See the `craft-cloud` skill's `assets-and-transforms.md` for Cloud's transform limits and `limitations.md` for the broader plugin-compatibility map.
- Assuming "pre-generated on asset save" covers everything — that is only the OptimizedImages field, and it runs as a queue job. Every **native** transform a template asks for (`asset.getUrl('card')`, `asset.getUrl({ width: 600 })`) still runs ImageOptimize's optimizers and cwebp when Craft generates it, in whichever request or job generates it. See [Request-Time Cost](#request-time-cost).
- `craft.imageOptimize.createOptimizedImages()` in a template — runs the whole variant pipeline in the page request. The docs: "the image transforms, placeholder images, and color palette extraction will all be done at pageload time."
- Optimizer binaries missing on the server — each transform logs `<commandPath> does not exist` as an error and is served unoptimized. It costs little, but the log fills up and nothing is optimized. Check the plugin's settings page, which shows tool status.
- Expecting `image-optimize/optimize/clear` — there is no such command in 5.x. The console controller has `create` and `create-asset` only.
- Every OptimizedImages resave clears **all** asset-dependent template caches — `ResaveOptimizedImages` starts with `invalidateCachesForElementType(Asset::class)`, so every `{% cache %}` block that loaded any asset is cleared on each upload. See [Caching Interaction](#caching-interaction).

## Setup

1. Install the plugin
2. Choose the transform method in Settings (Craft, imgix, Sharp JS, or Thumbor). Only `transformClass` decides which one runs.
3. For the Craft method, install the optimizer binaries on every server and set their paths in `config/image-optimize.php`
4. Create an OptimizedImages field (one per srcset you need)
5. Add the field to the Asset Volume field layout
6. Define image variants (widths, aspect ratios, formats)
7. Generate variants for existing assets: `ddev craft image-optimize/optimize/create`

## Twig API — Tag Builders

### `imgTag()` (Recommended)

```twig
{% set asset = entry.heroImage.one() %}
{% if asset %}
    {{ asset.optimizedImagesField.imgTag()
        .loadingStrategy('lazy')
        .render() }}
{% endif %}
```

Generates a complete `<img>` tag with `srcset`, `sizes`, `width`, `height`, `loading`, and `decoding` attributes.

### `pictureTag()`

```twig
{% set asset = entry.heroImage.one() %}
{% if asset %}
    {{ asset.optimizedImagesField.pictureTag()
        .loadingStrategy('lazy')
        .render() }}
{% endif %}
```

Generates `<picture>` with `<source>` elements for WebP/AVIF and fallback `<img>`.

### Chained Configuration

Both tag builders support chaining:

```twig
{{ asset.optimizedImagesField.imgTag()
    .loadingStrategy('lazy')
    .sizes('(max-width: 768px) 100vw, 50vw')
    .render() }}

{{ asset.optimizedImagesField.imgTag()
    .loadingStrategy('eager')
    .render() }}
```

### Object Configuration

```twig
{{ asset.optimizedImagesField.imgTag({
    'loadingStrategy': 'lazy',
    'sizes': '100vw',
}).render() }}
```

### Loading Strategies

| Strategy | Output | Use for |
|----------|--------|---------|
| `'lazy'` | `loading="lazy" decoding="async"` | Below-the-fold images |
| `'eager'` | `fetchpriority="high"` | Hero/LCP images |
| `'lazySizes'` | LazySizes.js integration | Legacy browser support |

## Twig API — Direct Access

### Source URLs and Srcsets

```twig
{% set optimized = asset.optimizedImagesField %}

{# Single best-fit URL #}
{{ optimized.src }}

{# Full srcset string #}
{{ optimized.srcset }}

{# WebP srcset #}
{{ optimized.srcsetWebp }}

{# Srcset filtered by width #}
{{ optimized.srcsetMinWidth(600) }}
{{ optimized.srcsetMaxWidth(1200) }}

{# Max available width (prevent upscaling) #}
{{ optimized.maxSrcsetWidth }}
```

### Placeholders (Lazy Loading)

```twig
{# Low-quality image placeholder (base64 inline) #}
{{ optimized.placeholderImage }}

{# SVG silhouette placeholder #}
{{ optimized.placeholderSilhouette }}

{# Solid color box placeholder #}
{{ optimized.placeholderBox }}

{# Arbitrary placeholder box #}
{{ craft.imageOptimize.placeholderBox(100, 100, '#CCC') }}
```

### Color Palette

```twig
{# Extracted dominant colors from the image #}
{% for color in optimized.colorPalette %}
    <div style="background-color: {{ color }}"></div>
{% endfor %}
```

### Dimensions

```twig
{{ optimized.originalImageWidth }}
{{ optimized.originalImageHeight }}
{{ optimized.placeholderWidth }}
{{ optimized.placeholderHeight }}
```

## Request-Time Cost

### Native transforms (Craft transform method)

ImageOptimize listens to `ImageTransformer::EVENT_TRANSFORM_IMAGE`. That event fires inside Craft's own transform generation, after Craft has resized the image and before the file is written. `Optimize::handleGenerateTransformEvent()` then does the following, synchronously in the same PHP process:

1. Applies filters (auto-sharpen when scaled down by `sharpenScaledImagePercentage` or more) and saves a temp file
2. Runs every tool listed in `activeImageProcessors[<format>]` as a shell command (`proc_open`, or `exec` as a fallback): jpegoptim for jpg, optipng for png, svgo for svg, gifsicle for gif by default
3. Runs every tool in `activeImageVariantCreators[<format>]`: cwebp for jpg, png and gif by default. It writes `<transform>.jpg.webp` next to the transform in the volume.

This only happens for the Craft method (`transformMethod instanceof CraftImageTransform`). A default JPEG transform costs the GD/Imagick resize plus two child processes. **Which request pays depends on who generates the transform:**

| Trigger | Process that runs the optimizers |
|---------|----------------------------------|
| `asset.getUrl(transform)` in a template, Craft `generateTransformsBeforePageLoad` `true` | The page request, before render |
| Same, `generateTransformsBeforePageLoad` `false` (Craft default) | The first request for the temporary `actions/assets/generate-transform?transformId=N` URL (the browser's image request), or the queued `GenerateImageTransform` job, whichever runs first. Never the page request. |
| OptimizedImages field variants | The `ResaveOptimizedImages` queue job, queued from the field's `afterElementSave()` on upload, move or save |
| Image edited in the CP image editor (`assets/save-image`) | That CP request (variants are rebuilt inline so the HUD shows them) |
| `craft.imageOptimize.createOptimizedImages()` in Twig | The page request |
| `image-optimize/optimize/create` | The console process |

With imgix, Sharp or Thumbor, nothing runs on your server. `Asset::EVENT_BEFORE_DEFINE_URL` returns the service URL for any `getUrl()` call **that has a transform**, so Craft never generates a local file. Untransformed `asset.url` is left to Craft.

ImageOptimize never modifies the uploaded original. None of its handlers write to the source file. There is no setting named `optimizeOriginals` or `autoGenerateVariants` in 5.x. The settings that control timing are below.

### OptimizedImages field: variants, placeholders, palette

On upload, move, or save of an asset whose volume has an OptimizedImages field, the field queues `ResaveOptimizedImages` (`OptimizedImages::resaveAsset()`). When the job runs, `populateOptimizedImageModel()` builds a transform URL for every variant × retina size through `CraftImageTransform::getTransformUrl()`. That forces Craft's `generateTransformsBeforePageLoad` to `true` while it builds them, so each transform is generated, and optimized as above, inside the job. The resulting URLs are stored in the asset's content. Reading the field in a template is a content read: no generation, no optimizer.

Placeholders are made once per asset per field, from the first variant (`OptimizedImages::generatePlaceholders()`):

| Step | Setting (default) | Cost |
|------|-------------------|------|
| Local copy of the original, scaled and cropped to 300px wide | `generatePlaceholders` (`true`) | `TransformHelper::getLocalImageSource()` downloads the original first when the volume is remote (S3 and similar) |
| 16px-wide base64 placeholder image | `generatePlaceholders` (`true`) | Small |
| 5-colour dominant palette (ColorThief) and lightness | `createColorPalette` (`true`) | The setting's own docblock: "It takes a bit of time" |
| Traced SVG silhouette (Potracio, needs GD) | `createPlaceholderSilhouettes` (`false`) | The slowest step. Capped at 32 KB by `capSilhouetteSvgSize`. The docs note it "can add to the db size". |

All of it runs in the queue job. In Twig, `createOptimizedImages(asset, variants, generatePlaceholders)` skips placeholders and palette unless you pass the third argument `true`.

### Settings that decide timing

`config/image-optimize.php` (multi-environment). Defaults are from `Settings.php` / `config.php` at v5.0.8.

| Setting | Default | What it controls |
|---------|---------|------------------|
| `transformClass` | `CraftImageTransform::class` | The only transform method that runs. Its settings come from `imageTransformTypeSettings[<class>]`. |
| `generateTransformsBeforePageLoad` | `true` | ImageOptimize's own setting, not Craft's. The docblock says "Should image variant be created on Asset save (aka BeforePageLoad)". In code, `CraftImageTransform::getTransformUrl()` sets Craft's setting to `true` for the URLs ImageOptimize builds (field variants, `createOptimizedImages()`), then restores it. It does not touch `asset.getUrl()` calls in your templates. |
| `automaticallyResaveImageVariants` | `true` | Queues a resave of every asset in the affected volume(s) when you save an OptimizedImages field, a volume whose layout has one, or the plugin settings. Each asset gets the full variant and placeholder run. On large volumes, turn it off and run the console command in a quiet window. |
| `generatePlaceholders` / `createColorPalette` / `createPlaceholderSilhouettes` | `true` / `true` / `false` | Per-asset cost in the resave job (table above). Turn off what the templates never read. |
| `activeImageProcessors` / `imageProcessors` | jpegoptim, optipng, svgo, gifsicle at `/usr/bin/…` | Which tools run per format, and their paths and flags. A name in the active list with no entry in `imageProcessors` is skipped silently. An entry whose `commandPath` is not a file logs `… does not exist` as an error on every transform. |
| `activeImageVariantCreators` / `imageVariantCreators` | cwebp for jpg, png, gif | Same rules. This is where `.webp` files come from. |

Keep ImageOptimize's `generateTransformsBeforePageLoad` at `true`. This next point is an inference from the source, not something the docs state: with it `false`, the field would store Craft's temporary `generate-transform` URLs in content. Every later view of a variant would then go through PHP and a redirect, and `{% cache %}` would refuse any block that contained one.

## Transform Methods

| Method | `transformClass` | Settings (`imageTransformTypeSettings[<class>]`) | Who does the work |
|--------|------------------|---------------------------------------------------|-------------------|
| Craft | `nystudio107\imageoptimize\imagetransforms\CraftImageTransform` | none (tool paths are top-level settings) | Your server: GD/Imagick plus the optimizer binaries |
| imgix | `nystudio107\imageoptimizeimgix\imagetransforms\ImgixImageTransform` | `domain`, `apiKey` (purging), `securityToken` (signed URLs) | imgix |
| Sharp JS | `nystudio107\imageoptimizesharp\imagetransforms\SharpImageTransform` | `baseUrl` | Your Sharp service, e.g. AWS Serverless Image Handler; the transform is encoded as base64 JSON in the URL |
| Thumbor | `nystudio107\imageoptimizethumbor\imagetransforms\ThumborImageTransform` | `baseUrl`, `securityKey`, `includeBucketPrefix` | Your Thumbor server |

Configure in CP → Settings → ImageOptimize → Transform Method, or set `transformClass` in `config/image-optimize.php`.

**Misconfiguration: a list naming sharp, thumbor and imgix on a site that uses native transforms.** That list is usually `defaultImageTransformTypes`. It only feeds the settings dropdown: `Optimize::getAllImageTransformTypes()` merges it with `DEFAULT_IMAGE_TRANSFORM_TYPES`, which already contains all four. Only `transformClass` is instantiated (`ImageOptimize::setImageTransformComponent()`). So the list does nothing, good or bad, and can be deleted. Check `transformClass` itself:

- **`transformClass` is a remote method, but the service was never set up.** None of the three checks that its service exists. Sharp with an empty `baseUrl` builds `/<base64>` URLs on your own domain, which 404. imgix and Thumbor build URLs from whatever is in their settings. No server work happens, so pages look fast while images break. Every Craft transform in templates is affected, not just the field.
- **`transformClass` is Craft, but `activeImageProcessors` names a tool that isn't installed.** Each transform logs an error and ships unoptimized. Remove the tool from the active list or install it.
- A remote method plus optimizer binaries is redundant. The optimizers only run for the Craft method.

## Queue Runner

`runQueueAutomatically` (Craft, default `true`): "Whether Craft should run pending queue jobs automatically when someone visits the control panel." The source goes further than the docs. When a non-Ajax **site** request pushes a job, `Queue::push()` registers `Queue::handleResponse()`, which appends an inline `<script>` before `</body>` that XHRs `actions/queue/run`. `QueueController::actionRun()` then closes the connection and runs the queue inside that web PHP worker (`App::maxPowerCaptain()`). With the Craft method, that means:

- `ResaveOptimizedImages` jobs (whole-volume resaves too) and `GenerateImageTransform` jobs, each running jpegoptim and cwebp per transform, run in your web PHP workers and compete with page requests. They are also subject to web limits; ImageOptimize's own docs warn about `max_execution_time`.
- On the front end, any page that renders a missing native transform with Craft's `generateTransformsBeforePageLoad` `false` pushes a `GenerateImageTransform` job and gets the injected script.
- The injected script has no nonce. Under a strict CSP it is blocked, so jobs wait for a CP visit or a CLI runner.

**Run the queue from the CLI instead** (the `GeneralConfig` docblock: "an alternate queue worker *must* be set up separately, either as an always-running daemon, or a cron job that runs the `queue/run` command every minute"):

```bash
# .env on production (Craft applies CRAFT_* general-config overrides itself)
CRAFT_RUN_QUEUE_AUTOMATICALLY=false

# cron, every minute
* * * * * /path/to/project/craft queue/run

# or a daemon under systemd/supervisor
/path/to/project/craft queue/listen --verbose
```

Recommend it whenever ImageOptimize uses the Craft method on a self-hosted production server, editors upload in bulk, the site sends a strict CSP, or the host has few PHP workers. Keep `true` locally in DDEV. On Servd, use its Dedicated Queue Runner (`servd` skill). Craft Cloud runs the queue itself (`craft-cloud` skill). Config details: the `craftcms` skill's `config-general-extended.md`.

## Caching Interaction

Does switching Craft's `generateTransformsBeforePageLoad` to `false` change ImageOptimize output?

- **OptimizedImages field (`src`, `srcset`, `srcsetWebp`, placeholders, palette):** no. They are built in the queue job with Craft's setting forced on, so they are real file URLs (or service URLs) stored in content. They are safe inside `{% cache %}` and in Blitz-cached pages. Placeholders are data URIs or inline SVG in content.
- **Native transforms your templates request (`asset.getUrl('card')`):** yes. They follow Craft's setting, and ImageOptimize does not change that. With `false`, a missing transform renders as a temporary `generate-transform` URL. `{% cache %}` will not store a block containing one (`TemplateCaches::endTemplateCache()` checks for `assets/generate-transform`), and the page response gets no-cache headers. The optimizers run on the image request.
- **WebP from a temporary URL is broken until generation.** This is an inference from the source. The docs suggest `asset.getUrl('someTransform') ~ '.webp'`, and `ImageTransform::appendExtension()` inserts `.webp` into the URL path. Both turn a temporary URL into one that does not resolve: `…generate-transform?transformId=12.webp`, or `…generate-transform.webp?transformId=12`. In a `<picture>`, the browser picks the `<source>` and does not fall back to `<img>`, so the first visitor sees a broken image. Fix it with the field (always real URLs), with Craft's native `format: 'webp'` transform instead of the suffix, or by pre-generating transforms.

**Every OptimizedImages resave clears all asset-dependent template caches.** `ResaveOptimizedImages::execute()` begins with `Craft::$app->getElements()->invalidateCachesForElementType(Asset::class)`, which invalidates the `element::craft\elements\Asset` tag. Craft adds that tag to any cache that ran an asset query or rendered an asset (`ElementQuery::getCacheTags()`, `Elements::collectCacheInfoForElement()`). So each upload into a volume with an OptimizedImages field clears every `{% cache %}` block that touched any asset, such as a logo in a cached header or card images in a cached listing. If those blocks are expensive, keep asset output out of them, or accept the rebuild.

## Docs vs Source

Where they disagree, the source at v5.0.8 wins:

- configuring.md says imgix is used "for all Asset URLs, including the original image". Source: `Optimize::handleGetAssetUrlEvent()` returns `null` ("let Craft handle it") when no transform is requested, so untransformed originals keep Craft's own URL with every remote method.
- using.md says "by default the generation of the dominant color palette and the generation of the placeholder silhouette are off". That is true only for `createOptimizedImages()` in Twig. For the field, `createColorPalette` defaults to `true` (`Settings.php`).
- The `generateTransformsBeforePageLoad` docblock says "Should image variant be created on Asset save". In code, it decides whether ImageOptimize-built Craft transform URLs are generated immediately, wherever they are built. Field variants are created in a queue job either way.
- advanced.md recommends the Async Queue plugin and still says "Craft CMS 3" in places. On Craft 5, use a CLI queue runner (above).

## Performance Checklist (Self-Hosted)

**Settings to check**

- [ ] Craft `generateTransformsBeforePageLoad` is `false` (the default). Not enabled to hide `generate-transform` URLs.
- [ ] Production has `runQueueAutomatically` `false`, plus a `queue/run` cron or `queue/listen` daemon. `ddev craft queue/info` shows nothing stuck.
- [ ] `transformClass` matches the infrastructure. If it is remote, its `imageTransformTypeSettings` are filled in and the service answers.
- [ ] Every tool in `activeImageProcessors` and `activeImageVariantCreators` exists at its `commandPath` on every server (`ls -l /usr/bin/jpegoptim /usr/bin/cwebp`, or the plugin settings page). Remove the ones you don't ship.
- [ ] ImageOptimize `generateTransformsBeforePageLoad` is `true` (the default).
- [ ] `createPlaceholderSilhouettes` and `createColorPalette` are on only if the templates use them.
- [ ] No `craft.imageOptimize.createOptimizedImages()` in front-end templates.
- [ ] On large volumes, `automaticallyResaveImageVariants` is off and resaves run from the CLI.

**Confirm no optimizer runs during a page view**

1. Upload a new image (never transformed before) and put it on a test page rendered with native transforms, e.g. the `image-presets.md` atom on the non-ImageOptimize path.
2. With `devMode` on, load the page once and open the debug toolbar's **Profiling** panel. ImageOptimize wraps its work in `Craft::beginProfile()`, so `handleGenerateTransformEvent`, `optimizeImage` and `createImageVariants` must **not** appear for the page request. If they do, Craft's `generateTransformsBeforePageLoad` is `true`, or the template calls `createOptimizedImages()`.
3. Time it: `curl -s -o /dev/null -w '%{time_total}\n' https://site.ddev.site/test-page/`. It should match an equivalent page with already-generated images. The HTML holds `generate-transform` URLs on this first load.
4. Request one of those URLs: `curl -sL -o /dev/null -w '%{http_code} %{time_total}\n' 'https://site.ddev.site/actions/assets/generate-transform?transformId=N'`. That request carries the resize and optimizer cost and ends in a redirect to the file. Reload the page: real file URLs now, and no new profiling entries.
5. ImageOptimize logs an info line per optimized transform (`… -> Original: 129.5K, Optimized: 100.8K -> Savings: 28.4%`). Find which log has it: web for page and image requests, console for the CLI runner. That tells you which process paid.

## Console Commands

```bash
# Queue a resave of every OptimizedImages field in every volume, then run the queue in this process
ddev craft image-optimize/optimize/create

# One volume, one field
ddev craft image-optimize/optimize/create myVolumeHandle --field=heroImage

# Recreate files that already exist (required after adding WebP or changing tool options)
ddev craft image-optimize/optimize/create --force

# One asset by ID
ddev craft image-optimize/optimize/create-asset 101 --force

# Only queue the jobs; let the cron/daemon runner pick them up
ddev craft image-optimize/optimize/create --queue
```

Without `--queue`, both commands run the Craft queue in the console process (`OptimizeController::runCraftQueue()`). That also runs any other waiting jobs. There is no `clear` command.

## Config File

```php
// config/image-optimize.php (values shown are the 5.0.8 defaults unless commented)
return [
    '*' => [
        'transformClass' => \nystudio107\imageoptimize\imagetransforms\CraftImageTransform::class,

        // Generate ImageOptimize-built Craft transforms immediately (keep true)
        'generateTransformsBeforePageLoad' => true,

        // Resave the whole volume when a field, volume or these settings change
        'automaticallyResaveImageVariants' => true,

        // Per-asset work in the resave job; turn off what templates never read
        'generatePlaceholders' => true,
        'createColorPalette' => true,
        'createPlaceholderSilhouettes' => false,

        // Sharpen transforms scaled down by this percentage or more
        'autoSharpenScaledImages' => true,
        'sharpenScaledImagePercentage' => 50,

        // Lower quality for retina variants
        'lowerQualityRetinaImageVariants' => true,

        // Only list tools installed on every server
        'activeImageProcessors' => [
            'jpg' => ['jpegoptim'],
            'png' => ['optipng'],
            'svg' => ['svgo'],
            'gif' => ['gifsicle'],
        ],
        'activeImageVariantCreators' => [
            'jpg' => ['cwebp'],
            'png' => ['cwebp'],
            'gif' => ['cwebp'],
        ],
    ],
];
```

Copy the plugin's own `src/config.php` as the starting point. It also holds the `imageProcessors` / `imageVariantCreators` path and flag definitions.

## GraphQL

```graphql
{
  entries(section: "news") {
    ... on news_article_Entry {
      heroImage {
        optimizedImagesField {
          src
          srcset
          srcsetWebp
          placeholderImage
          originalImageWidth
          originalImageHeight
        }
      }
    }
  }
}
```

## Pair With

- **Imager-X** — alternative transform engine with more CDN backend options
- **Small Pics** — URL-based image service (Imager-X transformer or standalone)
