# Element API

First-party JSON API plugin by Pixel & Tonic. Define endpoints in a config file that map URL patterns to element queries with Fractal transformers. Powers headless/hybrid setups, AJAX feeds, calendar integrations, and any external data consumer that needs Craft content as JSON. 10K+ installs.

`craftcms/element-api` — Free (MIT)

## Documentation

- GitHub/README: https://github.com/craftcms/element-api/blob/4.x/README.md
- Plugin Store: https://plugins.craftcms.com/element-api

When unsure about a config option, `WebFetch` the GitHub README — it's the canonical reference.

## Common Pitfalls

- Not defining a transformer — the default transformer returns direct attribute values but **no custom field values**. Almost every real endpoint needs a custom transformer.
- Returning too much data — transformers should explicitly select fields, not dump everything. Keep payloads lean.
- Missing `one` for single-element endpoints — without `'one' => true`, the endpoint returns a paginated collection even for detail routes. Set it for `api/entries/<slug>` style endpoints.
- Using `'p'` as a URL parameter name — Craft reserves `p` for path resolution. Use any other parameter name.
- Not scoping criteria tightly — an open `craft\elements\Entry::class` without section/type criteria exposes all entries across all sections. Always filter.
- Forgetting the endpoint is cached by default — responses cache automatically and invalidate when relevant elements change. If you're hitting stale data, check whether cache invalidation is working or add explicit cache config.
- Exposing draft/revision data — Element API respects Craft's default query behavior, but misconfigured criteria can leak drafts. Don't override status/draft params unless intentional.

## Config File

All endpoints are defined in `config/element-api.php`:

```php
<?php

use craft\elements\Entry;
use craft\elements\Asset;
use craft\helpers\UrlHelper;

return [
    'defaults' => [
        'elementsPerPage' => 20,
        'pageParam' => 'pg',
        'resourceKey' => 'data',
    ],

    'endpoints' => [
        // Collection endpoint — returns paginated list
        'api/news.json' => function() {
            return [
                'elementType' => Entry::class,
                'criteria' => [
                    'section' => 'news',
                    'orderBy' => 'postDate DESC',
                ],
                'transformer' => function(Entry $entry) {
                    return [
                        'id' => $entry->id,
                        'title' => $entry->title,
                        'url' => $entry->url,
                        'date' => $entry->postDate->format('c'),
                        'summary' => $entry->summary ?? null,
                    ];
                },
            ];
        },

        // Detail endpoint — single element
        'api/news/<slug:{slug}>.json' => function(string $slug) {
            return [
                'elementType' => Entry::class,
                'one' => true,
                'criteria' => [
                    'section' => 'news',
                    'slug' => $slug,
                ],
                'transformer' => function(Entry $entry) {
                    return [
                        'id' => $entry->id,
                        'title' => $entry->title,
                        'url' => $entry->url,
                        'date' => $entry->postDate->format('c'),
                        'body' => (string) $entry->body,
                        'image' => $entry->heroImage
                            ->one()?->getUrl('newsDetail'),
                    ];
                },
            ];
        },
    ],
];
```

## Endpoint Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `elementType` | string | — | Element class (required). `Entry::class`, `Asset::class`, `Category::class`, etc. |
| `criteria` | array | `[]` | Element query params: `section`, `type`, `orderBy`, `limit`, `relatedTo`, etc. |
| `transformer` | callable/class | default | Maps element → response array. Closure or `TransformerAbstract` class. |
| `one` | bool | `false` | Return single element instead of collection. |
| `paginate` | bool | `true` | Enable pagination on collection endpoints. |
| `elementsPerPage` | int | 100 | Page size. |
| `pageParam` | string | `'page'` | Query param for pagination. |
| `resourceKey` | string | `'data'` | Key wrapping element data in response. |
| `cache` | bool/int | `true` | Cache duration in seconds, or `true` for auto-invalidation. |
| `meta` | array | `[]` | Custom metadata in response root. |
| `serializer` | object | `JsonApiSerializer` | Fractal serializer instance. |
| `callback` | string/null | `null` | JSONP callback parameter name. |

## Custom Transformer Class

For complex endpoints, use a dedicated transformer:

```php
<?php

namespace modules\transformers;

use craft\elements\Entry;
use League\Fractal\TransformerAbstract;

class NewsTransformer extends TransformerAbstract
{
    public function transform(Entry $entry): array
    {
        return [
            'id' => $entry->id,
            'title' => $entry->title,
            'slug' => $entry->slug,
            'url' => $entry->url,
            'date' => $entry->postDate->format('c'),
        ];
    }
}
```

Reference in config: `'transformer' => new \modules\transformers\NewsTransformer()`.

## Dynamic URL Parameters

URL patterns support Craft's route tokens:

```php
// Slug token
'api/entries/<slug:{slug}>.json' => function(string $slug) { /* ... */ },

// Entry ID
'api/entries/<entryId:\d+>.json' => function(int $entryId) { /* ... */ },

// Section handle
'api/<section:{handle}>.json' => function(string $section) { /* ... */ },
```

## Events

The plugin fires `EVENT_BEFORE_SEND_DATA` before sending:

```php
use craft\elementapi\controllers\DefaultController;
use craft\elementapi\events\BeforeSendDataEvent;
use yii\base\Event;

Event::on(
    DefaultController::class,
    DefaultController::EVENT_BEFORE_SEND_DATA,
    function(BeforeSendDataEvent $event) {
        // Modify $event->data before it's sent
    }
);
```

## Multi-Site

Endpoints serve the current site's content by default. To pin to a specific site:

```php
'criteria' => [
    'site' => 'en',
    'section' => 'news',
],
```

## Pair With

- **Timeloop** — expose recurring dates as JSON for external calendar apps
- **SEOMatic** — use Element API for meta endpoints, SEOMatic for rendered page SEO
- **Blitz** — cached pages + JSON API endpoints from the same Craft install
- **Scout / Typesense** — Element API for structured feeds, search plugins for full-text
