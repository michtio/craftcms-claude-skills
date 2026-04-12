# Embedded Assets

oEmbed plugin by Spicy Web. Lets editors paste URLs (YouTube, Vimeo, Instagram, etc.) into Craft's asset manager and treat them as first-class assets stored as JSON files. Pulls images, embed codes, and metadata automatically. Supports GraphQL. Used in 4/6 projects.

`spicyweb/craft-embedded-assets` — Free (MIT)

## Documentation

- GitHub: https://github.com/spicywebau/craft-embedded-assets
- Templating: https://github.com/spicywebau/craft-embedded-assets/blob/main/docs/templating.md
- GraphQL: https://github.com/spicywebau/craft-embedded-assets/blob/main/docs/graphql.md
- Configuration: https://github.com/spicywebau/craft-embedded-assets/blob/main/docs/configuration.md

When unsure, `WebFetch` the relevant docs page.

## Common Pitfalls

- Forgetting that embedded assets are JSON files — they have `.json` extension and `kind === 'json'`. Asset fields must allow JSON file types, or have no file type restriction.
- Using `asset.url` directly — for an embedded asset, `asset.url` returns the JSON file path, not the embed URL. Always use `craft.embeddedAssets.get(asset)` to get the model.
- Not null-checking — `craft.embeddedAssets.get()` returns `null` if the asset isn't an embedded asset. Always guard with `{% if embed %}`.
- Instagram/social media breakage — social platforms frequently change their oEmbed APIs. Keep the plugin updated.
- Missing whitelist entries — the plugin whitelists allowed domains. If an embed URL doesn't work, check if the domain is in the whitelist config.
- Using deprecated properties — v4+ deprecated `$images` (use `$image`), `$providerIcons` (use `$providerIcon`), `$tags` (use `$keywords`).

## Twig API

### Getting an Embedded Asset

```twig
{% set asset = entry.videoField.one() %}
{% set embed = craft.embeddedAssets.get(asset) %}

{% if embed %}
    <h3>{{ embed.title }}</h3>
    <p>{{ embed.providerName }}</p>

    {# Safe HTML embed code (sanitized) #}
    {{ embed.safeHtml|raw }}
{% endif %}
```

### Model Properties

| Property | Type | Description |
|----------|------|-------------|
| `title` | `string` | Embed title |
| `description` | `string` | Embed description |
| `url` | `string` | Original URL |
| `type` | `string` | `video`, `photo`, `rich`, `link` |
| `image` | `string` | Primary image URL |
| `code` | `string` | Raw embed HTML |
| `providerName` | `string` | Provider name (YouTube, Vimeo, etc.) |
| `providerUrl` | `string` | Provider URL |
| `providerIcon` | `string` | Provider favicon URL |
| `authorName` | `string` | Content author |
| `authorUrl` | `string` | Author URL |
| `width` | `int` | Embed width |
| `height` | `int` | Embed height |
| `keywords` | `array` | Keywords/tags |

### Model Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `getIsSafe()` | `bool` | Whether embed code URLs are from whitelisted domains |
| `getIframeSrc(params?)` | `string\|null` | Iframe src URL with optional extra params |
| `getIframeCode(params?, attributes?, removeAttributes?)` | `string\|null` | Full iframe HTML with modifications |
| `getVideoId()` | `string\|null` | Video ID for supported providers |
| `getVideoUrl(params?)` | `string\|null` | Video URL with optional params |

### Iframe Customization

```twig
{% set embed = craft.embeddedAssets.get(asset) %}

{# Get iframe src with extra params #}
{{ embed.getIframeSrc(['autoplay=1', 'controls=0']) }}

{# Get full iframe code with params, added attributes, and removed attributes #}
{{ embed.getIframeCode(
    ['autoplay=1', 'playsinline=1'],
    ['loading=lazy'],
    ['frameborder']
)|raw }}
```

### Alternative: From Raw Data

```twig
{# Build from property name/value pairs instead of an asset #}
{% set embed = craft.embeddedAssets.fromData({
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    title: 'Video Title',
    type: 'video',
}) %}
```

## GraphQL

```graphql
{
  entries(section: "videos") {
    ... on videos_default_Entry {
      videoField {
        embeddedAsset {
          title
          url
          type
          providerName
          image
          isSafe
          iframeSrc(params: ["autoplay=1"])
        }
      }
    }
  }
}
```

Returns `null` for assets that aren't embedded.

## Configuration

Settings are configurable via the CP (Settings → Embedded Assets) or config file:

```php
// config/embedded-assets.php
return [
    // Whitelisted domains (URLs must match one of these)
    'whitelist' => [
        'youtube.com',
        'vimeo.com',
        'soundcloud.com',
        // ... add custom domains
    ],

    // Show thumbnails in CP asset indexes
    'showThumbnailsInCp' => true,

    // Min/max dimensions for embedded image thumbnails
    'minImageSize' => 16,
    'maxImageSize' => 2000,
];
```

## Pair With

- **CKEditor** — embed media in rich text fields, use Embedded Assets for standalone media assets
- **ImageOptimize** — regular images use ImageOptimize transforms, embedded assets use their own thumbnails
