# Integration — Asset Bundles, Webpack, Craft.* Classes, Form Widgets

## Source

- `src/web/assets/garnish/GarnishAsset.php`
- `src/web/assets/garnish/webpack.config.js`
- `src/web/assets/garnish/src/index.js`
- `src/web/assets/cp/CpAsset.php`
- `packages/craftcms-webpack/index.js` (externals config)
- `src/web/assets/garnish/src/NiceText.js`
- `src/web/assets/garnish/src/CheckboxSelect.js`
- `src/web/assets/garnish/src/MixedInput.js`
- `src/web/assets/garnish/src/MultiFunctionBtn.js`

## Common Pitfalls

- Bundling Garnish into a plugin's webpack output — use `import Garnish from 'garnishjs'` which resolves to the global via externals.
- Requiring Garnish before `CpAsset` is loaded — if your asset bundle doesn't depend on `CpAsset` (or `GarnishAsset`), Garnish won't be available.
- Using `Craft.MyClass = function() {}` instead of `Garnish.Base.extend()` — loses event system, listener management, settings, and destroy lifecycle.
- Calling `Craft.initUiElements()` on content without context — it re-initializes all UI widgets in the container, which can double-instantiate.

## Table of Contents

- [Loading Sequence](#loading-sequence)
- [GarnishAsset PHP Bundle](#garnishasset-php-bundle)
- [Webpack Configuration](#webpack-configuration)
- [Plugin Asset Bundles](#plugin-asset-bundles)
- [Craft.* Class Pattern](#craft-class-pattern)
- [Twig JavaScript Blocks](#twig-javascript-blocks)
- [Form Widgets](#form-widgets)

---

## Loading Sequence

```
1. <head>
   └── CpAsset registered
       ├── depends on GarnishAsset
       │   ├── depends on JqueryAsset
       │   ├── depends on VelocityAsset
       │   ├── depends on JqueryTouchEventsAsset
       │   └── depends on ElementResizeDetectorAsset
       └── registers cp.js, cp.css

2. Asset load order (guaranteed by Yii2 dependency resolution):
   jquery.js
   → jquery-touch-events.js
   → velocity.js
   → element-resize-detector.js
   → garnish.js          ← window.Garnish available
   → cp.js               ← Craft.CP, Craft.* classes
   → plugin assets        ← your code

3. Initialization:
   garnish/src/index.js creates singletons:
     Garnish.uiLayerManager = new Garnish.UiLayerManager()
     Garnish.escManager = new Garnish.EscManager()

   cp.js initializes:
     Craft.cp = new Craft.CP()
```

---

## GarnishAsset PHP Bundle

```php
// craft\web\assets\garnish\GarnishAsset
class GarnishAsset extends AssetBundle
{
    public function init(): void
    {
        $this->sourcePath = __DIR__ . '/dist';
        $this->depends = [
            ElementResizeDetectorAsset::class,
            JqueryAsset::class,
            JqueryTouchEventsAsset::class,
            VelocityAsset::class,
        ];
        $this->js = ['garnish.js'];
        parent::init();
    }
}
```

The compiled `dist/garnish.js` (134KB) is a single bundle containing all Garnish classes.

---

## Webpack Configuration

### Garnish's Own Build

```javascript
// src/web/assets/garnish/webpack.config.js
module.exports = getConfig({
  context: __dirname,
  config: {
    entry: { garnish: './index.js' },
    module: {
      rules: [{
        test: require.resolve('./src/index.js'),
        loader: 'expose-loader',
        options: {
          exposes: [{
            globalName: 'Garnish',
            moduleLocalName: 'default',
          }],
        },
      }],
    },
  },
});
```

`expose-loader` makes the default export of `index.js` available as `window.Garnish`.

### Externals for Plugin Assets

Craft's shared webpack config (`@craftcms/webpack`) configures externals:

```javascript
externals: {
  'garnishjs': 'Garnish',
  'jquery': 'jQuery',
  'craft': 'Craft',
  'axios': 'axios',
}
```

This means in any Craft asset bundle built with `@craftcms/webpack`:

```javascript
// This import resolves to window.Garnish (no bundling)
import Garnish from 'garnishjs';

// These imports also resolve to globals
import $ from 'jquery';
import Craft from 'craft';
```

### Plugin Webpack Setup

```javascript
// your-plugin/src/web/assets/myasset/webpack.config.js
const {getConfig} = require('@craftcms/webpack');

module.exports = getConfig({
  context: __dirname,
  config: {
    entry: { myasset: './src/MyAsset.js' },
  },
});
```

```javascript
// MyAsset.js
import Garnish from 'garnishjs';
import $ from 'jquery';

Craft.MyWidget = Garnish.Base.extend({
  init: function (element, settings) { ... },
});
```

---

## Plugin Asset Bundles

Your PHP asset bundle must depend on `CpAsset` (which includes `GarnishAsset`):

```php
use craft\web\assets\cp\CpAsset;

class MyPluginAsset extends AssetBundle
{
    public function init(): void
    {
        $this->sourcePath = __DIR__ . '/dist';
        $this->depends = [CpAsset::class];
        $this->js = ['myasset.js'];
        parent::init();
    }
}
```

Register it from a controller or template:
```php
// In a controller
$this->getView()->registerAssetBundle(MyPluginAsset::class);

// In Twig
{% do view.registerAssetBundle('myplugin\\web\\assets\\MyPluginAsset') %}
```

---

## Craft.* Class Pattern

All Craft CP JavaScript classes extend `Garnish.Base`:

```javascript
Craft.CP = Garnish.Base.extend({ ... });
Craft.ElementEditor = Garnish.Base.extend({ ... });
Craft.Slideout = Garnish.Base.extend({ ... });
Craft.AuthManager = Garnish.Base.extend({ ... });
Craft.ColorInput = Garnish.Base.extend({ ... });
Craft.FieldToggle = Garnish.Base.extend({ ... });
```

**Pattern for plugin classes:**

```javascript
import Garnish from 'garnishjs';

// Define on the Craft namespace so it's accessible from Twig {% js %} blocks
Craft.MyPlugin = {};

Craft.MyPlugin.FieldEditor = Garnish.Base.extend({
  $container: null,
  dragSort: null,

  init: function (container, settings) {
    this.$container = $(container);
    this.setSettings(settings, Craft.MyPlugin.FieldEditor.defaults);

    // Use Garnish widgets
    this.dragSort = new Garnish.DragSort(
      this.$container.find('.item'),
      {
        axis: Garnish.Y_AXIS,
        handle: '.move',
        onSortChange: this.handleSortChange.bind(this),
      }
    );

    // Use Garnish listeners (auto-cleanup on destroy)
    this.addListener(this.$container, 'activate', 'handleActivate');
  },

  handleActivate: function (ev) {
    // Show a HUD for inline editing
    new Garnish.HUD(ev.currentTarget, this.getEditorHtml(), {
      onSubmit: this.handleSave.bind(this),
    });
  },

  destroy: function () {
    if (this.dragSort) {
      this.dragSort.destroy();
    }
    this.base();
  },
}, {
  defaults: {
    maxItems: null,
  },
});
```

---

## Twig JavaScript Blocks

In CP templates, use `{% js %}` blocks to write JavaScript that uses Garnish:

```twig
{% js %}
  // Garnish is already available as window.Garnish
  new Garnish.DragSort($('#{{ id|namespaceInputId }}').find('.items .item'), {
    axis: Garnish.Y_AXIS,
    handle: '.move.icon',
    onSortChange: function () {
      // reorder logic
    },
  });

  // Use activate event for keyboard accessibility
  $('#{{ handle|namespaceInputId }}').on('activate', function () {
    // handle activation
  });

  // Use key constants
  $('#my-input').on('keydown', function (ev) {
    if (ev.keyCode === Garnish.RETURN_KEY && Garnish.isCtrlKeyPressed(ev)) {
      // Ctrl+Enter
    }
  });
{% endjs %}
```

**Common patterns in Twig:**
```twig
{# Disclosure menu (Garnish auto-initializes via Craft.initUiElements) #}
<button aria-controls="menu-{{ id }}" data-disclosure-trigger>Actions</button>
<div id="menu-{{ id }}" class="menu menu--disclosure">
  <ul class="padded">
    <li><button class="menu-item" type="button">Edit</button></li>
  </ul>
</div>

{# Menu button (Craft.initUiElements auto-initializes .menubtn) #}
<button class="btn menubtn">Options</button>
<div class="menu">
  <ul>
    <li><a>Option A</a></li>
    <li><a>Option B</a></li>
  </ul>
</div>
```

`Craft.initUiElements($container)` automatically initializes:
- `.menubtn` → `new Garnish.MenuBtn()`
- `[data-disclosure-trigger]` → `new Garnish.DisclosureMenu()`
- Various other Craft-specific widgets

---

## Form Widgets

### NiceText

Auto-growing textarea with optional character count and hint text.

```javascript
new Garnish.NiceText($textarea, {
  autoHeight: true,        // Auto-grow textarea height (default: true)
  showCharsLeft: false,    // Show remaining character count
  charsLeftClass: 'chars-left',
  onHeightChange: $.noop,  // Callback when height changes
});
```

**Features:**
- Auto-height: Calculates height based on content using a hidden `<stage>` element
- Character count: If `maxlength` attribute exists and `showCharsLeft` is true, displays remaining chars with `aria-live="polite"`
- Hint text: If `settings.hint` is set, shows placeholder-like overlay that fades on input
- Ctrl+Enter: Submits the closest `<form>`
- Uses `textchange` custom event for reliable value tracking

### CheckboxSelect

Checkbox group with "Select All" toggle.

```javascript
new Garnish.CheckboxSelect($container);
```

**Features:**
- Finds checkbox with `.all` class as the "select all" toggle
- When "all" is checked, individual checkboxes are disabled
- When "all" is unchecked, individual checkboxes re-enable
- Optional `localStorage` persistence via `storageKey` setting (uses `Craft.getLocalStorage()`/`Craft.setLocalStorage()`)
- Listens for `change` events on checkboxes

### MultiFunctionBtn

Button with multiple states: idle, busy, failure, retry, success.

```javascript
var btn = new Garnish.MultiFunctionBtn($button, {
  busyClass: 'loading',           // Class during busy state
  changeButtonText: false,        // Update button label text
  clearLiveRegionTimeout: 2500,   // Clear SR announcement after ms
  failureMessageDuration: 3000,   // Show failure message for ms
});

// State transitions
btn.busyEvent();     // Show loading state
btn.successEvent();  // Show success message
btn.failureEvent();  // Show failure, then retry message
```

**Data attributes on the button:**
- `data-busy-message` — Text during busy state (default: "Loading")
- `data-success-message` — Text on success (default: "Success")
- `data-failure-message` — Text on failure
- `data-retry-message` — Text after failure clears

Uses `role="status"` live region for screen reader announcements.

### MixedInput

Text input that supports inline tag elements mixed with text.

```javascript
new Garnish.MixedInput($container);
```

Used for complex input fields where users can type text interspersed with tag-like elements. Manages caret positioning and element insertion/removal within the mixed content.

### Key Methods:
- `addTextElement()` — Add a text segment
- `addElement($element)` — Add a tag/chip element inline
- `removeElement($element)` — Remove an inline element
- `getVal()` — Get the combined value

---

## See Also

- `class-system.md` — Garnish.Base.extend() pattern used by all Craft.* classes, event system, addListener
- `ui-widgets.md` — Full API for Modal, HUD, DisclosureMenu, Select — the widgets used in Twig JS blocks
- `drag-system.md` — DragSort and DragDrop APIs for reorderable and droppable interactions
- `utilities.md` — Key constants, custom events (activate, textchange, resize), ARIA helpers used in CP templates
