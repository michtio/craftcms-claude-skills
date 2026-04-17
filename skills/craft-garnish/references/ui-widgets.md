# UI Widgets — Modal, HUD, DisclosureMenu, MenuBtn, Select, CustomSelect

## Source

- `src/web/assets/garnish/src/Modal.js`
- `src/web/assets/garnish/src/HUD.js`
- `src/web/assets/garnish/src/DisclosureMenu.js`
- `src/web/assets/garnish/src/MenuBtn.js`
- `src/web/assets/garnish/src/CustomSelect.js`
- `src/web/assets/garnish/src/SelectMenu.js`
- `src/web/assets/garnish/src/Select.js`
- `src/web/assets/garnish/src/ContextMenu.js`

## Common Pitfalls

- Creating a Modal without a container element — pass `null` for container and set it later with `setContainer()`, or pass settings only.
- Not setting `triggerElement` on Modal — after hiding, focus has nowhere to return; the console warns about it.
- HUD `$body` is a `<form>` — calling `show()` on an HUD that contains form inputs will submit on Enter unless you handle `submit` event.
- Double-instantiating widgets — all widgets warn and destroy the previous instance, but it's wasteful. Check `$el.data('modal')` first.
- DisclosureMenu requires `aria-controls` on the trigger pointing to the container's ID — instantiation throws if the container isn't found.
- MenuBtn expects `.menu` as the next sibling by default — if your markup differs, pass the menu element explicitly.

## Table of Contents

