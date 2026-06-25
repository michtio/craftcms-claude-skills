# CKEditor

First-party rich text editor by Pixel & Tonic. CKEditor 5 (currently bundled at upstream 48.x) with drag-and-drop toolbar config, nested entries, element linking, image uploads, custom styles, and HTML Purifier integration. Replaces Redactor as Craft's default rich text solution.

`craftcms/ckeditor` — Free. Current major: 5.x.

## Documentation

- GitHub (primary docs): https://github.com/craftcms/ckeditor
- Plugin Store: https://plugins.craftcms.com/ckeditor
- CKEditor 5 config reference: https://ckeditor.com/docs/ckeditor5/latest/api/module_core_editor_editorconfig-EditorConfig.html

When unsure about CKEditor options, `WebFetch` the GitHub readme.

## Common Pitfalls

- Not enabling HTML Purifier rules for custom styles — CKEditor's client-side editor allows certain markup, but HTML Purifier strips it on save if the rules don't permit it. Relax Purifier config in `config/htmlpurifier/` when adding custom styles or plugins.
- Forgetting to cache oEmbed content — with "Parse embeds" enabled, CKEditor fetches embed HTML on every request. Wrap output in `{% cache %}` tags or use Blitz.
- Nested entries without partial templates — nested entries render via `_partials/entry/{entryTypeHandle}.twig`. Missing templates produce blank output.
- Using `{{ entry.ckeditorField }}` directly when nested entries exist — the field returns an iterable chunk array, not a string. Direct output renders `Array`. Always use the chunk loop pattern.
- Configuring heading levels in both the field's `$headingLevels` setting and the config options' `heading.options` — the field setting takes precedence. Don't set `heading.options` in config unless you need fine-grained control beyond what the field exposes.
- Images as `<img>` vs nested entries — CKEditor supports both via `$imageMode`. Using nested entries gives editors more control (alt text fields, captions, transforms) but adds rendering complexity. See Image Mode below.
- Pre-5.0 custom plugin asset bundles silently break — plugin 5.0.0 changed third-party CKEditor plugin registration to ES modules. Asset bundles built against the 4.x pattern load but their plugins never register. See Extending with Custom Plugins.
- Pre-5.0 CKEditor Config records carrying toolbar/heading settings — these have moved to field-level settings (`$toolbar`, `$headingLevels`). The v5 upgrade migrates them; double-check fields after upgrade.

## Configuration

CKEditor field settings expose toolbar arrangement, heading levels, config options, and custom styles directly on the field — no separate "CKEditor Config" record needed for these (as of 5.0.0). Shared configs that span multiple fields live in `config/ckeditor/` files (as of 5.3.0).

### Field Settings

The CKEditor field carries these settings, configurable in the field's UI or programmatically:

| Setting | Type | Purpose |
|---------|------|---------|
| `$toolbar` | array | Toolbar button arrangement. Default: `['heading', '\|', 'bold', 'italic', 'link']` |
| `$headingLevels` | array \| false | Allowed heading levels. Default: `[1..6]`. `false` disables headings entirely. |
| `$options` | string | Inline JS/JSON config (CKEditor `EditorConfig` shape) |
| `$styles` | string | Inline CSS for the editor surface |
| `$jsFile` | string | Path to a `.js` or `.json` file in `config/ckeditor/` (5.3.0+) |
| `$cssFile` | string | Path to a `.css` file in `config/ckeditor/` (5.3.0+) |
| `$imageMode` | string | `'img'` (default) or `'entries'` (5.0.0+, see Image Mode) |
| `$imageEntryTypeUid` | string | Entry type UID used when `$imageMode = 'entries'` |
| `$imageFieldUid` | string | Assets field UID inside the image entry type |
| `$advancedLinkFields` | array | Extra fields shown in the link modal (5.0.0+, see Link Configuration) |
| `$fullGraphqlData` | bool | GraphQL Mode toggle (4.8.0+, see GraphQL Mode) |

Programmatic config goes through `Field::getJson()` / `Field::setJson()`:

```php
$json = $field->getJson();
$json['toolbar'][] = 'fullscreen';
$field->setJson($json);
```

### Config Options (JSON)

Inline config goes in the field's "Config Options" textarea, or in a `.json` / `.js` file referenced by `$jsFile`:

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

Custom `toolbar` values are respected as of plugin 5.2.0 — earlier versions silently overrode toolbar in the config with the field-level setting. Set toolbar via the field setting where possible; reach for config-level `toolbar` only for ordering tweaks that the UI can't express.

### Config as Files (5.3.0+)

Drop shared configs into `config/ckeditor/` and reference them per-field:

```
config/
└── ckeditor/
    ├── default.js          # CKEditor config (JS export or JSON)
    ├── minimal.json
    └── editor-styles.css   # Custom CSS for the editor surface
```

