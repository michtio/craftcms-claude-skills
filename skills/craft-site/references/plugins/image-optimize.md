# ImageOptimize

Automatic responsive image transform generation by nystudio107. Adds an OptimizedImages field type that pre-generates responsive variants and provides Twig helpers for `<img>` and `<picture>` output. Supports native Craft transforms, imgix, Thumbor, Sharp JS, and Cloudinary as transform backends.

`nystudio107/craft-imageoptimize` — $59

## Documentation

- Overview: https://nystudio107.com/docs/image-optimize/
- Configuration: https://nystudio107.com/docs/image-optimize/configuring.html
- Using (Twig): https://nystudio107.com/docs/image-optimize/using.html
- Advanced: https://nystudio107.com/docs/image-optimize/advanced.html

When unsure about an ImageOptimize feature, `web_fetch` the relevant docs page.

## Common Pitfalls

- Adding the OptimizedImages field to a Section field layout instead of the Asset Volume field layout — the field must be on the Asset Volume, not the Section. It generates variants for the asset itself.
- Forgetting to call `.render()` on tag builders — `.imgTag()` and `.pictureTag()` return builder objects, not HTML strings. Chain `.render()` at the end.
- Not running `ddev craft image-optimize/optimize/create` after adding new variants — existing assets don't auto-regenerate unless you resave them or run the console command.
- Using ImageOptimize on Craft Cloud — Craft Cloud handles transforms via Cloudflare Images at the edge. ImageOptimize is for self-hosted or imgix/Thumbor setups. Don't use both.
- Missing `--force` flag when adding WebP variants after the fact — existing transforms won't be recreated unless forced.
- Expecting real-time transform generation — transforms are pre-generated as queue jobs on asset save, not at request time. Large uploads may take a moment.

## Setup

1. Install the plugin
2. Configure the transform method in Settings (Craft, imgix, Thumbor, or Sharp JS)
3. Create an OptimizedImages field (one per srcset you need)
4. Add the field to the Asset Volume field layout
5. Define image variants (widths, aspect ratios, formats)
6. Resave assets: `ddev craft image-optimize/optimize/create`

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

## Console Commands

```bash
# Create all optimized image variants
ddev craft image-optimize/optimize/create

# Create variants for a specific field only
ddev craft image-optimize/optimize/create --field=heroImage

# Force recreation (required when adding new formats like WebP)
ddev craft image-optimize/optimize/create --force

# Clear all generated variants
ddev craft image-optimize/optimize/clear
```

## Config File

```php
// config/image-optimize.php
return [
    '*' => [
        // Automatically resave image variants when field/volume settings change
        'automaticallyResaveImageVariants' => true,

        // Generate placeholders and color palettes
        'createColorPalette' => true,
        'createPlaceholderSilhouettes' => true,

        // Sharpening threshold (% size reduction before auto-sharpening applies)
        'autoSharpenScaledImages' => true,
        'sharpenScaledImagePercentage' => 50,

        // Lower quality for smaller file sizes (0-100)
        'lowerQualityRetinaImageVariants' => true,
    ],
];
```

## Transform Methods

| Method | Package | Description |
|--------|---------|-------------|
| Craft | Built-in | Native Craft transforms (GD/Imagick) |
| imgix | Built-in | imgix URL-based transforms |
| Thumbor | Built-in | Open-source image service |
| Sharp JS | Built-in | AWS Lambda serverless transforms |

Configure in CP → Settings → ImageOptimize → Transform Method.

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
