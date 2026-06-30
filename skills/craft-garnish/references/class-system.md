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
- Calling `this.disable()` to "pause" an overlay on a class that *also* owns its trigger listener — `disable()` silences every one of the instance's `addListener` handlers, so the trigger fires once and then dies. Use state flags or a separate instance (see [Enable / Disable](#enable--disable)).

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
- `addLayer` / `removeLayer` — UiLayerManager

(DragDrop triggers no instance events for drop targets — it reports changes via the `onDropTargetChange($activeDropTarget)` settings callback instead.)

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

`disable()` / `enable()` flip a single `this._disabled` flag. Every handler bound via `addListener` is wrapped so it checks that flag before running:

```javascript
// Garnish.Base.addListener (paraphrased from src/Base.js)
$elem.on(events, data, $.proxy(function () {
  if (!this._disabled) {
    return func.apply(this, arguments);
  }
}, this));
```

So `disable()` silences **every** `addListener` handler on that instance at once — there is no per-listener granularity. It is used by Modal (`disable()` on hide, `enable()` on show), HUD, and other widgets during transitions.

### Pitfall: `disable()` kills your own trigger listeners

This bites when **one** `Garnish.Base` subclass owns *both* a persistent trigger (a launcher button/menu bound with `addListener`) *and* a transient overlay it opens. Calling `this.disable()` to "pause" the overlay on close also silences the trigger handler — so the launcher works **once**, then goes dead:

```javascript
// BROKEN — one instance owns trigger + overlay
Craft.Launcher = Garnish.Base.extend({
  init: function () {
    this.addListener(this.$button, 'activate', 'open'); // persistent trigger
  },
  open: function () {
    this.enable();
    this.$overlay.addClass('visible');
    this.addListener(this.$overlay, 'keydown', 'handleKeydown');
  },
  close: function () {
    this.$overlay.removeClass('visible');
    this.disable(); // ❌ also silences the 'activate' trigger — button now dead
  },
});
```

Two correct options:

```javascript
// FIX 1 — guard re-entry with state flags, never disable() the instance
close: function () {
  if (!this.isOpen) return;
  this.isOpen = false;
  this.$overlay.removeClass('visible');
  this.removeListener(this.$overlay, 'keydown'); // drop only the overlay's listeners
},
open: function () {
  if (this.isOpen) return; // guard instead of relying on enable/disable
  this.isOpen = true;
  this.$overlay.addClass('visible');
  this.addListener(this.$overlay, 'keydown', 'handleKeydown');
},
```

```javascript
// FIX 2 — separate instances: the overlay gets its own Garnish.Base,
// so disabling it never touches the launcher's trigger listener
Craft.Launcher = Garnish.Base.extend({
  init: function () {
    this.addListener(this.$button, 'activate', () => this.overlay.show());
  },
});
Craft.Overlay = Garnish.Base.extend({ /* owns only the overlay; safe to disable() */ });
```

This is exactly why Garnish's own `Modal` can safely `disable()` on hide: its trigger lives on a **separate** element (`settings.triggerElement`), not bound on the Modal instance — so disabling the Modal never deafens whatever opens it.

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
