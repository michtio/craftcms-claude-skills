# CKEditor

First-party rich text editor by Pixel & Tonic. CKEditor 5 with drag-and-drop toolbar config, nested entries, element linking, image uploads, custom styles, and HTML Purifier integration. Replaces Redactor as Craft's default rich text solution.

`craftcms/ckeditor` — Free

## Documentation

- GitHub (primary docs): https://github.com/craftcms/ckeditor
- Plugin Store: https://plugins.craftcms.com/ckeditor
- CKEditor 5 config reference: https://ckeditor.com/docs/ckeditor5/latest/api/module_core_editor_editorconfig-EditorConfig.html

When unsure about CKEditor options, `WebFetch` the GitHub readme.

## Common Pitfalls

- Not enabling HTML Purifier rules for custom styles — CKEditor's client-side editor allows certain markup, but HTML Purifier strips it on save if the rules don't permit it. Relax Purifier config in `config/htmlpurifier/` when adding custom styles or plugins.
- Forgetting to cache oEmbed content — with "Parse embeds" enabled, CKEditor fetches embed HTML on every request. Wrap output in `{% cache %}` tags or use Blitz.
- Nested entries without partial templates — nested entries render via `_partials/entry/{entryTypeHandle}.twig`. Missing templates produce blank output.
- Using `{{ entry.ckeditorField }}` without chunk iteration when nested entries exist — string output works for plain HTML content, but nested entries need the chunk loop to render correctly.
- Configuring heading levels in both the CKEditor config and the field settings — the field's "Heading Levels" setting takes precedence. Don't set `heading.options` in config options unless you need fine-grained control beyond what the UI provides.
- Images as `<img>` vs nested entries — CKEditor supports both. Using nested entries for images gives editors more control (alt text fields, captions, transforms) but adds complexity.

## Configuration

CKEditor configs are managed in the CP under Settings → CKEditor. Each config defines:

- **Toolbar** — drag-and-drop button arrangement
- **Config Options** — static JSON or JavaScript snippet for CKEditor 5 options
- **Custom Styles** — CSS classes available in the Styles dropdown

Configs are reusable across multiple CKEditor fields.

### Config Options (JSON)

```json
{
  "table": {
    "contentToolbar": [
      "toggleTableCaption",
      "tableColumn",
      "tableRow",
      "mergeTableCells",
      "tableProperties",
      "tableCellProperties"
    ]
  },
  "list": {
    "properties": {
      "styles": true,
      "startIndex": true,
      "reversed": true
    }
  }
}
```

### Custom Styles

In the CKEditor config's Styles field:

```json
[
  { "label": "Lead Text", "element": "p", "classes": ["text-lead"] },
  { "label": "Callout", "element": "div", "classes": ["callout"] },
  { "label": "Button Link", "element": "a", "classes": ["btn", "btn-primary"] }
]
```

Ensure your HTML Purifier config allows the corresponding classes and elements.

## Nested Entries

CKEditor fields can embed Craft entries inline within rich text content — Craft 5's replacement for Matrix-in-rich-text patterns.

### Setup

1. Create entry types for your nested content (e.g., `imageBlock`, `codeBlock`, `quoteBlock`)
2. Edit the CKEditor config → drag the "+" button into the toolbar
3. Edit the CKEditor field → select which entry types are available
4. Optionally enable "Show toolbar buttons for entry types with icons" for dedicated buttons

### Front-End Rendering

CKEditor field content with nested entries is iterable as chunks:

```twig
{% for chunk in entry.richContent %}
    {% if chunk.type == 'markup' %}
        <div class="prose">{{ chunk }}</div>
    {% elseif chunk.type == 'entry' %}
        {% include '_partials/entry/' ~ chunk.entry.type.handle with {
            entry: chunk.entry
        } only %}
    {% endif %}
{% endfor %}
```

### Partial Templates

Create templates at `_partials/entry/{entryTypeHandle}.twig`:

```twig
{# _partials/entry/imageBlock.twig #}
{% set image = entry.image.eagerly().one() %}
{% if image %}
    <figure>
        {{ image.optimizedImagesField.imgTag().loadingStrategy('lazy').render() }}
        {% if entry.caption %}
            <figcaption>{{ entry.caption }}</figcaption>
        {% endif %}
    </figure>
{% endif %}
```

### Simple String Output (No Nested Entries)

If the field has no nested entries, output directly:

```twig
{{ entry.richContent }}
```

## HTML Purifier

CKEditor passes content through HTML Purifier on save. Config files live in `config/htmlpurifier/`:

```json
// config/htmlpurifier/Default.json
{
    "Attr.AllowedClasses": [
        "text-lead", "callout", "btn", "btn-primary"
    ],
    "HTML.AllowedElements": "p,h2,h3,h4,a,strong,em,ul,ol,li,blockquote,figure,figcaption,img,table,thead,tbody,tr,th,td,div,span",
    "Attr.EnableID": true
}
```

If custom styles or plugins produce HTML that gets stripped on save, the Purifier config needs updating.

## Migration from Redactor

```bash
ddev craft ckeditor/convert
```

Converts all Redactor fields to CKEditor fields, preserving content. Run once during the Craft 5 upgrade process.

## Extending with Custom Plugins

Register a CKEditor package from a Craft plugin:

```php
// In your plugin's init()
\craft\ckeditor\Plugin::registerCkeditorPackage(MyCustomAsset::class);
```

The asset bundle extends `BaseCkeditorPackageAsset` and defines the plugin's build directory, JS file, plugin names, and toolbar items.

## Pair With

- **Typogrify** — apply smart typography filters to CKEditor output: `{{ entry.richContent|typogrify }}`
- **Embedded Assets** — for oEmbed content within CKEditor or alongside it
