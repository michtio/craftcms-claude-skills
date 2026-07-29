---
name: craft-garnish
description: "Garnish — Craft CMS's built-in JavaScript UI toolkit for the control panel. ALWAYS load when writing, editing, or reviewing JavaScript that runs in the Craft CP — plugin CP assets, custom field type JS, element index JS, CP webpack config, or code importing garnishjs / referencing window.Garnish. Also for CP accessibility, keyboard interactions, drag-sort, and CP JS memory issues. Triggers on: Garnish.Base.extend, this.base(), init, setSettings, addListener, on/off/trigger, destroy, garnishjs, GarnishAsset, CpAsset, webpack externals, CP JavaScript, Craft.* pattern, Garnish.Modal, HUD, DisclosureMenu, MenuBtn, CustomSelect, ContextMenu, Select, modal/HUD popover, BaseDrag, DragSort, DragDrop, DragMove, onSortChange/onOptionSelect/onSelectionChange, NiceText, CheckboxSelect, MixedInput, MultiFunctionBtn, ESC_KEY/RETURN_KEY, activate/textchange events, UiLayerManager, registerShortcut, trapFocusWithin/releaseFocusWithin/setFocusWithin, ARIA helpers, focus management, aria-modal, aria-hidden retained focus, inert attribute, focus trap, keyboard navigation CP, Craft.CP, Craft.Slideout, Craft.ElementEditor, Craft.sendActionRequest, CP memory leak, event listener cleanup, jQuery .on() in CP, custom slideout/overlay lifecycle, disable kills listeners, sidebar panel injected into the entry form, id-only inputs with no name attribute, host form swallows my fields, Enter key submits the entry form, lightswitch value in JS. Do NOT trigger for front-end JavaScript (Alpine, Vue, htmx) or Twig templates (craft-site)."
---

# Garnish — Craft CMS Control Panel JavaScript Toolkit

Reference for Garnish, Craft CMS's built-in JavaScript UI framework. Covers the class system, UI widgets, drag interactions, form components, accessibility helpers, and integration with Craft's CP.

This skill is scoped to **Garnish itself** — the JavaScript library at `src/web/assets/garnish/`. For PHP-side plugin development (elements, controllers, services), see the `craftcms` skill. For CP template markup that Garnish widgets attach to, see the `craftcms` skill's `cp.md` reference.

## Companion Skills — Load When Needed

- **`craftcms`** — Load when the task involves PHP asset bundle classes, plugin architecture, or CP template markup that Garnish widgets attach to. Skip for pure JavaScript refactoring, Garnish API questions, or JS-only tasks.
- **`craft-php-guidelines`** — Load only when editing PHP files (asset bundle classes, controllers that register JS). Skip for pure JS work.

## Documentation

- Garnish source: `src/web/assets/garnish/src/` in the Craft CMS repository
- No official external documentation exists — this skill IS the documentation.

Use `WebFetch` on Craft's class reference (https://docs.craftcms.com/api/v5/) when looking up PHP-side asset bundle registration.

## Common Pitfalls (Cross-Cutting)

- Using jQuery `.on()` directly instead of `this.addListener()` — listeners added via jQuery won't auto-clean on `destroy()`, causing memory leaks.
- Forgetting `this.base()` when overriding `destroy()` — parent cleanup (listener removal, event teardown) gets skipped.
- Using `click` instead of `activate` event on non-`<button>` elements — `activate` handles both click and keyboard (Space/Enter), making the UI accessible.
- Fighting `UiLayerManager` by binding ESC directly — use `Garnish.uiLayerManager.registerShortcut(Garnish.ESC_KEY, callback)` so escape routes through the layer stack correctly.
- Magic key code numbers instead of `Garnish.ESC_KEY`, `Garnish.RETURN_KEY`, etc. — constants are self-documenting and consistent.
- Instantiating Garnish widgets before the DOM is ready — Garnish requires jQuery and all dependencies loaded first; in plugin assets, rely on `CpAsset` dependency chain.
- Not calling `destroy()` when removing widgets — orphaned listeners accumulate, especially in slideouts and live preview where DOM is repeatedly created/destroyed.
- Importing Garnish into webpack bundles instead of using the external — `import Garnish from 'garnishjs'` resolves to `window.Garnish` via webpack externals; bundling it duplicates 134KB.
- Giving `name` attributes to inputs in a panel injected into another form (an entry-edit sidebar panel, a CP template hook) — the host form serializes them on save and your plugin's values are silently swallowed. Inputs are id-only, your JS reads them by id and posts to your own endpoint, and an Enter-key guard keeps the host form from submitting. See `integration.md` (Panels Injected Into Another Form).
- Using deprecated `Garnish.Menu` instead of `Garnish.CustomSelect` — `Menu` is an alias kept for BC only.
- Using deprecated `Garnish.escManager` or `Garnish.shortcutManager` instead of `Garnish.uiLayerManager` — the newer manager provides layer-aware keyboard routing that respects the modal/menu stack.

