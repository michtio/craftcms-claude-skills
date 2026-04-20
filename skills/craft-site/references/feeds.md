# Feeds, RSS & XML Output

How to build RSS, Atom, JSON Feed, and XML sitemap templates in Craft CMS 5. Pure Twig — no plugins required for basic feeds. For SEOmatic-managed sitemaps, see `plugins/seomatic.md`. For JSON API endpoints, see `plugins/element-api.md`.

## Documentation

- Twig template tags: https://craftcms.com/docs/5.x/reference/twig/tags.html
- Routing: https://craftcms.com/docs/5.x/system/routing.html

## Common Pitfalls

- Forgetting `{% header %}` for content type — browsers will render XML as HTML without the correct `Content-Type` header.
- Using `|date` instead of `|rss` or `|atom` — RSS and Atom have specific date format requirements. The dedicated filters handle them correctly.
- Not wrapping HTML content in `<![CDATA[...]]>` — HTML entities in RSS `<description>` will break XML parsers.
- Including draft or disabled entries in feeds — always use the default query (which excludes them) or explicitly filter with `.status('live')`.

## Contents

- [RSS 2.0 Feed](#rss-20-feed)
- [Atom Feed](#atom-feed)
- [JSON Feed](#json-feed)
- [XML Sitemap](#xml-sitemap)
- [Custom Routes](#custom-routes)
- [Date Filters](#date-filters)

## RSS 2.0 Feed

```twig
{# templates/_feeds/rss.twig #}
{% header "Content-Type: application/rss+xml; charset=utf-8" %}
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>{{ siteName }}</title>
        <link>{{ siteUrl }}</link>
        <description>{{ siteName }} RSS Feed</description>
        <language>{{ currentSite.language }}</language>
        <atom:link href="{{ url('feed/rss') }}" rel="self" type="application/rss+xml" />
        <lastBuildDate>{{ now | rss }}</lastBuildDate>

        {% set entries = craft.entries()
            .section('blog')
            .orderBy('postDate DESC')
            .limit(20)
            .all() %}

        {% for entry in entries %}
            <item>
                <title>{{ entry.title | e('html') }}</title>
                <link>{{ entry.url }}</link>
                <guid isPermaLink="true">{{ entry.url }}</guid>
                <pubDate>{{ entry.postDate | rss }}</pubDate>

                {% if entry.summary is defined and entry.summary %}
                    <description><![CDATA[{{ entry.summary }}]]></description>
                {% endif %}

                {% if entry.featuredImage is defined %}
                    {% set image = entry.featuredImage.one() %}
                    {% if image %}
                        <enclosure url="{{ image.url }}"
                                   length="{{ image.size }}"
                                   type="{{ image.mimeType }}" />
                    {% endif %}
                {% endif %}

                {% if entry.categories is defined %}
                    {% for category in entry.categories.all() %}
                        <category>{{ category.title | e('html') }}</category>
                    {% endfor %}
                {% endif %}
            </item>
        {% endfor %}
    </channel>
</rss>
```

### Adding to `<head>`

```twig
{# In your layout #}
<link rel="alternate"
      type="application/rss+xml"
      title="{{ siteName }} RSS"
      href="{{ url('feed/rss') }}">
```

## Atom Feed

```twig
{# templates/_feeds/atom.twig #}
{% header "Content-Type: application/atom+xml; charset=utf-8" %}
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>{{ siteName }}</title>
    <link href="{{ siteUrl }}" />
    <link href="{{ url('feed/atom') }}" rel="self" />
    <id>{{ siteUrl }}</id>
    <updated>{{ now | atom }}</updated>

    {% set entries = craft.entries()
        .section('blog')
        .orderBy('postDate DESC')
        .limit(20)
        .all() %}

    {% for entry in entries %}
        <entry>
            <title>{{ entry.title | e('html') }}</title>
            <link href="{{ entry.url }}" />
            <id>{{ entry.url }}</id>
            <published>{{ entry.postDate | atom }}</published>
            <updated>{{ entry.dateUpdated | atom }}</updated>

            {% if entry.summary is defined and entry.summary %}
                <summary type="html"><![CDATA[{{ entry.summary }}]]></summary>
            {% endif %}

            {% if entry.author %}
                <author>
                    <name>{{ entry.author.fullName | e('html') }}</name>
                </author>
            {% endif %}
        </entry>
    {% endfor %}
</feed>
```

## JSON Feed

```twig
{# templates/_feeds/feed.json.twig #}
{% header "Content-Type: application/feed+json; charset=utf-8" %}
{% set entries = craft.entries()
    .section('blog')
    .orderBy('postDate DESC')
    .limit(20)
    .all() %}

{{ {
    version: 'https://jsonfeed.org/version/1.1',
    title: siteName,
    home_page_url: siteUrl,
    feed_url: url('feed.json'),
    language: currentSite.language,
    items: entries | map(entry => {
        id: entry.url,
        url: entry.url,
        title: entry.title,
        date_published: entry.postDate | atom,
        date_modified: entry.dateUpdated | atom,
        summary: entry.summary is defined ? entry.summary | striptags : null,
        authors: entry.author ? [{ name: entry.author.fullName }] : [],
    }),
{# |raw is safe here — json_encode output is not user-controlled HTML #}
} | json_encode(constant('JSON_PRETTY_PRINT') b-or constant('JSON_UNESCAPED_SLASHES')) | raw }}
```

## XML Sitemap

For SEOmatic-managed sitemaps (recommended for most sites), see `plugins/seomatic.md`. For a custom Twig-based sitemap:

```twig
{# templates/sitemap.xml.twig #}
{% header "Content-Type: application/xml; charset=utf-8" %}
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {# Homepage #}
    <url>
        <loc>{{ siteUrl }}</loc>
        <lastmod>{{ now | atom }}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>

    {# All sections with URLs #}
    {% for section in craft.app.entries.allSections() %}
        {% if section.hasUrls %}
            {% set entries = craft.entries()
                .section(section.handle)
                .orderBy('dateUpdated DESC')
                .all() %}

            {% for entry in entries %}
                <url>
                    <loc>{{ entry.url }}</loc>
                    <lastmod>{{ entry.dateUpdated | atom }}</lastmod>
                </url>
            {% endfor %}
        {% endif %}
    {% endfor %}
</urlset>
```

### Sitemap index (for large sites)

```twig
{# templates/sitemap-index.xml.twig #}
{% header "Content-Type: application/xml; charset=utf-8" %}
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {% for section in craft.app.entries.allSections() %}
        {% if section.hasUrls %}
            {% set latest = craft.entries().section(section.handle).orderBy('dateUpdated DESC').one() %}
            {% if latest %}
                <sitemap>
                    <loc>{{ url("sitemap-#{section.handle}.xml") }}</loc>
                    <lastmod>{{ latest.dateUpdated | atom }}</lastmod>
                </sitemap>
            {% endif %}
        {% endif %}
    {% endfor %}
</sitemapindex>
```

## Custom Routes

In `config/routes.php`:

```php
return [
    'feed/rss' => ['template' => '_feeds/rss'],
    'feed/atom' => ['template' => '_feeds/atom'],
    'feed.json' => ['template' => '_feeds/feed.json'],
    'sitemap.xml' => ['template' => 'sitemap.xml'],
    'sitemap-index.xml' => ['template' => 'sitemap-index.xml'],

    // Dynamic section feed
    'feed/<section:{handle}>' => ['template' => '_feeds/rss'],
];
```

Named parameters (like `<section:{handle}>`) are available as template variables.

### Multi-site feed routes

For multi-site, routes are site-specific in the CP (Settings > Routes) or use site-prefixed patterns:

```php
return [
    'en' => [
        'feed/rss' => ['template' => '_feeds/rss'],
    ],
    'nl' => [
        'feed/rss' => ['template' => '_feeds/rss'],
    ],
];
```

## Date Filters

| Filter | Format | Example Output |
|--------|--------|---------------|
| `\|rss` | RFC 2822 | `Wed, 31 May 2023 12:23:09 -0700` |
| `\|atom` | ISO 8601 | `2023-05-31T12:23:09-07:00` |

Both filters accept an optional timezone parameter:

```twig
{{ entry.postDate | rss('UTC') }}
{{ entry.postDate | atom('America/New_York') }}
{{ entry.postDate | rss(false) }}  {# Preserve the date's existing timezone #}
```

Use `|atom` for JSON Feed dates, Atom feeds, and sitemaps. Use `|rss` for RSS 2.0 feeds.
