# Third-Party Integration in Craft CMS

How to install analytics, consent management, tag management, email transport, and automation webhooks in Craft CMS Twig templates.

For API reference on each tool, see `tools/integrations/`. This file covers the Craft-specific installation patterns only.

## Script Loading Order

The loading order matters. In your base layout (`_boilerplate/_layouts/base-html-layout.twig`):

1. **Consent Mode defaults** (before anything else)
2. **CMP** (UserCentrics or CookieBot)
3. **GTM** (reads consent state from CMP)
4. **Analytics** (Fathom/Plausible load independently — no CMP needed if cookieless)
5. **Vite assets** (via `craft.vite.script()`)

## Consent Mode v2 Defaults

Set before CMP and GTM load. This ensures Google tags respect consent even before the CMP initializes:

```twig
{%- block consentDefaults -%}
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('consent', 'default', {
  'analytics_storage': 'denied',
  'ad_storage': 'denied',
  'ad_user_data': 'denied',
  'ad_personalization': 'denied',
  'functionality_storage': 'denied',
  'personalization_storage': 'denied',
  'security_storage': 'granted',
  'wait_for_update': 500,
});
</script>
{%- endblock -%}
```

## CMP (UserCentrics)

```twig
{%- block cmp -%}
<script id="usercentrics-cmp"
  src="https://app.usercentrics.eu/browser-ui/latest/loader.js"
  data-settings-id="{{ craft.app.config.custom.usercentricsSid ?? '' }}"
  async>
</script>
{%- endblock -%}
```

Store the Settings ID in `config/custom.php` so it can differ per environment:

```php
// config/custom.php
return [
    'usercentricsSid' => craft\helpers\App::env('USERCENTRICS_SID'),
];
```

## CMP (CookieBot)

```twig
{%- block cmp -%}
<script id="Cookiebot"
  src="https://consent.cookiebot.com/uc.js"
  data-cbid="{{ craft.app.config.custom.cookiebotCbid ?? '' }}"
  data-blockingmode="auto"
  type="text/javascript"
  async>
</script>
{%- endblock -%}
```

### Cookie Declaration Page

Embed in a single-section template for an auto-updated cookie declaration:

```twig
{# _views/view--cookie-declaration.twig #}
<script id="CookieDeclaration"
  src="https://consent.cookiebot.com/{{ craft.app.config.custom.cookiebotCbid }}/cd.js"
  type="text/javascript"
  async>
</script>
```

## GTM (Client-Side)

```twig
{# Head — as high as possible, after CMP #}
{%- block gtmHead -%}
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','{{ craft.app.config.custom.gtmId ?? '' }}');</script>
{%- endblock -%}

{# Body — immediately after opening <body> #}
{%- block gtmBody -%}
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={{ craft.app.config.custom.gtmId ?? '' }}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
{%- endblock -%}
```

### Data Layer

Push Craft-specific data for GTM:

```twig
<script>
window.dataLayer = window.dataLayer || [];
dataLayer.push({
  'event': 'page_view',
  'page_type': '{{ entry.section.handle ?? 'static' }}',
  'content_group': '{{ entry.type.handle ?? 'default' }}',
  {% if currentUser %}
  'user_logged_in': true,
  {% endif %}
});
</script>
```

## Fathom Analytics

Cookieless — no CMP needed. Can coexist with GA4:

```twig
{%- block analytics -%}
<script src="https://cdn.usefathom.com/script.js"
  data-site="{{ craft.app.config.custom.fathomSiteId ?? '' }}"
  {% if craft.app.config.general.devMode %}data-excluded-domains="localhost,{{ craft.app.request.hostName }}"{% endif %}
  defer>
</script>
{%- endblock -%}
```

The `devMode` check automatically excludes tracking in development.

## Plausible Analytics

Also cookieless — no CMP needed:

```twig
{%- block analytics -%}
<script defer
  data-domain="{{ craft.app.config.custom.plausibleDomain ?? craft.app.request.hostName }}"
  src="https://plausible.io/js/script.js">
</script>
{%- endblock -%}
```

## AWS SES (via putyourlightson/craft-amazon-ses)

The Craft Amazon SES plugin provides a mail transport adapter. No Twig needed — configure in the CP under Settings → Email or via `config/app.php`:

```php
// config/app.php
return [
    'components' => [
        'mailer' => static function() {
            $settings = craft\helpers\App::mailSettings();
            $settings->transportType = putyourlightson\amazonses\mail\SesAdapter::class;
            $settings->transportSettings = [
                'region' => craft\helpers\App::env('AWS_REGION'),
                'accessKeyId' => craft\helpers\App::env('AWS_ACCESS_KEY_ID'),
                'secretAccessKey' => craft\helpers\App::env('AWS_SECRET_ACCESS_KEY'),
            ];
            return Craft::createObject($settings->mailerSettings());
        },
    ],
];
```

## n8n Webhooks (from Craft Events)

Trigger n8n workflows from Craft CMS events using a module:

```php
use craft\elements\Entry;
use yii\base\Event;
use yii\base\ModelEvent;

Event::on(Entry::class, Entry::EVENT_AFTER_SAVE, function(ModelEvent $event) {
    $entry = $event->sender;

    Craft::createGuzzleClient()->post(
        craft\helpers\App::env('N8N_WEBHOOK_URL') . '/entry-saved',
        [
            'json' => [
                'entry_id' => $entry->id,
                'title' => $entry->title,
                'section' => $entry->section->handle,
                'status' => $entry->getStatus(),
            ],
        ]
    );
});
```

## Blitz Compatibility Notes

All client-side scripts (CMP, GTM, Fathom, Plausible) work with Blitz static caching — they load in the browser and don't interact with the PHP request cycle.

For user-specific content within Blitz-cached pages, use `{% dynamicInclude %}`:

```twig
{% dynamicInclude '_includes/user-data-layer' with {
  userId: currentUser.id ?? null
} %}
```

## Full Head Template Example

```twig
{# _boilerplate/_layouts/base-html-layout.twig #}
<!DOCTYPE html>
<html lang="{{ craft.app.language }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    {# 1. Consent defaults #}
    {%- block consentDefaults -%}{%- endblock -%}

    {# 2. CMP (choose one) #}
    {%- block cmp -%}{%- endblock -%}

    {# 3. GTM #}
    {%- block gtmHead -%}{%- endblock -%}

    {# 4. Analytics (cookieless — no CMP dependency) #}
    {%- block analytics -%}{%- endblock -%}

    {# 5. SEO meta (SEOMatic) #}
    {% hook 'seomaticRender' %}

    {# 6. Vite assets #}
    {%- block headLinks -%}
        {{ craft.vite.script('src/js/app.ts', false) }}
    {%- endblock -%}
</head>
<body>
    {%- block gtmBody -%}{%- endblock -%}

    {%- block content -%}{%- endblock -%}

    {%- block bodyJs -%}
        {%- block pageJs -%}{%- endblock -%}
    {%- endblock -%}
</body>
</html>
```
