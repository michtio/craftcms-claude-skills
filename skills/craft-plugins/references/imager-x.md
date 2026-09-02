# Imager X

Image transforms, optimization and manipulation by SpaceCat Ninja (André Elvan). Transforms are
file-based — no database queries and no transform index. Transforms Assets (local or cloud),
local paths, external URLs, and already-transformed images, and can hand the work off to a
third-party service instead of doing it locally. The compact template syntax and named
transforms make responsive image sets cheap to write and maintain.

`spacecatninja/imager-x` — Lite $49 / Pro $99

This reference covers the essentials. For the full transform parameter set, per-transformer
feature differences, automatic generation and the Power Pack in depth, there is a dedicated
Imager X skill maintained by the plugin author — install it with
`/plugin marketplace add spacecatninja/imager-x-skills`. Nothing here depends on it.

## Contents

- [Documentation](#documentation)
- [Common Pitfalls](#common-pitfalls)
- [Twig API](#twig-api)
- [Named Transforms](#named-transforms-configimager-x-transformsphp)
- [Config File](#config-file)
- [Automatic Generation](#automatic-generation-pro)
- [Console Commands](#console-commands)
- [Transformers](#transformers)
- [When to Use: Imager X vs Native vs ImageOptimize](#when-to-use-imager-x-vs-native-vs-imageoptimize)
- [Multi-Site](#multi-site)
- [Pair With](#pair-with)

## Documentation

- Overview and editions: https://imager-x.spacecat.ninja/overview
- Usage and quick syntax: https://imager-x.spacecat.ninja/usage/
- Templating reference: https://imager-x.spacecat.ninja/templating
- Transform parameters: https://imager-x.spacecat.ninja/transform-parameters
- Configuration: https://imager-x.spacecat.ninja/configuration
- Named transforms: https://imager-x.spacecat.ninja/usage/named-transforms
- Automatic generation: https://imager-x.spacecat.ninja/usage/generate
- Effects: https://imager-x.spacecat.ninja/effects
- GitHub: https://github.com/spacecatninja/craft-imager-x
- Power Pack: https://github.com/spacecatninja/craft-imager-x-power-pack
- Dedicated Imager X skill (deeper coverage): https://github.com/spacecatninja/imager-x-skills

When unsure about an Imager X feature, `WebFetch` the docs site.

## Common Pitfalls

- There is no `|transform` filter and no `'400x300'` string syntax. The only Twig filter Imager X
  adds is `|srcset`. A *string* second argument to `transformImage()` is always a named transform
  handle.
- `transformImages()` does not exist. It is always `transformImage()` — it returns a single model
  for a single transform object, and an array for an array of them.
- `quality` is not a real transform parameter. It is remapped to `jpegQuality` and then removed,
  so it does nothing for WebP, AVIF or JPEG XL. Use `webpQuality`, `avifQuality` or `jxlQuality`
  explicitly.
- `position` is silently dropped unless `mode` is `crop` or `croponly`. Setting a crop position on
  a `fit` transform has no effect. Craft's position keywords are hyphenated (`top-center`); a
  space-separated value throws `Unsupported operand types: string / int`.
- Quick syntax needs real integers. `['400', '1200']` is not detected as quick syntax and throws;
  `[400, 1200]` works. Cast values that may arrive as strings from a field or config.
- Every transformer except `craft` is Pro-only and ships as a separate plugin. Setting one on Lite
  throws `ImagerException`. Automatic generation, the generate console command, external storages
  and GraphQL support are Pro too.
- Imager X's transform cache is files on disk, not a Craft cache component. `ddev craft
  cache/flush` does not clear it — use `ddev craft imager-x/clear-caches/transforms-cache` or the
  CP utility.
- Third-party transformers degrade silently. On Imgix, `getPath()`, `getExtension()`,
  `getMimeType()`, `getSize()`, `getDataUri()` and `getBase64Encoded()` return empty strings rather
  than failing, so templates depending on them break quietly. Only `url`, `width` and `height` are
  safe across transformers.
- Automatic generation runs through queue jobs. With a cron-driven queue runner the front end still
  transforms on demand until the job runs — use a daemon.

## Twig API

`craft.imagerx` and `craft.imager` are the same variable. Prefer `craft.imagerx`.

```php
transformImage(Asset|string|null $image, array|string $transforms,
               ?array $transformDefaults = null, ?array $configOverrides = null)
```

### Quick Syntax

The compact form for "a range of widths, optionally a ratio and a format". This is the syntax to
reach for by default.

```twig
{% set imgs = craft.imagerx.transformImage(asset, [400, 1600]) %}
{% set imgs = craft.imagerx.transformImage(asset, [400, 1600, 16/9]) %}
{% set imgs = craft.imagerx.transformImage(asset, [400, 1600, 'webp']) %}
{% set imgs = craft.imagerx.transformImage(asset, [400, 1600, { ratio: 16/9, format: 'webp', webpQuality: 78 }]) %}
```

The two integers are the smallest and largest width; slot 3 is a ratio (numeric), a format
(string), or an object of transform defaults. Intermediate sizes are **filled automatically** —
`[400, 1600]` yields 400, 700, 1000, 1300, 1600. `fillInterval` is ignored in this mode; raise
`autoFillCount` if a wide range gets too coarse, or set `fillTransforms: false` for exactly the two
sizes you wrote.

```twig
<img src="{{ imgs|first.url }}"
     srcset="{{ imgs|srcset }}"
     sizes="(min-width: 768px) 50vw, 100vw"
     width="{{ imgs|first.width }}"
     height="{{ imgs|first.height }}"
     alt="{{ asset.alt }}"
     loading="lazy">
```

`|srcset` is the only filter Imager X registers. It takes a descriptor — `'w'` (default), `'h'`,
or `'w+h'` — and de-duplicates candidates that resolve to the same width.

### Full Syntax

Use it when sizes differ by more than width — per-size modes, effects, watermarks, art-directed
crops.

```twig
{% set imgs = craft.imagerx.transformImage(
    asset,
    [{ width: 400 }, { width: 800 }, { width: 1200 }],
    { ratio: 16/9, format: 'webp', webpQuality: 78 },
    { allowUpscale: false }
) %}
```

The third argument is defaults merged into every transform; the fourth is Imager X config
overrides for this call only.

### Named Transforms

```twig
{% set imgs = craft.imagerx.transformImage(asset, 'hero') %}
```

Defined in `config/imager-x-transforms.php` (below). `craft.imagerx.hasNamedTransform(handle)`
guards a handle that comes from content.

### Responsive Markup with the Power Pack

`spacecatninja/imager-x-power-pack` is a free companion plugin (MIT) that generates the markup —
`srcset`, `sizes`, intrinsic dimensions, `alt`, focal-point `object-position`, loading hints and
placeholders. It is the recommended way to write responsive images, and it removes most of the
ways hand-rolled `<picture>` markup goes wrong.

```bash
ddev composer require spacecatninja/imager-x-power-pack
ddev craft plugin/install imager-x-power-pack
```

```twig
{# One image #}
{{ ppimg(asset, [400, 1600, 16/9], {
    sizes: '(min-width: 1024px) 33vw, 100vw',
    class: 'w-full h-auto'
}) }}

{# AVIF and WebP with a fallback #}
{{ pppicture([
    [asset, [400, 1600, 16/9, 'avif'], 'avif'],
    [asset, [400, 1600, 16/9, 'webp'], 'webp'],
    [asset, [400, 1600, 16/9]],
], { sizes: '100vw' }) }}
```

Each source is `[image, transform, mediaQuery, format]`. The last source becomes the `<img>`
fallback; the format slot only sets `type="image/…"`, so the format must be in the transform too.
`loading` defaults to `lazy`, so pass `loading: 'eager'` and `fetchpriority: 'high'` on the LCP
image.

### Placeholders and Colors

```twig
{# Data-URI placeholder at the right ratio #}
{{ craft.imagerx.placeholder({ width: 160, height: 90, color: '#eeeeee' }) }}

{# Dominant color and palette — pass a small transform, not the full-size original #}
{% set small = craft.imagerx.transformImage(asset, { width: 100 }) %}
{% set bg = craft.imagerx.getDominantColor(small) %}
{% set palette = craft.imagerx.getColorPalette(small, 5) %}

{# WCAG contrast, for picking text color over an image-derived background #}
{% set onDark = craft.imagerx.getContrastRatio(bg, '#ffffff') >= 4.5 %}
```

Also available: `serverSupportsWebp()`, `serverSupportsAvif()`, `clientSupports(format)`,
`isAnimated(asset)`, `transformer()`.

## Named Transforms (`config/imager-x-transforms.php`)

```php
// config/imager-x-transforms.php
return [
    'hero' => [
        'displayName' => 'Hero',
        'transforms' => [800, 2400, 16 / 9],
        'defaults' => ['jpegQuality' => 78],
    ],
    'thumbnail' => [
        'displayName' => 'Thumbnail',
        'transforms' => [200, 600],
        'defaults' => ['ratio' => 1, 'mode' => 'crop'],
        'generateFlags' => ['dominantColor'],
    ],
];
```

Keys: `transforms` (full syntax, quick syntax, a single object, or a string naming another named
transform), `defaults`, `configOverrides`, `generateFlags` (`blurhash`, `palette`,
`dominantColor`, precomputed during automatic generation), `displayName`.

Template arguments win over the config file, and `transforms` may name another named transform,
which makes format variants cheap:

```php
'heroAvif' => [
    'transforms' => 'hero',
    'defaults' => ['format' => 'avif', 'avifQuality' => 62],
],
```

Named transforms are required for automatic generation and for GraphQL.

## Config File

```php
// config/imager-x.php
return [
    '*' => [
        'transformer' => 'craft',
        'imagerSystemPath' => '@webroot/imager/',
        'imagerUrl' => '/imager/',
        'jpegQuality' => 78,
        'webpQuality' => 78,
        'avifQuality' => 65,
        'interlace' => 'line',
        'allowUpscale' => false,
        'removeMetadata' => true,
    ],
    'dev' => [
        // Work without the real assets
        // 'mockImage' => '/uploads/site/placeholder.jpg',
    ],
];
```

`optimizeType` accepts only `'job'` (default — optimize in a queue job after the response) and
`'runtime'`. Optimizers are off by default and are a marginal gain next to serving a modern
format; enable them via `optimizers` plus `optimizerConfig` when you must serve JPEG or PNG.
Available handles: `jpegoptim`, `jpegtran`, `mozjpeg`, `optipng`, `pngquant`, `gifsicle`,
`tinify`, `kraken`, `imageoptim`. A missing binary is silent — optimization just does not happen.

Imager X uses Craft's own `imageDriver` general config setting; it has none of its own. Imagick
unlocks most effects, animated GIFs, `resizeFilter`, `removeMetadata` and watermark opacity.

## Automatic Generation (Pro)

Generate transforms when an asset is uploaded or an element is saved, instead of during a page
request.

```php
// config/imager-x-generate.php
return [
    'volumes' => [
        'images' => ['thumbnail', 'seoOpenGraph'],
    ],
    'fields' => [
        'heroImage' => ['hero'],
        'contentBlocks:imageBlock.image' => ['contentImage'],
    ],
    'elements' => [
        [
            'elementType' => \craft\elements\Entry::class,
            'criteria' => ['section' => 'events'],
            'fields' => ['heroImage'],
            'transforms' => ['eventHero'],
        ],
    ],
];
```

If this file does not exist, no listeners are registered at all. Field handles support
`matrixField:entryTypeHandle.field`, `*` for all types, and `fieldHandle[offset:limit]`. Only
assets whose extension is in `safeFileFormats` (`jpg`, `jpeg`, `gif`, `png`, `webp`) are
processed. Everything runs as queue jobs.

## Console Commands

```bash
# Generate the transforms configured for a volume (Pro)
ddev craft imager-x/generate --volume=images

# Specific named transforms, queued instead of inline
ddev craft imager-x/generate --volume=images --transforms=hero,thumbnail --queue

# By field, forcing regeneration of existing files
ddev craft imager-x/generate --field=heroImage --transforms=hero --force

# Clear caches
ddev craft imager-x/clear-caches/all
ddev craft imager-x/clear-caches/transforms-cache
ddev craft imager-x/clear-caches/runtime-cache

# Remove transforms older than a duration
ddev craft imager-x/clean --volume=images --duration=P1M
```

`--transforms` is a comma-separated list of **named transform handles** only; quick-syntax arrays
cannot be passed on the command line. Other options: `--folderId`, `--recursive`, `--limit`,
`--offset`. `--volume` and `--field` are mutually exclusive.

## Transformers

A transformer decides *where* the transform happens. `craft` is the only one available on Lite;
every other handle requires Pro **and** its own companion plugin.

| Handle | Plugin | Notes |
|--------|--------|-------|
| `craft` | built in | GD/Imagick on the server. Full feature set, works with optimizers and storages |
| `imgix` | `imager-x-imgix-transformer` | Most complete remote option. Supports `auto: format` |
| `imgixdownload` | `imager-x-imgix-download-transformer` | Imgix transforms stored locally. `auto: format` stops working |
| `imagekit` | `imager-x-imagekit-transformer` | Focal points become anchor keywords; no effects converted |
| `imageboss` | `imager-x-imageboss-transformer` | Assets only; no `croponly`/`stretch` |
| `cloudflareimages` | `imager-x-cloudflare-images-transformer` | Crop modes, size, quality, format only. Does not store images |
| `awsserverless` | `imager-x-aws-serverless-transformer` | AWS-bucket assets only; no `cropZoom` |
| `bunny` | `imager-x-bunny-transformer` | `crop`/`fit` only |
| `craftcloud` | `imager-x-craft-cloud-transformer` | Craft Cloud edge transforms |

Set it with `'transformer' => 'imgix'`. Each transformer has its own config file
(`imager-x-imgix-transformer.php` and so on), usually with a `profiles` array and a
`defaultProfile`. Pass service-specific options with the `transformerParams` transform parameter:

```twig
{% set imgs = craft.imagerx.transformImage(asset, [400, 1200], { transformerParams: { sharp: 10 } }) %}
```

Do not switch transformer per transform — `transformer` is excluded from the filename hash, so
two transforms differing only by transformer collide on one cached file. Switch per environment
instead, and give each environment its own `imagerSystemPath`.

External storages (S3, Google Cloud Storage, DigitalOcean Spaces) are separate Pro plugins and are
independent of the transformer — they are how you keep `craft`'s full feature set on an ephemeral
filesystem.

## When to Use: Imager X vs Native vs ImageOptimize

- **Native transforms** — a single resize, nothing more. No extra plugin needed.
- **ImageOptimize** — the field owns variant config, tag builders handle output;
  convention-over-configuration. See `image-optimize.md`.
- **Imager X** — compact syntax for responsive sets, named transforms in config, automatic
  generation, effects and watermarks, or offloading transforms to a service.

## Multi-Site

Transforms operate on Assets, which exist independently of sites, so transforms themselves are not
site-scoped. `imagerUrl` **is** localizable — pass an array keyed by site handle to serve
transforms from a different domain per site:

```php
'imagerUrl' => [
    'default' => 'https://example.com/imager/',
    'norwegian' => 'https://example.no/imager/',
],
```

Volume-based automatic generation skips propagation saves, so a transform is not generated once
per site.

## Pair With

- **ImageOptimize** — overlapping scope; pick one as the responsive-image layer rather than both
- **Blitz** — pre-warm pages with heavy transforms so the first visitor does not pay for them
- **SEOmatic** — use a named transform for OG and Twitter card images
