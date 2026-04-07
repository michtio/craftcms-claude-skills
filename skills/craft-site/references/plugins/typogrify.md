# Typogrify

Smart typography Twig filters by nystudio107. Prevents widows, fixes quotes, applies hanging punctuation, and handles typographic best practices automatically. Used on every project.

`nystudio107/craft-typogrify` — Free

## Documentation

- GitHub: https://github.com/nystudio107/craft-typogrify
- Plugin Store: https://plugins.craftcms.com/typogrify

## Common Pitfalls

- Applying `|typogrify` to HTML that contains inline scripts or JSON — it can mangle non-prose content. Only use on text/HTML content blocks.
- Using `|typogrify` inside `{% cache %}` tags that also contain SEOMatic variables — the cache conflict is with SEOMatic, not Typogrify, but the combination trips people up.
- Double-encoding entities — if content already has `&amp;` entities, Typogrify may double-process them. Use `|raw` before `|typogrify` if you're getting entity issues.
- Not using `|widont` on headings — this is the single most impactful filter for visual polish. Prevents orphaned single words on the last line.

## Twig Filters

### `|typogrify` (All-in-One)

Applies the full suite of typographic improvements:

```twig
{{ entry.body|typogrify }}
```

Includes: smart quotes, ellipses, dashes, widow prevention, ordinal suffixes, math symbols, and more.

### Individual Filters

```twig
{{ entry.title|widont }}              {# Prevents widows — adds &nbsp; before last word #}
{{ entry.body|smartypants }}          {# Smart quotes and dashes only #}
{{ entry.title|typogrifyFeed }}       {# Safe for RSS feeds (no HTML entities) #}
{{ text|truncate(160) }}              {# Truncate to character count, word-boundary aware #}
{{ text|truncateOnWord(160) }}        {# Same — truncates at word boundary #}
{{ richText|humanFileSize }}          {# Formats bytes as "1.2 MB" #}
{{ number|humanDuration }}            {# Formats seconds as "2 hours, 30 minutes" #}
{{ text|wordCount }}                  {# Returns word count #}
```

### Common Usage Patterns

```twig
{# Headings — always prevent widows #}
<h1>{{ entry.title|widont }}</h1>

{# Rich text — full typography treatment #}
<div class="prose">
    {{ entry.body|typogrify }}
</div>

{# SEO descriptions — truncate cleanly #}
<meta name="description" content="{{ entry.summary|truncateOnWord(160) }}">

{# Card excerpts #}
<p>{{ entry.body|striptags|truncateOnWord(120) }}</p>
```

## What `|typogrify` Does

- **Smart quotes** — straight `"` and `'` → curly `"` `"` `'` `'`
- **Dashes** — `--` → en-dash, `---` → em-dash
- **Ellipses** — `...` → `…`
- **Widow prevention** — `&nbsp;` before last word in block elements
- **Ordinal suffixes** — `1st` → `1<sup>st</sup>`
- **Math symbols** — `(c)` → `©`, `(tm)` → `™`
- **Hanging punctuation** — opening quotes hang in the margin

## Pair With

- **CKEditor** — apply `|typogrify` to CKEditor field output
- **SEOMatic** — Typogrify for display, SEOMatic for meta (don't apply `|typogrify` to meta descriptions)
