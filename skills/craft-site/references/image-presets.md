# Image Presets Reference

> One image atom, many presets. Config-driven responsive images.

## Documentation

- Craft image transforms: https://craftcms.com/docs/5.x/development/image-transforms.html
- ImageOptimize plugin: https://nystudio107.com/docs/image-optimize/
- Responsive images (MDN): https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images

## Common Pitfalls

- Hardcoded dimensions in templates — never write `width: 800` directly in a view. Always go through presets.
- Missing alt text fallback chain — always: explicit alt → asset alt field → asset title → empty string.
- `loading="eager"` everywhere — only the first visible image (above-fold hero) should be eager. Everything else is lazy.
- Missing `sizes` attribute — without it, the browser downloads the largest srcset image regardless of viewport.
- Provider lock-in — don't call ImageOptimize API directly in views. The image atom abstracts the provider.
- Multiple image variant files — use one atom with presets, not `image--hero.twig`, `image--teaser.twig`, etc.

## The Single Image Atom

Instead of multiple image variant files, one universal atom with a preset parameter.

### Props File

```twig
{# _atoms/images/_image--props.twig #}

{# Preset definitions — widths, sizes, loading strategy, aspect ratio #}
{%- set presets = {
    hero: {
        widths: [640, 960, 1280, 1920, 2560],
        sizes: '100vw',
        loading: 'eager',
        ratio: null,
    },
    teaser: {
        widths: [300, 450, 600, 900],
        sizes: '(min-width: 1024px) 33vw, 100vw',
        loading: 'lazy',
        ratio: 'aspect-[16/9]',
    },
    content: {
        widths: [400, 600, 900, 1200],
        sizes: '(min-width: 1024px) 50vw, 100vw',
        loading: 'lazy',
        ratio: null,
    },
    profile: {
        widths: [150, 300, 450],
        sizes: '150px',
        loading: 'lazy',
        ratio: 'aspect-square',
    },
    branding: {
        widths: [200, 400],
        sizes: '200px',
        loading: 'lazy',
        ratio: null,
    },
    gallery: {
        widths: [400, 600, 900, 1200, 1800],
        sizes: '(min-width: 1024px) 50vw, 100vw',
        loading: 'lazy',
        ratio: null,
    },
} -%}

{%- set config = presets[preset ?? 'content'] ?? presets.content -%}

{%- set props = collect({
    image: image ?? null,
    alt: alt ?? null,
    config: config,
    ratio: ratio ?? config.ratio ?? null,
    loading: config.loading,
    utilities: utilities ?? null,
}) -%}

{%- block image -%}{%- endblock -%}
```

### Variant File

```twig
{# _atoms/images/image--responsive.twig #}
{%- extends '_atoms/images/_image--props' -%}

{%- block image -%}

    {%- set asset = props.get('image') -%}

    {%- if asset -%}
        {%- set alttext = props.get('alt') ?? asset.alt ?? asset.title -%}

        {%- set classes = collect({
            display: 'block w-full h-auto',
            ratio: props.get('ratio'),
            fit: props.get('ratio') ? 'object-cover' : null,
            utilities: props.get('utilities'),
        }) -%}

        {# With ImageOptimize plugin #}
        {%- if asset.optimizedImages is defined -%}

            <picture>
                {%- if asset.optimizedImages.srcsetWebp() -%}
                    {{ tag('source', {
                        type: 'image/webp',
                        srcset: asset.optimizedImages.srcsetWebp(),
                        sizes: props.get('config').sizes,
                    }) }}
                {%- endif -%}

                {{ tag('img', {
                    class: classes.implode(' '),
                    src: asset.optimizedImages.src(),
                    srcset: asset.optimizedImages.srcset(),
                    sizes: props.get('config').sizes,
                    alt: alttext,
                    loading: props.get('loading'),
                    width: asset.width,
                    height: asset.height,
                    style: asset.optimizedImages.placeholderBox() ? {
                        'background-image': "url('" ~ asset.optimizedImages.placeholderImage() ~ "')",
                        'background-size': 'cover',
                    } : false,
                }) }}
            </picture>

        {# With Craft Cloud / native transforms #}
        {%- else -%}
            <picture>
                {%- for width in props.get('config').widths -%}
                    {%- set transform = { width: width, format: 'webp' } -%}
                    {{ tag('source', {
                        type: 'image/webp',
                        srcset: asset.getUrl(transform),
                        media: loop.last ? false : '(max-width: ' ~ width ~ 'px)',
                    }) }}
                {%- endfor -%}

                {{ tag('img', {
                    class: classes.implode(' '),
                    src: asset.getUrl({ width: props.get('config').widths|last }),
                    alt: alttext,
                    loading: props.get('loading'),
                    width: asset.width,
                    height: asset.height,
                }) }}
            </picture>
        {%- endif -%}
    {%- endif -%}

{%- endblock -%}
```