Set `$jsFile = 'default.js'` and `$cssFile = 'editor-styles.css'` on the field. The v5 upgrade migration auto-extracts shared configs from CKEditor Config records into `config/ckeditor/` files when the same config is used by 2+ fields.

### Custom Styles

Custom style classes appear in the editor's Styles dropdown:

```json
[
  { "label": "Lead Text", "element": "p", "classes": ["text-lead"] },
  { "label": "Callout", "element": "div", "classes": ["callout"] },
  { "label": "Button Link", "element": "a", "classes": ["btn", "btn-primary"] }
]
```

The CSS that styles these classes inside the editor surface lives in `$styles` (inline) or `$cssFile` (5.3.0+). `@import` works in the `$cssFile` CSS as of 5.2.1 — pull in shared font/color tokens without inlining them.

Ensure HTML Purifier permits the corresponding classes and elements on save.

## Image Mode (5.0.0+)

CKEditor fields can render images two ways:

- **`$imageMode = 'img'`** (default) — images are inserted as `<img>` tags directly in the content. Simplest, but no per-image alt text or caption fields beyond what the image upload dialog captures.
- **`$imageMode = 'entries'`** — each image is inserted as a nested entry of a configured type. The image entry type carries an Assets field plus any other fields you want (alt text, caption, focal point overrides). Editors interact with images as element chips.

To use entries mode, configure `$imageEntryTypeUid` (the entry type UID) and `$imageFieldUid` (the Assets field UID inside that entry type). The entry type's field layout determines what editors can configure per-image.

```php
$field->imageMode = \craft\ckeditor\Field::IMAGE_MODE_ENTRIES;
$field->imageEntryTypeUid = $imageEntryType->uid;
$field->imageFieldUid = $imageAssetsField->uid;
```

Drag-and-drop uploads work in both modes. In entries mode, dropping an image creates a new nested entry with the dropped file in the configured Assets field (5.0.0; refined in 5.2.0 to work even when the toolbar has only the "Add nested content" button, no dedicated "Insert image").

## Link Configuration (5.0.0+)

The link modal was rebuilt on top of Craft's native Link fields in 5.0.0. The link picker supports the same target types as a regular Link field (URL, email, phone, asset, entry, category, custom element types registered via Link field events).

`$advancedLinkFields` opts in to additional fields in the link modal — labels, target attributes, link types beyond the defaults. The setting is an array of field handles drawn from a Link field's settings schema. Default: empty (basic link picker only).

New links default to the first available link type as of 5.4.0 (typically "Entry"), instead of leaving the type unselected.

## GraphQL Mode (4.8.0+)

Set `$fullGraphqlData = true` to expose the CKEditor field as a structured object in GraphQL, not just the rendered HTML string. Two GraphQL types ship:

- **`craft\ckeditor\gql\CkeditorMarkup`** (default) — returns the rendered markup as a string. Schema field: `myField` returns `String`.
- **`craft\ckeditor\gql\CkeditorData`** (when `$fullGraphqlData = true`) — returns both the markup and the nested entries as queryable elements. Schema fields: `myField.markup` (string), `myField.entries` (array of entries with full GraphQL surface — query their fields like any other entry).

Use `CkeditorData` when the headless front-end needs to render nested entries with the same flexibility as the Twig chunk-iteration pattern. Use `CkeditorMarkup` when the back end has already rendered everything to HTML and the front end just paints it.

## Nested Entries

CKEditor fields can embed Craft entries inline within rich text content — Craft 5's replacement for Matrix-in-rich-text patterns.

### Setup

