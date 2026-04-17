# Utilities — Constants, Custom Events, ARIA, Focus, Geometry, Animation

## Source

- `src/web/assets/garnish/src/Garnish.js` (lines 32–1193)
- `src/web/assets/garnish/src/UiLayerManager.js`
- `src/web/assets/garnish/src/EscManager.js` (deprecated)

## Common Pitfalls

- Using `Garnish.$bod` before `<body>` exists — Garnish caches `$(document.body)` at import time; if loaded in `<head>` before body, it's empty.
- Binding `resize` event on `window` instead of using `Garnish.$win.on('resize')` — the custom `resize` event only works on non-window elements (it uses ResizeObserver).
- Calling `Garnish.trapFocusWithin()` without later calling `releaseFocusWithin()` — focus stays trapped even after the modal/overlay is gone.
- Using `ev.keyCode` with magic numbers instead of `Garnish.RETURN_KEY` etc. — reduces readability and risks cross-browser issues.
- Calling `Garnish.scrollContainerToElement()` on a hidden element — offset calculations return 0.

## Table of Contents

- [Global References](#global-references)
- [Key Code Constants](#key-code-constants)
- [Other Constants](#other-constants)
- [Custom jQuery Events](#custom-jquery-events)
- [ARIA & Focus Management](#aria--focus-management)
- [UiLayerManager](#uilayermanager)
- [Geometry & Hit Testing](#geometry--hit-testing)
- [Animation](#animation)
- [Form Helpers](#form-helpers)
- [Detection](#detection)
- [Static Event System](#static-event-system)

---

## Global References

```javascript
Garnish.$win   // $(window)
Garnish.$doc   // $(document)
Garnish.$bod   // $(document.body)
Garnish.$scrollContainer  // $(window) by default, can be overridden

Garnish.rtl    // true if <body> has class 'rtl'
Garnish.ltr    // true if NOT rtl
```

---

## Key Code Constants

```javascript
Garnish.BACKSPACE_KEY  // 8
Garnish.TAB_KEY        // 9
Garnish.CLEAR_KEY      // 12
Garnish.RETURN_KEY     // 13
Garnish.SHIFT_KEY      // 16
Garnish.CTRL_KEY       // 17
Garnish.ALT_KEY        // 18
Garnish.ESC_KEY        // 27
Garnish.SPACE_KEY      // 32
Garnish.PAGE_UP_KEY    // 33
Garnish.PAGE_DOWN_KEY  // 34
Garnish.END_KEY        // 35
Garnish.HOME_KEY       // 36
Garnish.LEFT_KEY       // 37
Garnish.UP_KEY         // 38
Garnish.RIGHT_KEY      // 39
Garnish.DOWN_KEY       // 40
Garnish.DELETE_KEY     // 46
Garnish.A_KEY          // 65
Garnish.S_KEY          // 83
Garnish.CMD_KEY        // 91
Garnish.META_KEY       // 224
```

Always use these instead of magic numbers:
```javascript
// Correct
if (ev.keyCode === Garnish.ESC_KEY) { ... }

// Wrong
if (ev.keyCode === 27) { ... }
```

---

## Other Constants

```javascript
Garnish.PRIMARY_CLICK    // 1 (left mouse button)
Garnish.SECONDARY_CLICK  // 3 (right mouse button)

Garnish.X_AXIS  // 'x'
Garnish.Y_AXIS  // 'y'

Garnish.FX_DURATION  // 200 (default animation duration in ms)
Garnish.TEXT_NODE    // 3 (DOM node type)

// ARIA class markers (used internally for modal background hiding)
Garnish.JS_ARIA_CLASS       // 'garnish-js-aria'
Garnish.JS_ARIA_TRUE_CLASS  // 'garnish-js-aria-true'
Garnish.JS_ARIA_FALSE_CLASS // 'garnish-js-aria-false'
```

---

## Custom jQuery Events

Garnish registers three custom events via `$.event.special`:

### `activate`

Fires on click OR keyboard activation (Space/Enter). The primary way to make non-`<button>` elements keyboard-accessible.

```javascript
// Bind
$element.on('activate', function (ev) {
  // ev.originalEvent is the underlying click/keydown
});

// Or via addListener
this.addListener(this.$element, 'activate', 'handleActivate');

// Shorthand
$element.activate(handler);
```

**Behavior:**
- On `setup`: adds `tabindex="0"` to the element (making it focusable), unless it's `<body>` or has `.disabled`
- On `click`: fires `activate` unless `.disabled` or Ctrl+click on `<a>` with href
- On `keydown`: fires `activate` for Space or Enter (only on the bound element, not bubbled children)
- `Garnish.activateEventsMuted` flag suppresses activate events globally (set during drag)

### `textchange`

Fires when an input's value actually changes. More reliable than `input` alone.

```javascript
// Basic
$input.on('textchange', function () {
  console.log('Value changed to:', $(this).val());
});

// With delay (debounce)
$input.on('textchange', { delay: 300 }, function () {
  // Fires 300ms after last change
});

// Shorthand
$input.textchange(handler);
```

**Behavior:**
- Listens to `keypress`, `keyup`, `change`, `blur` on the element
- Compares current value to stored previous value
- Only fires if the value actually changed
- Optional `delay` parameter (via event data) debounces the handler

### `resize`

Element-level resize detection using `ResizeObserver`.

```javascript
// Fires when element dimensions change (NOT window resize)
$element.on('resize', function () {
  console.log('Element was resized');
});

// Shorthand
$element.resize(handler);
```

**Behavior:**
- Uses a shared `ResizeObserver` across all elements
- Stores previous `{width, height}` and only fires when either changes
- Does NOT apply to `window` (native window resize event handles that)
- Suppressed when `Garnish.resizeEventsMuted` is true (via `Garnish.muteResizeEvents(callback)`)

---

## ARIA & Focus Management

### Focus Trapping

```javascript
// Trap Tab/Shift+Tab within a container (for modals/overlays)
Garnish.trapFocusWithin($container);

// Release the trap
Garnish.releaseFocusWithin($container);

// Set focus to first focusable element within container
Garnish.setFocusWithin($container);
```

`setFocusWithin` is smart: it skips `.checkbox` and `.prevent-autofocus` elements, and checks that the first focusable element belongs to the first visible `.field` container (avoids jumping to a CKEditor or other complex field unexpectedly).

### Focus Queries

```javascript
// Is focus inside this container?
Garnish.focusIsInside($container);  // boolean

// Get first focusable element
Garnish.firstFocusableElement($container);  // jQuery

// Get all keyboard-focusable elements (excludes tabindex="-1")
Garnish.getKeyboardFocusableElements($container);  // jQuery

// Is this element keyboard-focusable?
Garnish.isKeyboardFocusable(element);  // boolean

// Get currently focused element
Garnish.getFocusedElement();  // jQuery
```

### Modal ARIA Helpers

```javascript
// Set aria-modal="true" and role="dialog" on container
Garnish.addModalAttributes($container);

// Hide all body children from screen readers (except topmost modal and #notifications)
Garnish.hideModalBackgroundLayers();

// Restore aria-hidden state after modal closes
Garnish.resetModalBackgroundLayerVisibility();

// Manually hide a specific element from AT
Garnish.ariaHide(element);

// Check if element was hidden by Garnish's ARIA system
Garnish.hasJsAriaClass(element);
```

The ARIA hiding system preserves the original `aria-hidden` state using CSS class markers, so it can be restored correctly even for elements that had `aria-hidden="false"` or `aria-hidden="true"` before the modal opened.

---

## UiLayerManager

Manages a stack of UI layers (base document, modals, HUDs, menus) for keyboard shortcut routing.

```javascript
// Singleton — always use:
Garnish.uiLayerManager
```

### Key Properties

```javascript
Garnish.uiLayerManager.layer          // Current layer index (0 = base)
Garnish.uiLayerManager.currentLayer   // Current layer object
Garnish.uiLayerManager.modalLayers    // Array of modal layers
Garnish.uiLayerManager.highestModalLayer  // Topmost modal layer
```

### Methods

```javascript
// Add a new layer (called by Modal.show(), HUD.show(), etc.)
Garnish.uiLayerManager.addLayer($container, { bubble: false });

// Remove the top layer
Garnish.uiLayerManager.removeLayer();

// Remove a specific layer by container
Garnish.uiLayerManager.removeLayer($container);

// Register a keyboard shortcut on the current layer
Garnish.uiLayerManager.registerShortcut(Garnish.ESC_KEY, function () {
  this.hide();
}.bind(this));

// Register with modifiers
Garnish.uiLayerManager.registerShortcut({
  keyCode: Garnish.S_KEY,
  ctrl: true,  // Cmd on Mac
  shift: false,
  alt: false,
}, saveHandler);

// Unregister a shortcut
Garnish.uiLayerManager.unregisterShortcut(Garnish.ESC_KEY);
```

### Events

| Event | When |
|-------|------|
| `addLayer` | Layer added. `ev.layer`, `ev.$container`, `ev.options` |
| `removeLayer` | Layer removed |

### How It Works

Keydown events on `<body>` are routed through `triggerShortcut()`:
1. Check the top layer's registered shortcuts for a match
2. If found, `preventDefault` and call the handler
3. If not found and `options.bubble` is true, check the next layer down
4. Handlers receive `ev.bubbleShortcut()` to manually bubble when needed

**Deprecated aliases:**
- `Garnish.escManager` — old escape key manager, still instantiated for BC
- `Garnish.shortcutManager` — alias for `Garnish.uiLayerManager`

---

## Geometry & Hit Testing

```javascript
// Get element offset (accounts for scroll container)
Garnish.getOffset($element);  // { top, left }

// Distance between two points
Garnish.getDist(x1, y1, x2, y2);  // number

// Is coordinate over an element?
Garnish.hitTest(x, y, $element);  // boolean

// Is the cursor over an element? (from a mouse event)
Garnish.isCursorOver(ev, $element);  // boolean
```

---

## Animation

```javascript
// Shake an element (validation feedback)
Garnish.shake($element);
Garnish.shake($element, 'margin-left');  // custom property

// Scroll a container to bring an element into view
Garnish.scrollContainerToElement($container, $element);
Garnish.scrollContainerToElement($element);  // auto-detect scroll parent

// requestAnimationFrame (with polyfill)
var id = Garnish.requestAnimationFrame(callback);
Garnish.cancelAnimationFrame(id);

// Respect reduced motion
Garnish.prefersReducedMotion();  // boolean
Garnish.getUserPreferredAnimationDuration(300);  // 300 or 0 if reduced motion

// Temporarily suppress resize events
Garnish.muteResizeEvents(function () {
  // DOM mutations here won't trigger resize events
});
```

---

## Form Helpers

```javascript
// Find all inputs in a container
Garnish.findInputs($container);  // input, text, textarea, select, button

// Get POST data as object { name: value }
Garnish.getPostData($container);

// Get a single input's value as it would be POSTed
Garnish.getInputPostVal($input);
// Handles: unchecked checkboxes (null), multi-selects, null <select>

// Get input's base name (strips brackets)
Garnish.getInputBasename($input);  // 'fields' from 'fields[title]'

// Copy input values from source to target container
Garnish.copyInputValues($source, $target);

// Copy text styles (font, size, etc.) from one element to another
Garnish.copyTextStyles($source, $target);
```

---

## Detection

```javascript
// Primary click (left button, no Ctrl/Meta)
Garnish.isPrimaryClick(ev);  // boolean

// Ctrl key (or Cmd on Mac)
Garnish.isCtrlKeyPressed(ev);  // boolean

// Mobile browser detection
Garnish.isMobileBrowser();         // boolean (phones only)
Garnish.isMobileBrowser(true);     // boolean (phones + tablets)

// Element attribute check
Garnish.hasAttr($element, 'data-foo');  // boolean

// Type checks
Garnish.isJquery(val);     // boolean
Garnish.isString(val);     // boolean
Garnish.isTextNode(elem);  // boolean
Garnish.isArray(val);      // boolean (deprecated, use Array.isArray)

// Is element a <script> or <style>?
Garnish.isScriptOrStyleElement(element);  // boolean

// Clamp a number within a range
Garnish.within(num, min, max);  // number

// Get the body's scrollTop (Safari bounce-safe)
Garnish.getBodyScrollTop();  // number

// Get first element from array or jQuery collection
Garnish.getElement(collection);  // DOM element
```

---

## Static Event System

Listen to events on all instances of a Garnish class:

```javascript
// Listen to ALL instances of a class
Garnish.on(Garnish.Modal, 'show', handler);
Garnish.on(Garnish.Modal, 'show', data, handler);

// Remove
Garnish.off(Garnish.Modal, 'show', handler);

// Once
Garnish.once(Garnish.Modal, 'show', handler);
```

Events support namespace syntax:
```javascript
Garnish.on(Garnish.Modal, 'show.myPlugin', handler);
Garnish.off(Garnish.Modal, 'show.myPlugin', handler);
```

These handlers fire when any instance of the class (or subclass) calls `this.trigger('show')`. Useful for global reactions to widget state changes.

---

## See Also

- `class-system.md` — Instance events (`on`/`off`/`trigger`), addListener (uses namespaces documented here), Garnish.Base
- `ui-widgets.md` — Widgets that use UiLayerManager, ARIA helpers, focus trapping, and key constants
- `drag-system.md` — Drag classes that use axis constants, hitTest, requestAnimationFrame
- `integration.md` — How custom jQuery events (activate, textchange) are used in Twig templates
