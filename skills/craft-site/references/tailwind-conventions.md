# Tailwind Conventions Reference

> How Tailwind CSS classes are composed and managed in Twig templates.
> Assumes Tailwind CSS — adapt class patterns to your CSS framework.
> The architectural patterns (named keys, additive utilities) are framework-agnostic.

## Documentation

- Tailwind CSS v4: https://tailwindcss.com/docs
- CSS custom properties: https://developer.mozilla.org/en-US/docs/Web/CSS/--*

## Common Pitfalls

- Hardcoded colors — never `bg-yellow-600`. Always `bg-brand-accent`. Colors
  come from tokens (see `design-tokens.md` in the `tailwind-v4` skill).
- Flat class strings — never `class="flex items-center bg-blue-500 ..."`.
  Always named-key collections.
- Overriding via utilities — `utilities` is additive. Override via named-slot
  merge.
- Duplicate classes — two conflicting classes on one element. Named keys
  prevent this by enforcing single occupancy per style concern.
- Missing responsive key — breakpoint classes mixed into other slots. Keep
  them in `responsive` or modifier-specific keys.
- Using margins between siblings instead of `gap` — prefer `gap-*` on the
  flex/grid parent over individual `mb-*` on children. Fewer classes, no
  last-child edge case.
- Missing dark mode variants when the project uses them — if existing
  components use `dark:`, new components must too.

## Table of Contents

- [Named-Key Collections](#named-key-collections)
- [Class Conflict Prevention](#class-conflict-prevention)
- [Spacing Preference](#spacing-preference)
- [Dark Mode (Variant-Based)](#dark-mode-variant-based)
- [craft-tailwind Plugin (Future)](#craft-tailwind-plugin-future)

## Named-Key Collections

Classes are built using `collect({})` with **named keys per style concern**.
This is the primary mechanism for preventing class conflicts and maintaining
readability.

```twig
{%- set classes = collect({
    layout: 'inline-flex items-center group w-fit',
    color: 'bg-brand-accent text-brand-on-accent',
    font: 'font-heading font-bold',
    size: props.get('size'),
    hover: 'hover:bg-brand-accent-hover',
    focus: 'focus:ring-2 focus:ring-brand-focus focus:ring-offset-1 focus:outline-none',
    radius: 'rounded-lg',
    spacing: 'py-2 px-4 gap-2',
    transition: 'transition-colors duration-200',
    utilities: props.get('utilities'),
}) -%}
```

### Standard Key Names

Use these consistently across all components:

| Key | Contains | Examples |
|-----|----------|---------|
| `layout` | Display, flex, grid, position, overflow | `flex`, `grid`, `relative`, `overflow-hidden` |
| `color` | Background, text color | `bg-brand-accent`, `text-brand-on-accent` |
| `font` | Font family, weight | `font-heading`, `font-bold` |
| `size` | Font size, width, height | `text-base`, `w-full`, `h-64` |
| `hover` | Hover states | `hover:bg-brand-accent-hover` |
| `focus` | Focus ring, outline | `focus:ring-2`, `focus:ring-brand-focus` |
| `radius` | Border radius | `rounded-lg`, `rounded-br-2xl` |
| `spacing` | Padding, margin, gap | `py-2 px-4`, `gap-4` |
| `border` | Border width, color, style | `border`, `border-brand-muted` |
| `shadow` | Box shadow | `shadow-md`, `hover:shadow-lg` |
| `transition` | Transition, animation | `transition-colors`, `duration-200` |
| `responsive` | Breakpoint-specific overrides | `lg:grid-cols-2`, `md:px-8` |
| `utilities` | Additive extension from caller | `props.get('utilities')` |

### The `utilities` Slot

`utilities` is the **extension point** — it adds classes that don't exist in
the base, like a margin or border where there wasn't one. It is **not** for
overriding existing slots.

```twig
{# Caller adds margin — extending, not overriding #}
{% include '_atoms/texts/text--h2' with {
    content: 'Section Title',
    utilities: 'mt-12 mb-4',
} only %}
```

To override a style concern, override the named slot on the collection:

```twig
{# Inside a variant that needs different colors #}
{%- set classes = classes.merge({ color: 'bg-brand-primary text-brand-on-primary' }) -%}
```

### Rendering

```twig
{# As a class attribute value #}
class="{{ classes.implode(' ') }}"

{# Inside {% tag %} #}
{%- tag element with {
    class: classes.implode(' '),
} -%}

{# Inside attr() #}
<div{{ attr({ class: classes.implode(' ') }) }}>
```

## Class Conflict Prevention

### Why Order Doesn't Matter

HTML class attribute order is **irrelevant** for CSS specificity.
`class="bg-red-500 bg-blue-500"` does NOT reliably resolve to blue. The winner
is determined by Tailwind's generated CSS stylesheet order — which is internal
and not intuitive.

**Rule:** Never put two conflicting classes on the same element. Named keys
enforce single-occupancy per concern — that's the prevention mechanism.

### Tailwind v4 Cascade Layers

Tailwind v4 uses native CSS `@layer`. Utilities always beat components. But
**within** the utilities layer, same-specificity conflicts still resolve by
stylesheet order. Named-key collections prevent this.

For the full cascade layer model, see `cascade-layers.md` in the `tailwind-v4`
skill.

## Spacing Preference

Prefer `gap` utilities on flex/grid parents over individual margins on children.
Gap is cleaner — no last-child edge cases, fewer classes, spacing defined once
on the container.

```twig
{# Correct — gap on the parent #}
<div class="flex flex-col gap-4">
    <div>Item 1</div>
    <div>Item 2</div>
    <div>Item 3</div>
</div>

{# Avoid — margins on each child #}
<div class="flex flex-col">
    <div class="mb-4">Item 1</div>
    <div class="mb-4">Item 2</div>
    <div>Item 3</div>
</div>
```

Use margins only for one-off spacing adjustments (e.g., `mt-8` on a section
heading) or when spacing varies between specific children.

## Dark Mode (Variant-Based)

For projects **without** the three-tier token system (single-brand, simple
sites), use Tailwind's `dark:` variant utilities directly.

Dark variants go in the same named key as their light counterpart:

```twig
{%- set classes = collect({
    color: 'bg-brand-surface text-brand-heading dark:bg-brand-surface-dark dark:text-brand-heading-dark',
    border: 'border-brand-muted dark:border-brand-muted-dark',
}) -%}
```

### Decision: Token-Based vs Variant-Based

| Approach | When to use |
|----------|-------------|
| **Token-based** (CSS custom properties switch) | Project uses multi-brand theming with CSS tokens. Dark mode = another token set. No `dark:` classes needed. See `design-tokens.md` in the `tailwind-v4` skill. |
| **Variant-based** (`dark:` utilities) | Single-brand project or project without CSS token architecture. Use `dark:` directly in class collections. |

Don't mix both approaches in the same project.

## craft-tailwind Plugin (Future)

The `craft-tailwind` plugin will provide:

- `craft.tailwind.merge()` — server-side class deduplication
- `craft.tailwind.classes({})` — named-slot class builder with auto-merge
- Tailwind v3 + v4 auto-detection

Until the plugin exists, named-key collections are the primary mechanism.
