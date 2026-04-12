# Imager-X

Advanced image transformation plugin by Spacecraft Technologies. Extends Craft's native transforms with batch generation, named presets, effects/filters, post-transform optimization, external storage (S3, GCS), and alternative transform drivers (Imgix, Cloudflare). The go-to solution for responsive image workflows.

`spacecrafttechnologies/imager-x` -- $99

## Documentation

- Overview: https://imager-x.spacecat.ninja/overview.html
- Configuration: https://imager-x.spacecat.ninja/configuration.html
- Transforms: https://imager-x.spacecat.ninja/usage/transforms.html
- Named transforms: https://imager-x.spacecat.ninja/usage/named-transforms.html
- Template helpers: https://imager-x.spacecat.ninja/usage/template-helpers.html
- GitHub: https://github.com/spacecrafttechnologies/craft-imager-x

When unsure about an Imager-X feature, `WebFetch` the docs site.

## Common Pitfalls

- Transform driver mismatch -- configured for Imgix or Cloudflare but credentials are wrong or missing. Transforms silently fall back or throw opaque errors. Verify the driver settings in `config/imager-x.php` before debugging template output.
- Imager-X has its own cache, separate from Craft's asset transform cache. Clearing Craft caches does not clear Imager-X. Use `ddev craft imager-x/clear` or CP Utilities to purge.
- Memory exhaustion on large source images with the local (GD/Imagick) driver. Set `imgixConfig` or `cloudflareConfig` for production, or increase PHP memory limit and set `optimizeType` to reduce output size.
- Missing optimizer binaries (jpegoptim, optipng, gifsicle, svgo) silently skip post-transform optimization. Install them in your DDEV or server environment and verify with `ddev craft imager-x/generate --dry-run`.
- AVIF output depends on the server's Imagick/GD build supporting the format. If AVIF transforms return errors or fallback to JPEG, check `phpinfo()` for AVIF support. Use an external driver (Imgix, Cloudflare) to sidestep server-level codec issues.
- Forgetting `fillTransforms: true` when generating responsive sets -- without it, Imager-X only returns the widths you explicitly list. With it enabled, intermediate sizes are auto-filled for smoother srcset coverage.

## Twig API

### Single Transform

```twig
{% set asset = entry.heroImage.one() %}
{% if asset %}
    {% set transformed = craft.imagerx.transformImage(asset, { width: 800 }) %}
    <img src="{{ transformed.url }}" width="{{ transformed.width }}" height="{{ transformed.height }}">
{% endif %}
```

### Batch Transforms

```twig
{% set transforms = craft.imagerx.transformImage(asset, [
    { width: 400 },
    { width: 800 },
    { width: 1200 },
    { width: 1600 },
], { format: 'webp', quality: 80 }) %}
```

The third parameter sets defaults applied to every transform in the array.

### Srcset Helper

```twig
{% set transforms = craft.imagerx.transformImage(asset, [
    { width: 400 },
    { width: 800 },
    { width: 1200 },
]) %}

<img src="{{ transforms[1].url }}"
     srcset="{{ craft.imagerx.srcset(transforms) }}"
     sizes="(max-width: 768px) 100vw, 50vw"
     width="{{ transforms[1].width }}"
     height="{{ transforms[1].height }}"
     loading="lazy">
```

### Named Transforms

```twig
{% set transforms = craft.imagerx.transformImage(asset, 'hero') %}

<img src="{{ transforms[0].url }}"
     srcset="{{ craft.imagerx.srcset(transforms) }}"
     sizes="100vw">
```

Named transforms are defined in `config/imager-x-transforms.php` (see below).

### Checking if Installed

```twig
{% if craft.imagerx is defined %}
    {# Imager-X available #}
{% endif %}
```

### Additional Helpers

```twig
{# Base64-encoded placeholder #}
{% set placeholder = craft.imagerx.placeholder({ width: 20, height: 12 }) %}

{# Dominant color from image #}
{% set color = craft.imagerx.getDominantColor(asset) %}

{# Hex palette #}
{% set palette = craft.imagerx.getColorPalette(asset, 5) %}
```

## Named Transforms (`config/imager-x-transforms.php`)

```php
// config/imager-x-transforms.php
return [
    'hero' => [
        'transforms' => [
            ['width' => 400],
            ['width' => 800],
            ['width' => 1200],
            ['width' => 1600],
        ],
        'defaults' => [
            'format' => 'webp',
            'quality' => 80,
        ],
        'configOverrides' => [
            'fillTransforms' => true,
        ],
    ],
    'thumbnail' => [
        'transforms' => [
            ['width' => 200, 'height' => 200, 'mode' => 'crop'],
        ],
        'defaults' => [
            'format' => 'webp',
            'quality' => 70,
        ],
    ],
];
```

## Config File

```php
// config/imager-x.php
return [
    '*' => [
        'transformer' => 'craft',
        'imagerSystemPath' => '@webroot/imager/',
        'imagerUrl' => '/imager/',
        'fillTransforms' => true,
        'fillInterval' => 200,
        'jpegQuality' => 80,
        'webpQuality' => 80,
        'avifQuality' => 60,
        'optimizeType' => 'runtime',
        'optimizers' => [
            'jpegoptim' => ['extensions' => ['jpg'], 'path' => '/usr/bin/', 'optionString' => '-s --max=80'],
            'optipng'   => ['extensions' => ['png'], 'path' => '/usr/bin/', 'optionString' => '-o2'],
        ],
        'cacheDuration' => 31536000,
    ],
    'dev' => [
        'optimizeType' => 'none',
    ],
];
```

## Console Commands

```bash
# Clear all Imager-X caches (transforms + remote cache)
ddev craft imager-x/clear

# Generate transforms for a specific named transform
ddev craft imager-x/generate hero

# Generate all named transforms
ddev craft imager-x/generate
```

## Transform Drivers

| Driver | Config key | Description |
|--------|-----------|-------------|
| Craft (local) | `'craft'` | GD/Imagick on the server. Default, no external deps |
| Imgix | `'imgix'` | URL-based SaaS transforms. Best for CDN-heavy setups |
| Cloudflare | `'cloudflare'` | Cloudflare Image Resizing. Requires Business/Enterprise plan |
| AWS Lambda | `'aws'` | Serverless transforms via AWS |

Set the driver with `'transformer' => 'imgix'` in `config/imager-x.php`. Each driver has its own config key (`imgixConfig`, `cloudflareConfig`, `awsConfig`).

## When to Use: Imager-X vs Native vs ImageOptimize

- **Native transforms** -- single resize, nothing more. No extra plugin needed.
- **ImageOptimize** -- the field owns variant config, tag builders handle output, convention-over-config approach.
- **Imager-X** -- explicit control over every transform, batch generation, named presets, effects, or a specific CDN driver (Imgix, Cloudflare, AWS).

## Multi-Site

Transforms are not site-scoped -- they operate on assets, which exist independently of sites. If using external drivers with different domains per site, configure multiple driver entries in `imgixConfig` and select per-site via `transformerConfig`.

## Pair With

- **ImageOptimize** -- can use Imager-X as its transform backend (not common, but possible)
- **Blitz** -- pre-warm pages that contain heavy image transforms to avoid queue bottlenecks on first visit
- **SEOMatic** -- use Imager-X transforms for OG/Twitter card images