- [Modal](#modal)
- [HUD (Heads-Up Display)](#hud-heads-up-display)
- [DisclosureMenu](#disclosuremenu)
- [MenuBtn](#menubtn)
- [CustomSelect](#customselect)
- [SelectMenu](#selectmenu)
- [Select](#select)
- [ContextMenu](#contextmenu)

---

## Modal

Full-screen dialog with shade overlay, focus trapping, and optional drag/resize.

### Constructor

```javascript
// With container
var modal = new Garnish.Modal($container, {
  autoShow: true,
  draggable: true,
  dragHandleSelector: '.header',
  resizable: false,
  hideOnEsc: true,
  hideOnShadeClick: true,
  shadeClass: 'modal-shade',
  triggerElement: this.$btn,
  onShow: function () { },
  onHide: function () { },
});

// Without container (set later)
var modal = new Garnish.Modal({ autoShow: false });
modal.setContainer($container);
modal.show();
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `autoShow` | `true` | Show immediately on construction |
| `draggable` | `false` | Enable drag-to-move via DragMove |
| `dragHandleSelector` | `null` | CSS selector for drag handle within container |
| `resizable` | `false` | Enable drag-to-resize from corner |
| `minGutter` | `10` | Minimum px between modal edge and viewport |
| `hideOnEsc` | `true` | Close on Escape key |
| `hideOnShadeClick` | `true` | Close when clicking the shade |
| `closeOtherModals` | `false` | Hide other visible modals when showing |
| `triggerElement` | `null` | Element to return focus to on hide (auto-detected if null) |
| `shadeClass` | `'modal-shade'` | CSS class for the shade overlay |
| `onShow` | `$.noop` | Callback on show |
| `onHide` | `$.noop` | Callback on hide |
| `onFadeIn` | `$.noop` | Callback after fade-in animation |
| `onFadeOut` | `$.noop` | Callback after fade-out animation |

### Key Methods

| Method | Description |
|--------|-------------|
| `show()` | Show modal with fade-in. Adds UI layer, traps focus, hides background from AT. |
| `hide()` | Hide modal with fade-out. Removes UI layer, restores focus to trigger. |
| `quickShow()` | Show without animation |
| `quickHide()` | Hide without animation |
| `setContainer(el)` | Set/change the modal's container element |
| `updateSizeAndPosition()` | Recalculate size and center in viewport |
| `destroy()` | Remove container, shade, draggers; clean up |

### Events

| Event | When |
|-------|------|
| `show` | After modal becomes visible |
| `hide` | After modal is hidden |
| `fadeIn` | After fade-in animation completes |
| `fadeOut` | After fade-out animation completes |
| `escape` | When ESC is pressed (before hide) |
| `updateSizeAndPosition` | After size/position recalculation |

### Statics

| Property | Description |
|----------|-------------|
| `Garnish.Modal.instances` | Array of all Modal instances |
| `Garnish.Modal.visibleModal` | Currently visible modal (or null) |

### Accessibility

- Sets `aria-modal="true"` and `role="dialog"` on container
- Traps focus within the modal via `Garnish.trapFocusWithin()`
- Hides background content from screen readers via `Garnish.hideModalBackgroundLayers()`
- Adds `no-scroll` class to `<body>` while visible
- Restores focus to `triggerElement` on close (with visibility check)
- Live region (`role="status"`) appended to container for announcements

---

## HUD (Heads-Up Display)

Floating popover anchored to a trigger element, with a pointer tip. The body is a `<form>`.

### Constructor

```javascript
var hud = new Garnish.HUD(this.$trigger, bodyHtml, {
  orientations: ['bottom', 'top', 'right', 'left'],
  triggerSpacing: 10,
  windowSpacing: 10,
  onShow: function () { },
  onHide: function () { },
  onSubmit: function () { },
});
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `orientations` | `['bottom','top','right','left']` | Preferred placement order |
| `triggerSpacing` | `10` | Gap between trigger and HUD edge |
| `windowSpacing` | `10` | Minimum gap between HUD and viewport |
| `tipWidth` | `30` | Width of the pointer tip |
| `minBodyWidth` | `200` | Minimum HUD width |
| `minBodyHeight` | `0` | Minimum HUD height |
| `withShade` | `true` | Show backdrop shade |
| `showOnInit` | `true` | Show immediately |
| `closeOtherHUDs` | `true` | Close other active HUDs |
| `hideOnEsc` | `true` | Close on Escape |
| `hideOnShadeClick` | `true` | Close when clicking shade |
| `closeBtn` | `null` | Optional close button element |
| `listenToMainResize` | `true` | Reposition when main content resizes |
| `onShow` | `$.noop` | Callback |
| `onHide` | `$.noop` | Callback |
| `onSubmit` | `$.noop` | Callback |

### Key Methods

| Method | Description |
|--------|-------------|
| `show()` | Show HUD, position relative to trigger |
| `hide()` | Hide HUD, return focus to trigger |
| `toggle()` | Toggle visibility |
| `updateBody(html)` | Replace body contents; re-detects header/footer |
| `updateSizeAndPosition()` | Recalculate position and orientation |
| `submit()` | Trigger submit event |
| `destroy()` | Remove HUD and shade from DOM |

### Events

| Event | When |
|-------|------|
| `show` | After HUD becomes visible |
| `hide` | After HUD is hidden |
| `submit` | When the HUD form is submitted |
| `updateSizeAndPosition` | After repositioning |

### Structure

The HUD creates this DOM structure:
```html
<div class="hud">
  <div class="tip tip-top"></div>  <!-- pointer, class varies by orientation -->
  <form class="body">
    <div class="hud-header">...</div>       <!-- auto-detected from body content -->
    <div class="main-container">
      <div class="main">...body content...</div>
    </div>
    <div class="hud-footer">...</div>       <!-- auto-detected from body content -->
  </form>
</div>
```

Elements with class `hud-header` or `hud-footer` inside body content are automatically extracted and placed outside the scrollable main area.

### Smart Positioning

HUD evaluates viewport clearance in all four directions and picks the first orientation from the `orientations` array that has enough room. Falls back to the direction with the most clearance.

---

## DisclosureMenu

Accessible popover menu triggered by a button. Used extensively in Craft's CP for action menus.

### Constructor

```javascript
// Trigger must have aria-controls pointing to the menu container ID
var menu = new Garnish.DisclosureMenu(this.$trigger, {
  position: null,       // 'below' to force below, null for auto
  windowSpacing: 5,
  withSearchInput: false,
});
```

### Required Markup

```html
<button aria-controls="my-menu-id" aria-expanded="false" data-disclosure-trigger>
  Actions
</button>
<div id="my-menu-id" class="menu menu--disclosure">
  <ul class="padded">
    <li><button class="menu-item" type="button">Edit</button></li>
    <li><a class="menu-item" href="/delete">Delete</a></li>
  </ul>
</div>
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `position` | `null` | `'below'` forces below trigger, `null` for smart positioning |
| `windowSpacing` | `5` | Minimum gap to viewport edge |
| `withSearchInput` | `false` | Add a search input to filter items (also activates via `data-with-search-input` attribute) |

### Key Methods

| Method | Description |
|--------|-------------|
| `show()` | Open menu, add UI layer, focus first item |
| `hide()` | Close menu, remove UI layer, return focus to trigger |
| `addItem(config, ul, prepend)` | Programmatically add a menu item |
| `addItems(items, ul)` | Add multiple items |
| `addGroup(heading, addHrs, before)` | Add a new `<ul>` group with optional heading |
| `addHr(before)` | Add a horizontal rule separator |
| `removeItem(el)` | Remove an item and clean up empty groups |
| `showItem(el)` / `hideItem(el)` | Toggle item visibility |
| `toggleItem(el, show)` | Toggle with optional explicit state |
| `createItem(config)` | Create a menu item `<li>` from a config object |
| `hasVisibleItems()` | Returns whether any items are visible |
| `focusElement(component)` | Move focus: `'prev'`, `'next'`, or a DOM element |
| `isExpanded()` | Check if menu is open |
| `destroy()` | Clean up |

### Item Config Object

```javascript
menu.addItem({
  label: 'Edit Entry',          // Text label
  // OR: html: '<em>Bold</em>', // HTML label
  icon: 'pencil',               // data-icon value, or Element/Function
  iconColor: 'blue',            // CSS class for icon color
  url: '/admin/entries/123',    // Makes it a link (type: 'link')
  type: 'button',               // 'button' (default) or 'link'
  selected: false,              // Add .sel class
  destructive: false,           // Add .error class + data-destructive
  disabled: false,              // Add .disabled class
  hidden: false,                // Start hidden
  description: 'Edit this',    // Small description text below label
  status: 'live',              // Status indicator dot
  action: 'entries/save',      // Craft action for formsubmit
  params: { entryId: 123 },    // Action params
  confirm: 'Are you sure?',    // Confirmation dialog
  redirect: 'entries',         // Redirect after action
  attributes: { 'data-x': 1 },// Additional HTML attributes
  onActivate: function (el) {}, // Click/activate handler
  callback: function (el) {},   // Alias for onActivate
});
```

### Events

| Event | When |
|-------|------|
| `beforeShow` | Before the menu opens |
| `show` | After the menu is visible |
| `hide` | After the menu is hidden |

### Keyboard Navigation

- Arrow Up/Down: Move focus between items
- Arrow Left/Right: Same as Up/Down
- Tab/Shift+Tab: Move focus in/out of menu, back to trigger
- Escape: Close menu, return focus to trigger
- Type-ahead: Typing characters focuses the first matching item (auto-clears after 1s)
- Search input (when enabled): Filters items by text match

### Search Input

When `withSearchInput: true` (or `data-with-search-input` attribute on container), a search field is prepended. Typing filters `<li>` items by text content and updates group/hr visibility.

---

## MenuBtn

Button that opens a `CustomSelect` dropdown menu. Used for Craft's select-style dropdowns.

### Constructor

```javascript
var menuBtn = new Garnish.MenuBtn(this.$btn, this.menu, {
  menuAnchor: null,
  onOptionSelect: function (option) { },
});

// Or auto-detect menu (next .menu sibling)
var menuBtn = new Garnish.MenuBtn(this.$btn);
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `menuAnchor` | `null` | Element to position menu against (defaults to button) |
| `onOptionSelect` | `$.noop` | Callback when an option is selected |

### Key Methods

| Method | Description |
|--------|-------------|
| `showMenu()` | Open the dropdown |
| `hideMenu()` | Close the dropdown |
| `enable()` / `disable()` | Toggle button state |
| `focusOption($option)` | Set visual focus on an option |
| `moveFocusUp(dist)` / `moveFocusDown(dist)` | Navigate options |
| `destroy()` | Destroy button and its CustomSelect |

### Events

| Event | When |
|-------|------|
| `optionSelect` | An option was selected. `ev.option` is the selected element. |

### ARIA

Sets on the button: `role="combobox"`, `aria-controls`, `aria-haspopup="listbox"`, `aria-expanded`.

### Keyboard

- Space/Enter/Down: Open menu, focus selected option
- Up/Home: Open menu, focus first option
- End: Open menu, focus last option
- When open: Up/Down/PageUp/PageDown navigate, Enter/Space select, Tab selects and moves focus
- Type-ahead search: Characters match option text

---

## CustomSelect

Dropdown listbox menu positioned relative to an anchor element. The underlying component for MenuBtn.

### Constructor

```javascript
var menu = new Garnish.CustomSelect($container, {
  anchor: this.$btn,
  windowSpacing: 5,
  onOptionSelect: function (option) { },
});
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `anchor` | `null` | Element to position against |
| `windowSpacing` | `5` | Minimum gap to viewport edge |
| `onOptionSelect` | `$.noop` | Callback on option selection |

### Key Methods

| Method | Description |
|--------|-------------|
| `show()` | Show menu, position relative to anchor, add UI layer |
| `hide()` | Hide with fade-out, remove UI layer |
| `selectOption(option)` | Trigger selection, fire event, hide |
| `addOptions($options)` | Register new option elements |

### Events

| Event | When |
|-------|------|
| `show` | Menu shown |
| `hide` | Menu hidden |
| `optionselect` | Option selected. `ev.selectedOption` is the element. |

### ARIA

Container gets `role="listbox"`. Each `<li>` wrapper gets `role="option"` and `aria-selected`. MutationObservers sync `aria-selected` with the `.sel` and `.hover` CSS classes.

**Note:** `Garnish.Menu` is a deprecated alias for `CustomSelect`.

---

## SelectMenu

Extends CustomSelect. When an option is selected, the button text updates to match.

```javascript
var selectMenu = new Garnish.SelectMenu($container, {
  anchor: this.$btn,
});
```

Inherits all CustomSelect settings and methods. Adds automatic button label sync on `optionselect`.

---

## Select

Selection interface for lists of items. Handles single/multi selection, keyboard navigation, shift-click ranges, and Ctrl+A.

### Constructor

```javascript
var select = new Garnish.Select($container, $items, {
  selectedClass: 'sel',
  multi: true,
  allowEmpty: true,
  vertical: true,
  handle: '.item-handle',
  checkboxMode: false,
  checkboxClass: 'checkbox',
  makeFocusable: false,
  onSelectionChange: function () { },
});
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `selectedClass` | `'sel'` | CSS class applied to selected items |
| `checkboxClass` | `'checkbox'` | CSS class for checkbox elements |
| `multi` | `false` | Allow multiple selection |
| `allowEmpty` | `true` | Allow deselecting all items |
| `vertical` | `false` | Items arranged vertically (for keyboard nav) |
| `horizontal` | `false` | Items arranged horizontally |
| `handle` | `null` | Selector, function, or element for selection handle |
| `filter` | `null` | Filter function or selector for valid click targets |
| `checkboxMode` | `false` | Checkbox-style toggle (Ctrl not required) |
| `makeFocusable` | `false` | Add `tabindex="0"` to focused item |
| `waitForDoubleClicks` | `false` | Delay deselection to distinguish double-clicks |
| `onSelectionChange` | `$.noop` | Callback |

### Key Methods

| Method | Description |
|--------|-------------|
| `selectItem($item, focus, preventScroll)` | Select a single item |
| `selectAll()` | Select all items (multi mode) |
| `selectRange($item)` | Select range from first to item (shift-click) |
| `deselectItem($item)` | Deselect a single item |
| `deselectAll()` | Deselect all items |
| `toggleItem($item)` | Toggle selection state |
| `isSelected($item)` | Check if item is selected |
| `addItems(items)` | Register new items |
| `removeItems(items)` | Unregister items |
| `getSelectedItems()` | Get jQuery collection of selected items |
| `getTotalSelected()` | Count of selected items |
| `focusItem($item)` | Set focus on an item |
| `resetItemOrder()` | Recalculate item order from DOM |

### Events

| Event | When |
|-------|------|
| `selectionChange` | Selection changed (debounced via rAF) |
| `focusItem` | An item received focus. `ev.item` is the jQuery element. |

### Keyboard Navigation

- Arrow keys: Navigate items (respects vertical/horizontal/grid layout)
- Space: Toggle selection on focused item
- Shift+Arrow: Select range
- Ctrl+A: Select all
- Ctrl+Arrow: Jump to furthest item in direction

---

## ContextMenu

Right-click context menu built from option arrays.

### Constructor

```javascript
var contextMenu = new Garnish.ContextMenu(this.$element, [
  { label: 'Edit', onClick: function (ev) { /* ev.currentTarget = right-clicked element */ } },
  '-',  // separator — creates a new <ul> group with <hr>
  { label: 'Delete', onClick: function (ev) { } },
], {
  menuClass: 'menu',
});
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `menuClass` | `'menu'` | CSS class for the menu container |

### Key Methods

| Method | Description |
|--------|-------------|
| `showMenu(ev)` | Show at cursor position (called on right-click/mousedown) |
| `hideMenu()` | Hide the menu |
| `enable()` | Bind contextmenu/mousedown listeners |
| `disable()` | Unbind listeners |
| `buildMenu()` | Build DOM from options array (lazy, on first show) |

### Behavior

- Listens for `contextmenu` and `mousedown` (right-click) events on the target
- Positions at cursor location (`ev.pageX`, `ev.pageY`)
- `onClick` callback is called with `this` set to the right-clicked element and `ev.currentTarget` also set to it
- Uses UiLayerManager for ESC key handling
- Use `'-'` in the options array to create a separator between option groups

---

## See Also

- `class-system.md` — Garnish.Base (all widgets extend this), event system, addListener, destroy lifecycle
- `utilities.md` — UiLayerManager (layer stack for modals/menus), ARIA helpers, focus trapping, key constants
- `drag-system.md` — DragSort and DragDrop (often used alongside Select for reorderable element lists)
- `integration.md` — How to register asset bundles, Twig markup for DisclosureMenu/MenuBtn, Craft.initUiElements