## Preset Definitions

| Preset | Use Case | Widths | Sizes | Loading |
|--------|----------|--------|-------|---------|
| `hero` | Full-width hero images | 640–2560 | `100vw` | `eager` |
| `teaser` | Card thumbnails, grid items | 300–900 | `33vw` at desktop | `lazy` |
| `content` | Inline content images | 400–1200 | `50vw` at desktop | `lazy` |
| `profile` | Author photos, avatars | 150–450 | `150px` | `lazy` |
| `branding` | Logos, partner logos | 200–400 | `200px` | `lazy` |
| `gallery` | Gallery/lightbox images | 400–1800 | `50vw` at desktop | `lazy` |

### Preset Naming

Lowercase context names: `hero`, `teaser`, `content`, `profile`, `branding`, `gallery`.

### Adding Project-Specific Presets

Add to the `presets` hash in `_image--props.twig`:

```twig
{%- set presets = presets|merge({
    floorplan: {
        widths: [600, 900, 1200],
        sizes: '(min-width: 768px) 50vw, 100vw',
        loading: 'lazy',
        ratio: null,
    },
}) -%}
```

## Calling the Image Atom

```twig
{# Standard usage #}
{%- include '_atoms/images/image--responsive' with {
    image: entry.heroImage.eagerly().one(),
    preset: 'hero',
} only -%}

{# With alt text override #}
{%- include '_atoms/images/image--responsive' with {
    image: entry.teamPhoto.one(),
    preset: 'profile',
    alt: entry.memberName,
    utilities: 'rounded-full',
} only -%}

{# With aspect ratio override #}
{%- include '_atoms/images/image--responsive' with {
    image: entry.thumbnail.one(),
    preset: 'teaser',
    ratio: 'aspect-[4/3]',
} only -%}
```

## Hosting / Transform Strategies

| Strategy | When to use | Notes |
|----------|-------------|-------|
| **ImageOptimize plugin** | VPS / Servd hosting | Full srcset/webp generation at upload. Best quality control. Not compatible with Craft Cloud. |
| **Craft Cloud transforms** | Craft Cloud hosting | Native Craft transforms. Craft Cloud intercepts and serves via Cloudflare Images — no special template syntax needed. |
| **Small Pics / Cloudflare Images** | External transform service | URL-based. Best for CDN-first architectures. |

The image atom handles both paths. It checks for the `optimizedImages` field
handle (ImageOptimize plugin) and falls back to native Craft transforms via
`asset.getUrl()`. On Craft Cloud, these native transforms are automatically
served through Cloudflare Images — the template code is identical either way.

## A11y Requirements

- `alt` is always required. Fallback chain: explicit `alt` prop → asset `alt` field → asset `title`.
- Decorative images: pass `alt: ''` explicitly. Never omit.
- `loading="eager"` only on hero/above-fold images. Everything else is `lazy`.
- `width` and `height` always rendered to prevent CLS.

## DS Module Vision (Future)

With the `craft.ds` module, image rendering collapses to:

```twig
{{ craft.ds.image(entry.heroImage.one(), 'hero') }}
```

The PHP service resolves the preset, detects the hosting environment, generates the `<picture>` element, and handles all transform logic server-side. The vanilla Twig approach documented here is the foundation that the module will formalize.