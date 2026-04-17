# Class System — Garnish.Base, Inheritance, Events, Listeners

## Source

- `src/web/assets/garnish/src/lib/Base.js` — Dean Edwards' Base.js v1.1a (prototypal inheritance engine)
- `src/web/assets/garnish/src/Base.js` — Garnish.Base (extends lib/Base with events, listeners, settings)

## Common Pitfalls

- Calling `super` or `super()` — Garnish uses `this.base()` to call parent methods, not ES6 super.
- Passing a string method name to `addListener` that doesn't exist on `this` — fails silently, listener never fires.
- Forgetting that `init()` is called automatically by the constructor — don't call `init()` manually from `extend()`.
- Overriding `constructor` — override `init()` instead; constructor is internal to the class system.
- Not calling `this.base()` in overridden lifecycle methods (especially `destroy`) — skips parent cleanup.

## Table of Contents

- [Defining a Class](#defining-a-class)
- [Inheritance and Method Overriding](#inheritance-and-method-overriding)
- [Settings Management](#settings-management)
- [Instance Events](#instance-events)
- [Class-Level Events](#class-level-events)
- [DOM Listeners](#dom-listeners)
- [Enable / Disable](#enable--disable)
- [Destroy Lifecycle](#destroy-lifecycle)
- [Namespace System](#namespace-system)

---

## Defining a Class

All Garnish classes are created with `Garnish.Base.extend()`:

```javascript
Craft.MyWidget = Garnish.Base.extend(
  {
    // Instance properties and methods (first argument)
    $element: null,
    isActive: false,

    init: function (element, settings) {
      this.$element = $(element);
      this.setSettings(settings, Craft.MyWidget.defaults);

      this.addListener(this.$element, 'activate', 'handleActivate');
    },

    handleActivate: function (ev) {
      this.isActive = true;
      this.trigger('activate');
    },

    destroy: function () {
      this.$element.removeData('myWidget');
      this.base(); // ALWAYS call parent destroy
    },
  },
  {
    // Static properties and methods (second argument, optional)
    defaults: {
      speed: 300,
      onActivate: $.noop,
    },
  }
);
```

**Key rules:**
- `init()` is the constructor — called automatically when you `new Craft.MyWidget(el, settings)`
- The first argument to `extend()` is the instance prototype
- The second argument (optional) is static properties, attached to the class itself
- Convention: store defaults as a static `defaults` object

## Inheritance and Method Overriding

```javascript
// Single-level inheritance
Craft.FancyWidget = Craft.MyWidget.extend({
  init: function (element, settings) {
    // Call parent init
    this.base(element, settings);

    // Additional setup
    this.$element.addClass('fancy');
  },

  handleActivate: function (ev) {
    this.base(ev); // Call parent handleActivate
    this.$element.addClass('activated');
  },
});
```

**`this.base(...args)`** calls the parent class's version of the current method. It works at any depth of inheritance. This is the Garnish equivalent of `super.method()`.

The drag system uses multi-level inheritance:
```
Garnish.Base
  → Garnish.BaseDrag
    → Garnish.Drag
      → Garnish.DragSort
      → Garnish.DragDrop
    → Garnish.DragMove
```

## Settings Management

```javascript
init: function (element, settings) {
  // Merges: base settings ← defaults ← user settings
  this.setSettings(settings, Craft.MyWidget.defaults);

  // Access merged settings
  console.log(this.settings.speed); // 300 (or user override)
}
```

`setSettings(settings, defaults)` performs a shallow `$.extend()`:
```javascript
this.settings = $.extend({}, this.settings || {}, defaults, settings);
```

If a class inherits settings from a parent, the merge is cumulative — parent defaults are preserved unless overridden.

## Instance Events

Every Garnish.Base instance has its own event system (separate from jQuery DOM events):

```javascript
// Listen to an instance event
widget.on('activate', function (ev) {
  console.log(ev.target); // the widget instance
});

// Listen once
widget.once('show', function (ev) { ... });

// Remove a specific handler
widget.off('activate', myHandler);

// Trigger an event from inside the class
this.trigger('activate'); // fires instance + class-level handlers
this.trigger('activate', { extra: 'data' }); // pass extra data
```

**Event object shape:**
```javascript
{
  type: 'activate',
  target: widgetInstance,
  data: { ... },  // from handler registration
  // ...plus any extra data from trigger()
}
```

**Common events** triggered by Garnish classes:
- `destroy` — on all classes, when `destroy()` is called
- `show` / `hide` — Modal, HUD, DisclosureMenu, CustomSelect
- `fadeIn` / `fadeOut` — Modal
- `escape` — Modal (before hiding)
- `submit` — HUD (form submission)
- `optionselect` — CustomSelect, MenuBtn
- `selectionChange` — Select
- `focusItem` — Select
- `dragStart` / `drag` / `dragStop` — BaseDrag and subclasses
- `sortChange` / `insertionPointChange` — DragSort
- `dropTarget` — DragDrop
- `addLayer` / `removeLayer` — UiLayerManager

## Class-Level Events

Listen to events on ALL instances of a class:

```javascript
// Fires whenever ANY Modal triggers 'show'
Garnish.on(Garnish.Modal, 'show', function (ev) {
  console.log('A modal was shown:', ev.target);
});

// Works with Craft classes too (they extend Garnish.Base)
Garnish.on(Craft.Slideout, 'show', function (ev) { ... });

// Remove
Garnish.off(Garnish.Modal, 'show', myHandler);

// Once
Garnish.once(Garnish.Modal, 'show', function (ev) { ... });
```

This is how one part of the CP can react to widgets created elsewhere — the events bubble from `instance.trigger()` through both instance handlers and class-level handlers.

## DOM Listeners

`addListener` binds jQuery events to DOM elements with automatic namespacing and cleanup:

```javascript
// String method name (resolved on `this`)
this.addListener(this.$element, 'click', 'handleClick');

// Function reference (bound to `this` automatically)
this.addListener(this.$element, 'click', function (ev) {
  // `this` is the widget instance, not the DOM element
});

// Multiple events
this.addListener(this.$element, 'mouseenter, mouseleave', 'handleHover');

// With data
this.addListener(this.$element, 'click', { key: 'value' }, 'handleClick');
```

**Key behavior:**
- All listeners are namespaced with a random `.Garnish{id}` suffix — prevents collision
- Listeners respect enable/disable state — when `this._disabled` is true, handlers don't fire
- `addListener` remembers the element — `destroy()` removes all listeners automatically

**Removing listeners:**
```javascript
// Remove specific event from element
this.removeListener(this.$element, 'click');

// Remove all namespaced events from element
this.removeAllListeners(this.$element);
```

## Enable / Disable

```javascript
widget.disable(); // All addListener handlers stop firing
widget.enable();  // Handlers resume
```

This is used by Modal (disabled while hiding), HUD, and other widgets during transitions.

## Destroy Lifecycle

```javascript
destroy: function () {
  // 1. Clean up widget-specific state
  this.$container.removeData('myWidget');
  this.$container.remove(); // if the widget owns this DOM

  // 2. ALWAYS call parent destroy
  this.base();
}
```

`Garnish.Base.destroy()` does:
1. `this.trigger('destroy')` — notifies listeners
2. `this.removeAllListeners(this._listeners)` — removes all jQuery listeners added via `addListener`

**When to call destroy:**
- When removing a widget from the DOM permanently
- When a slideout/modal that contained widgets is closed
- When replacing one widget instance with another on the same element

## Namespace System

Each Garnish.Base instance gets a unique namespace string: `.Garnish{randomId}` (e.g., `.Garnish847291036`).

This namespace is appended to all jQuery events registered via `addListener`:
```javascript
// When you write:
this.addListener($el, 'click', handler);

// Garnish actually binds:
$el.on('click.Garnish847291036', handler);
```

This ensures:
- `removeAllListeners($el)` only removes THIS instance's handlers (via `$el.off('.Garnish847291036')`)
- Multiple Garnish instances can listen on the same element without interfering
- `destroy()` cleanly removes only the destroyed instance's listeners

---

## See Also

- `ui-widgets.md` — Modal, HUD, Select, and other widgets that extend Garnish.Base
- `drag-system.md` — Drag class hierarchy built on Garnish.Base inheritance
- `utilities.md` — Class-level events (`Garnish.on/off`), custom jQuery events, UiLayerManager
- `integration.md` — How to structure Craft.* classes that extend Garnish.Base
