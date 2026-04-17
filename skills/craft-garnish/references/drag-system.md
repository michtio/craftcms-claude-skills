# Drag System — BaseDrag, Drag, DragSort, DragDrop, DragMove

## Source

- `src/web/assets/garnish/src/BaseDrag.js`
- `src/web/assets/garnish/src/Drag.js`
- `src/web/assets/garnish/src/DragSort.js`
- `src/web/assets/garnish/src/DragDrop.js`
- `src/web/assets/garnish/src/DragMove.js`

## Common Pitfalls

- Using DragSort without an axis constraint on a vertical list — set `axis: Garnish.Y_AXIS` to prevent horizontal jitter.
- Forgetting to call `addItems()` when new items are dynamically added — they won't be draggable.
- Not providing a `handle` selector — the entire item becomes the drag handle, blocking text selection and button clicks within.
- Using `removeDraggee: true` without an insertion element — there's no visual placeholder.
- Ignoring `ignoreHandleSelector` — by default, clicks on `input, textarea, button, select, .btn` within the handle don't initiate drag.

## Table of Contents

- [Class Hierarchy](#class-hierarchy)
- [BaseDrag](#basedrag)
- [Drag](#drag)
- [DragSort](#dragsort)
- [DragDrop](#dragdrop)
- [DragMove](#dragmove)

---

## Class Hierarchy

```
Garnish.Base
  └── BaseDrag       (mouse tracking, scroll handling, drag lifecycle)
        ├── Drag      (helper clones, visual feedback, draggee management)
        │     ├── DragSort   (reorder items in a list)
        │     └── DragDrop   (drag to drop targets)
        └── DragMove  (simple drag-to-reposition)
```

---

## BaseDrag

Low-level drag infrastructure. Tracks mouse position, detects drag start (minimum distance threshold), manages scroll-while-dragging, and fires lifecycle events.

### Constructor

```javascript
var drag = new Garnish.BaseDrag($items, {
  handle: '.drag-handle',
  axis: Garnish.Y_AXIS,
  onDragStart: function () { },
  onDrag: function () { },
  onDragStop: function () { },
});
```

### Settings (defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `minMouseDist` | `null` | Minimum px mouse must move to start drag (defaults to `BaseDrag.minMouseDist` = 1) |
| `handle` | `null` | CSS selector, function, or element for drag handle. If null, whole item is handle. |
| `axis` | `null` | Constrain to `Garnish.X_AXIS` or `Garnish.Y_AXIS`. Null = free movement. |
| `ignoreHandleSelector` | `'input, textarea, button, select, .btn'` | Clicks on matching elements within the handle don't initiate drag |
| `onBeforeDragStart` | `$.noop` | Before drag begins |
| `onDragStart` | `$.noop` | Drag started |
| `onDrag` | `$.noop` | Mouse moved during drag |
| `onDragStop` | `$.noop` | Drag ended |

### Key Properties

| Property | Description |
|----------|-------------|
| `dragging` | `boolean` — whether currently dragging |
| `mousedownX` / `mousedownY` | Initial mouse position |
| `mouseX` / `mouseY` | Current mouse position (axis-constrained) |
| `realMouseX` / `realMouseY` | Actual mouse position (ignoring axis constraint) |
| `mouseDistX` / `mouseDistY` | Distance from mousedown |
| `mouseOffsetX` / `mouseOffsetY` | Mouse offset from target item's top-left |
| `$targetItem` | The item being dragged |
| `$items` | All registered draggable items |

### Key Methods

| Method | Description |
|--------|-------------|
| `addItems(items)` | Register new draggable items |
| `removeItems(items)` | Unregister items |
| `removeAllItems()` | Unregister all items |
| `allowDragging()` | Override to conditionally prevent drag start |
| `getPrevItem(item)` | Get previous item in DOM order |
| `getNextItem(item)` | Get next item in DOM order |

### Events

| Event | When |
|-------|------|
| `beforeDragStart` | Mouse exceeded threshold, about to start |
| `dragStart` | Drag has begun |
| `drag` | Mouse moved during drag (every move) |
| `dragStop` | Mouse released, drag ended |

### Scroll While Dragging

When the mouse nears the edge of the scroll container (within 25px), BaseDrag automatically scrolls in that direction using `requestAnimationFrame`. Works with both `window` and nested scrollable containers.

---

## Drag

Extends BaseDrag. Creates "helper" clones of dragged elements that follow the cursor with a lag effect.

### Constructor

```javascript
var drag = new Garnish.Drag($items, {
  handle: '.drag-handle',
  axis: Garnish.Y_AXIS,
  removeDraggee: false,
  hideDraggee: true,
  helperOpacity: 1,
  helperBaseZindex: 1000,
  singleHelper: false,
  onDragStart: function () { },
  onDragStop: function () { },
});
```

### Settings (defaults, in addition to BaseDrag)

| Setting | Default | Description |
|---------|---------|-------------|
| `filter` | `null` | Function or selector to determine which items are dragged together |
| `singleHelper` | `false` | Create only one helper regardless of draggee count |
| `collapseDraggees` | `false` | Only show target item's helper, hide others |
| `removeDraggee` | `false` | Remove draggee from view entirely (use with insertion) |
| `hideDraggee` | `true` | Make draggee invisible (visibility: hidden) |
| `copyDraggeeInputValuesToHelper` | `false` | Copy form values to helper clone |
| `helperOpacity` | `1` | Opacity of helper clones |
| `moveHelperToCursor` | `false` | Center helper on cursor instead of offset position |
| `helper` | `null` | Function to customize helper element, or wrapper element |
| `helperBaseZindex` | `1000` | Base z-index for helpers |
| `helperLagBase` | `3` | Base lag divisor (higher = more lag) |
| `helperLagIncrementDividend` | `1.5` | Additional lag per helper index |
| `helperSpacingX` | `5` | Horizontal offset between stacked helpers |
| `helperSpacingY` | `5` | Vertical offset between stacked helpers |
| `onReturnHelpersToDraggees` | `$.noop` | After helpers animate back |

### Key Methods

| Method | Description |
|--------|-------------|
| `returnHelpersToDraggees()` | Animate helpers back to original positions |
| `fadeOutHelpers()` | Fade out and remove helpers |
| `setDraggee($draggee)` | Set which elements are being dragged |
| `appendDraggee($newDraggee)` | Add elements to current drag set |
| `findDraggee()` | Determine draggee based on filter setting |

### Events (in addition to BaseDrag)

| Event | When |
|-------|------|
| `returnHelpersToDraggees` | After helpers animate back to draggees |

### Helper System

When a drag starts, Drag clones each draggee element (adding `.draghelper` class), strips `name` attributes (to protect radio buttons), and positions them absolutely in `<body>`. Helpers follow the cursor with a configurable lag effect that creates a smooth, staggered animation for multi-element drags.

---

## DragSort

Extends Drag. Enables reordering items within a container by dragging.

### Constructor

```javascript
var dragSort = new Garnish.DragSort($items, {
  handle: '.move.icon',
  axis: Garnish.Y_AXIS,
  container: this.$container,
  magnetStrength: 1,
  insertion: $('<div class="insertionmarker"/>'),
  onSortChange: function () { },
  onInsertionPointChange: function () { },
});
```

### Settings (defaults, in addition to Drag)

| Setting | Default | Description |
|---------|---------|-------------|
| `container` | `null` | Container element — drag only reorders within this container. Cursor must be over it. |
| `insertion` | `null` | Insertion marker element or function. Placed where draggee will land. |
| `moveTargetItemToFront` | `false` | Move target item before other draggees in DOM |
| `magnetStrength` | `1` | Helper damping (1 = follows cursor exactly, higher values = more lag/resistance) |
| `onInsertionPointChange` | `$.noop` | Called when insertion position changes |
| `onSortChange` | `$.noop` | Called when sort order changes (on drop) |
| `canInsertBefore` | `() => true` | Callback to allow/deny insertion before an item |
| `canInsertAfter` | `() => true` | Callback to allow/deny insertion after an item |

### Key Methods (in addition to Drag)

| Method | Description |
|--------|-------------|
| `createInsertion()` | Create the insertion marker element |
| `canInsertBefore($item)` | Check if draggee can go before this item |
| `canInsertAfter($item)` | Check if draggee can go after this item |

### Events (in addition to Drag)

| Event | When |
|-------|------|
| `sortChange` | Sort order changed after drop |
| `insertionPointChange` | Insertion position changed during drag |

### How It Works

1. **dragStart**: Records original indexes, creates insertion marker, pre-calculates item midpoints
2. **drag**: Finds closest item to cursor via midpoint distance, moves draggee in DOM
3. **dragStop**: Removes insertion, compares new indexes to old — fires `sortChange` if order changed

Performance: For large lists (200+ items), only viewport-visible items are checked during drag.

---

## DragDrop

Extends Drag. Enables dragging items onto drop target areas.

### Constructor

```javascript
var dragDrop = new Garnish.DragDrop({
  dropTargets: $dropZones,           // jQuery collection or function returning elements
  activeDropTargetClass: 'active',
  onDropTargetChange: function ($activeDropTarget) {
    // $activeDropTarget is jQuery element or null
  },
});

// Add draggable items after construction
dragDrop.addItems($items);
```

Note: DragDrop's `init()` takes only `settings` (no `items` parameter). Add items via `addItems()` after construction.

### Settings (in addition to Drag)

| Setting | Default | Description |
|---------|---------|-------------|
| `dropTargets` | `null` | jQuery collection or function returning drop target elements |
| `activeDropTargetClass` | `'active'` | CSS class added to drop target when cursor is over it |
| `onDropTargetChange` | `$.noop` | Called when active drop target changes. Receives `$activeDropTarget` (jQuery or null). |

### Key Properties

| Property | Description |
|----------|-------------|
| `$dropTargets` | Resolved drop target elements |
| `$activeDropTarget` | Currently active drop target (jQuery) or null |

### How It Works

1. **onDragStart**: Resolves drop targets (evaluates function if `dropTargets` is a function)
2. **onDrag**: Hit tests cursor against all drop targets each frame. When the active target changes, removes `activeDropTargetClass` from old, adds to new, calls `onDropTargetChange`
3. **onDragStop**: Removes `activeDropTargetClass`. Check `this.$activeDropTarget` to see where the item was dropped.

---

## DragMove

Extends BaseDrag (not Drag). Simple drag-to-reposition — moves the element's CSS position to follow the cursor.

### Constructor

```javascript
var dragMove = new Garnish.DragMove(this.$element, {
  handle: '.drag-handle',
});
```

Used by Modal for draggable dialogs. No helpers, no clones — directly repositions the element.

### How It Works

On each `drag` event, sets the target element's `top` and `left` CSS properties to match mouse offset.

---

## See Also

- `class-system.md` — Garnish.Base (all drag classes extend this), addListener, destroy lifecycle
- `utilities.md` — Axis constants (`Garnish.X_AXIS`, `Garnish.Y_AXIS`), `requestAnimationFrame`, `hitTest`
- `ui-widgets.md` — Modal uses DragMove for draggable dialogs, Select often pairs with DragSort
- `integration.md` — How to set up drag interactions in Twig JS blocks and plugin asset bundles