## Reference Files

Read the relevant reference file(s) for your task. Multiple files often apply together.

**Task examples:**
- "Create a modal dialog in a plugin's CP JS" → read `class-system.md` + `ui-widgets.md`
- "Add drag-to-reorder to a custom field type" → read `drag-system.md` + `class-system.md`
- "Build a custom CP widget class" → read `class-system.md` + `integration.md`
- "Add a disclosure menu to a CP template" → read `ui-widgets.md` + `integration.md`
- "Handle keyboard events in CP JavaScript" → read `utilities.md` + `class-system.md`
- "Create an inline editor HUD" → read `ui-widgets.md` (HUD section)
- "Make a selection interface for elements" → read `ui-widgets.md` (Select section)
- "Set up a plugin's webpack config for Garnish" → read `integration.md`
- "Custom element index class isn't loading" → read `integration.md` (Element Index JS Loading)
- "Load element index JS with Vite" → read `integration.md` (Element Index JS Loading — Vite doesn't work for element index classes)
- "Add ARIA attributes to a custom modal" → read `utilities.md` (ARIA & Focus section)
- "Build a custom slideout/overlay/launcher on Garnish.Base" → read `ui-widgets.md` (Building a custom overlay/slideout) + `class-system.md` (Enable / Disable) + `utilities.md` (ARIA & Focus)
- "My launcher button only works once / 'Blocked aria-hidden' warning" → read `class-system.md` (Enable / Disable) + `utilities.md` (Closing an overlay: move focus OUT before hiding)
- "Understand how Craft.CP extends Garnish" → read `integration.md` + `class-system.md`
- "Add an interactive panel to an entry edit screen's sidebar from a plugin" → read `integration.md` (Panels Injected Into Another Form) + the `craftcms` skill's `cp-ui-patterns.md` for the markup
- "My panel's fields disappear when the entry is saved / Enter submits the entry form" → read `integration.md` (Panels Injected Into Another Form)
- "Build a multi-state submit button" → read `integration.md` (Form Widgets section)
- "Add auto-growing textarea behavior" → read `integration.md` (Form Widgets section)

| Reference | Scope |
|-----------|-------|
| `references/class-system.md` | Garnish.Base, inheritance (extend/init/base), events (on/off/trigger), listeners (addListener/removeListener), settings, namespacing, enable/disable, destroy lifecycle |
| `references/ui-widgets.md` | Modal, HUD, DisclosureMenu, MenuBtn, SelectMenu, CustomSelect, ContextMenu, Select — constructor args, settings/defaults, methods, events, ARIA behavior |
| `references/drag-system.md` | BaseDrag, Drag, DragSort, DragDrop, DragMove — class hierarchy, settings/defaults, events, helper system, insertion points, scroll handling |
| `references/utilities.md` | Garnish namespace object, key constants, custom jQuery events (activate, textchange, resize), ARIA/focus management, geometry/hit testing, animation, form helpers, detection |
| `references/integration.md` | GarnishAsset PHP bundle, webpack externals, loading sequence, Craft.* class pattern, Twig JS blocks, form widgets (NiceText, CheckboxSelect, MultiFunctionBtn, MixedInput) |
