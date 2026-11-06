# Image Presets Reference

> One image atom, many presets. Config-driven responsive images.

## Documentation

- Craft image transforms: https://craftcms.com/docs/5.x/development/image-transforms.html
- `generateTransformsBeforePageLoad`: https://craftcms.com/docs/5.x/reference/config/general.html#generatetransformsbeforepageload
- `runQueueAutomatically`: https://craftcms.com/docs/5.x/reference/config/general.html#runqueueautomatically
- `{% cache %}` and temporary transform URLs: https://craftcms.com/docs/5.x/reference/twig/tags.html#cache
- ImageOptimize plugin: https://nystudio107.com/docs/image-optimize/
- Responsive images (MDN): https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images

The transform docs page does not describe when a transform is generated. The timing below comes from the `craftcms/cms` 5.11.5.1 source:

- `ImageTransformer::getTransformUrl()`: https://github.com/craftcms/cms/blob/5.11.5.1/src/imagetransforms/ImageTransformer.php
- `AssetsController::actionGenerateTransform()`: https://github.com/craftcms/cms/blob/5.11.5.1/src/controllers/AssetsController.php
- `GenerateImageTransform` job: https://github.com/craftcms/cms/blob/5.11.5.1/src/queue/jobs/GenerateImageTransform.php
- `Queue::push()` / `handleResponse()`: https://github.com/craftcms/cms/blob/5.11.5.1/src/queue/Queue.php

## Common Pitfalls

- Hardcoded dimensions in templates — never write `width: 800` directly in a view. Always go through presets.
- Missing alt text fallback chain — always: explicit alt → asset alt field → asset title → empty string.
- `loading="eager"` everywhere — only the first visible image (above-fold hero) should be eager. Everything else is lazy.
- Missing `sizes` attribute — without it, the browser downloads the largest srcset image regardless of viewport.
- Provider lock-in — don't call ImageOptimize API directly in views. The image atom abstracts the provider.
- Multiple image variant files — use one atom with presets, not `image--hero.twig`, `image--teaser.twig`, etc.
- Turning on `generateTransformsBeforePageLoad` to "fix" `generate-transform` URLs — it moves every missing transform (and, with ImageOptimize on the Craft transform method, every optimizer and WebP run) into the page request. A preset with 5 widths plus a WebP `<source>` is 10 transforms per image. Leave it `false` on the front end; see [Transform Generation Timing](#transform-generation-timing).
- Treating `generate-transform` URLs in the HTML as a bug — they are Craft's default for transforms that do not exist yet, and they resolve to the real file on the next request.
- A strict CSP with `runQueueAutomatically` on — a page that queues a transform job gets an inline `<script>` with no nonce injected before `</body>`. The CSP blocks it and the queue is not kicked from that page.

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
            {%- set webpSrcset = props.get('config').widths|map(w =>
                asset.getUrl({ width: w, format: 'webp' }) ~ ' ' ~ w ~ 'w'
            )|join(', ') -%}
            {%- set srcset = props.get('config').widths|map(w =>
                asset.getUrl({ width: w }) ~ ' ' ~ w ~ 'w'
            )|join(', ') -%}

            <picture>
                {{ tag('source', {
                    type: 'image/webp',
                    srcset: webpSrcset,
                    sizes: props.get('config').sizes,
                }) }}

                {{ tag('img', {
                    class: classes.implode(' '),
                    src: asset.getUrl({ width: props.get('config').widths|last }),
                    srcset: srcset,
                    sizes: props.get('config').sizes,
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
| **Craft Cloud transforms** | Craft Cloud hosting | Native Craft transforms. Craft Cloud intercepts and serves via Cloudflare Images — no special template syntax needed. See the `craft-cloud` skill's `assets-and-transforms.md` for the edge transform limits (70MB, 100MP, 12,000px max). |
| **Small Pics / Cloudflare Images** | External transform service | URL-based. Best for CDN-first architectures. |

The image atom handles both paths. It checks for the `optimizedImages` field
handle (ImageOptimize plugin) and falls back to native Craft transforms via
`asset.getUrl()`. On Craft Cloud, these native transforms are automatically
served through Cloudflare Images — the template code is identical either way.

## Transform Generation Timing

Applies to native Craft transforms on self-hosted sites (Forge, VPS, shared hosting, fortrabbit, Servd's local transforms). On Craft Cloud the edge generates transforms, so none of this runs on your server.

`generateTransformsBeforePageLoad`: default `false`. The docs say only "Whether image transforms should be generated before page load." What each value does, from `ImageTransformer::getTransformUrl()`:

| | `false` (default) | `true` |
|---|---|---|
| Transform already exists | Real file URL | Real file URL |
| Transform missing, page request | Returns a temporary URL `{actionTrigger}/assets/generate-transform?transformId=N` (default trigger `actions`). Also pushes a `GenerateImageTransform` queue job "in case the temp URL never gets requested" (priority 2048), and sets no-cache headers on the page response. | Generates the file inline before the page renders. If another request is generating the same transform, it polls once a second for up to 30 seconds. |
| Who pays for generation | The first browser request for that image (`AssetsController::actionGenerateTransform()` generates it, then redirects to the file), or the queue job, whichever runs first | The page request |
| First visit to a page with N missing transforms | Page renders quickly. N separate image requests, each running PHP. | Page waits for all N transforms. On a small shared host, a gallery or listing page can hit `max_execution_time`. |

**`false` is the right default for the front end.** Keep it unless something consumes the HTML outside a browser and cannot follow a redirect. Craft already forces it on for those cases: GraphQL responses (`GraphqlController`) and outgoing email (`Mailer`) both switch it on for the duration of the request.

Side effects of `false` to know about:

- **`{% cache %}` will not store a block with a temporary URL in it.** The docs: the tag "holds off caching the template until the next request so those temporary image URLs aren't cached." A cached block with new images renders uncached until its transforms exist. See `template-caching.md`.
- **The page response carries no-cache headers** while any transform on it is missing. Blitz, a CDN or a reverse proxy that honours `Cache-Control` will not store that response. The next request after generation is cacheable.
- **Every missing transform also queues a job.** With `runQueueAutomatically` on (the default), a site request that pushed a job gets an inline script appended before `</body>` that XHRs `actions/queue/run` (`Queue::handleResponse()`). The queue then runs inside a web PHP worker. That script has no nonce, so under a strict CSP it is blocked; the jobs wait for the next CP visit or a CLI runner. See the `craft-plugins` skill's `image-optimize.md`, "Queue Runner", for the cron alternative.

**With ImageOptimize installed on the Craft transform method,** every transform Craft generates also runs ImageOptimize's optimizers and WebP variant creator in the same process. That happens in the page request (`true`), the image request or queue job (`false`), or the queue job that resaves an OptimizedImages field. ImageOptimize also has its own setting with the same name, `generateTransformsBeforePageLoad` (default `true`), which forces Craft's setting on just for the URLs it builds. See the `craft-plugins` skill's `image-optimize.md`, "Request-Time Cost".

**Pre-generating instead of turning it on:** if you want no generate URLs on launch day, create the transforms ahead of time. For OptimizedImages fields, run `ddev craft image-optimize/optimize/create`. For transforms requested from templates, Craft core has no "generate all transforms" console command. Request every page once: a crawler, Blitz's cache warmer, or Cache Igniter. With a CLI queue runner in place, the queued `GenerateImageTransform` jobs finish the rest even if the image URLs are never requested.

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