1. Create entry types for your nested content (e.g., `imageBlock`, `codeBlock`, `quoteBlock`).
2. Edit the CKEditor field → select which entry types are available.
3. The toolbar surfaces entry types two ways:
   - **Entry types with icons** get dedicated toolbar buttons (configurable via the entry type's icon setting).
   - **Entry types without icons** are grouped under a single "+" / "Add nested content" button.

The 4.8.0-era "'New' Button Label" setting was removed in 5.0.0 — the "+" button is named automatically based on what the field allows.

`Field::entryType()` returns the configured nested-entries entry type when one is set, useful for programmatic introspection.

### Front-End Rendering

Always use the chunk iteration pattern — it handles both plain HTML and nested entries correctly. Direct output (`{{ entry.richContent }}`) only works when the field has zero nested entries; if nested entries exist, it renders as `Array`.

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

### Value Helpers (4.8.0+)

For non-chunk workflows, the field value (`craft\ckeditor\data\FieldData`) and individual markup chunks (`craft\ckeditor\data\Markup`) expose helpers:

- **`$value->getEntries(): EntryQuery`** — all nested entries as a query you can further filter / eager-load. Useful for collecting all images across a CKEditor field, or counting nested entries of a specific type.
- **`$markupChunk->getMarkdown(): string`** — markup chunk as Markdown.
- **`$markupChunk->getPlainText(): string`** — markup chunk as plain text (HTML stripped).

```twig
{# All embedded images, regardless of where they appear in the field #}
{% set embeddedImages = entry.richContent.entries.type('imageBlock').all() %}

{# Plain-text excerpt for OpenGraph / search index #}
{% set excerpt = entry.richContent|first.plainText|slice(0, 160) %}
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

## Fullscreen Toolbar Item (5.0.0+)

The `fullscreen` toolbar item maximizes the editor to fill the viewport. Add it to the field's `$toolbar` array or the config's `toolbar` array. Useful for content-heavy fields where editors want extra working room without a slideout.

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

Converts all Redactor fields to CKEditor fields, preserving content. Run once during the Craft 5 upgrade process. Nested-context conversion is correct as of 4.10.0.

## Reference Deletion Blocker (5.6.0+ — requires Craft 5.10)

Plugin 5.6.0 hooks into Craft 5.10's deletion-blocker subsystem (see `craftcms/elements.md` → Deletion Blockers) to prevent silent orphaning of CKEditor references. When an editor tries to delete an element that appears inside a CKEditor field somewhere — embedded as a nested entry, linked via the link picker, used as an image source — Craft now surfaces the conflict in the deletion modal instead of letting the delete proceed and leaving broken markup behind.

The mechanism: a new `ckeditor_references` table tracks every cross-reference. `craft\ckeditor\deletionblockers\ReferenceDeletionBlocker` listens for delete attempts on any element type and consults the table. If the element is referenced, the blocker reports the offending CKEditor fields and (when possible) offers reassignment to a replacement element.

### Upgrade step

Existing CKEditor field data won't be in the `ckeditor_references` table until you backfill it. After upgrading to plugin 5.6.0 on a Craft 5.10 install:

```bash
ddev craft resave/all --with-fields=ckeditor
```

Adjust `--with-fields` to match the handles of the CKEditor fields you want indexed (comma-separated for multiple). The resave walks each element, parses its CKEditor field values, and populates `ckeditor_references`. Until this completes, the blocker has nothing to block on and deletions proceed as before 5.6.0.

This is a one-time migration. New saves write to `ckeditor_references` automatically.

### `removePlugins` config respected (5.6.0+)

Before 5.6.0, custom `removePlugins` config values were silently ignored. As of 5.6.0 the value passes through to CKEditor — useful for disabling built-in plugins (like the upload adapter or autoformat) that conflict with custom workflows. Pair with `removePlugins` in your inline config or `$jsFile`.

## Extending with Custom Plugins (5.0.0+ — Breaking)

Third-party CKEditor plugins ship as **ES modules** as of plugin 5.0.0 — the asset-bundle-only registration from 4.x is gone. The new pattern:

1. **Asset bundle** extending `craft\ckeditor\web\assets\BaseCkeditorPackageAsset` and declaring `$namespace` (matches the ES module's exported namespace):

    ```php
    namespace mycompany\myplugin\web\assets;

    use craft\ckeditor\web\assets\BaseCkeditorPackageAsset;

    class MyCkeditorPackageAsset extends BaseCkeditorPackageAsset
    {
        public string $namespace = 'MyCkeditorPlugin';

        public $sourcePath = '@mycompany/myplugin/web/assets/dist';
        public $js = ['my-ckeditor-plugin.js'];
    }
    ```

2. **Plugin source** built as an ES module that exports the plugin class on the declared namespace. Bundle via Vite/Rollup/Webpack — the build output must be a single JS file that registers the plugin on `window.MyCkeditorPlugin`.

3. **Register the asset bundle** via the `CkeditorConfig` helper or by adding to the plugin's component config:

    ```php
    use craft\ckeditor\helpers\CkeditorConfig;

    CkeditorConfig::registerPackageAsset(MyCkeditorPackageAsset::class);
    ```

The pre-5.0 pattern (`\craft\ckeditor\Plugin::registerCkeditorPackage()` with a plain asset bundle) still loads but won't activate plugins built without the ES module wrapper. Audit any custom packages during the 4.x → 5.x upgrade.

The `BaseCkeditorPackageAsset::getImportCompliantLanguage()` helper (5.2.0+) returns the user's CKEditor language code in a form compatible with `import()` statements — useful when your plugin needs to load a language file on demand.

## Pair With

- **Typogrify** — apply smart typography filters to CKEditor output: `{{ entry.richContent|typogrify }}`
- **Embedded Assets** — for oEmbed content within CKEditor or alongside it
