# Component Inventory Methodology

> How to classify UI elements into tiers, name them, design their props,
> and decide when to promote project-specific components to the common library.
> For the underlying atomic design methodology, see `atomic-design.md`.

## Documentation

- Atomic Design book: https://atomicdesign.bradfrost.com/chapter-2/
- Craft CMS Twig templates: https://craftcms.com/docs/5.x/development/twig.html

## Common Pitfalls

- Over-atomizing — a `<p>` tag used once in a card body doesn't need a "paragraph" atom. Atoms are reusable visual treatments.
- Under-classifying — a "card" with hero image, nav links, form, and CTA section is an organism.
- Naming by data source — `entry-card`, `category-link`. Name the visual treatment, not the Craft element type.
- Props bloat — 15+ props means the component is doing too much. Split into children.
- Variant explosion — 5+ variants with minimal overlap are separate components sharing a name.
- Premature promotion — three project-specific versions that work are better than one premature abstraction.

## Three Tiers

| Tier | Scope | Usage |
|------|-------|-------|
| **Scaffold** | Ships with every project. Generated on setup. | Buttons, links, texts, images, icons, basic cards, navigation, hero, footer, builder. |
| **Common** | Documented patterns. Add when the design requires them. | Review cards, office cards, video heroes, secondary CTAs, feature lists. |
| **Project-Specific** | One-off components for a single project. | Job cards, sector grids, teambuilding sliders, event teasers. |

Scaffold is the canonical starting set. Common is the "add when needed" shelf.
Project-specific is everything else — follow naming conventions but don't
document exhaustively in the skill.

## Classification Decision Tree

When you encounter a new UI element, walk this tree. For the full methodology
behind these tiers, see `atomic-design.md`.

```
1. Is it a single HTML element (or thin wrapper) with no child components?
   ├── YES → Atom
   └── NO ↓

2. Does it compose multiple atoms into a reusable unit?
   ├── YES → Is it a full page section/region?
   │         ├── YES → Organism
   │         └── NO  → Molecule
   └── NO ↓

3. Does it control page structure (header/main/footer chrome)?
   ├── YES → Layout (goes in _boilerplate/_layouts/)
   └── NO ↓

4. Does it render a specific entry type or page composition?
   ├── YES → View (goes in _views/)
   └── NO ↓

5. Does it map Matrix/CKEditor blocks to components?
   └── YES → Builder (goes in _organisms/builders/)
```

### Common Classification Questions

**"Is a card an atom or molecule?"**
A card composes image + heading + text + link atoms. Multiple children = molecule.

**"Is a navigation an organism or molecule?"**
A simple link list (footer links, breadcrumbs) = molecule.
A full site navigation with dropdowns, mobile toggle, search = organism.
The boundary is page-region scale.

**"Where does a search form go?"**
Input + button composed: molecule. Full section with filters, results,
pagination: organism.

**"Is an icon an atom?"**
Yes. Single-purpose, no children, context-agnostic.

**"Is a rich text block an atom?"**
No — it's a molecule or organism depending on what it includes. A `<div>` with
Tailwind `prose` classes wrapping CKEditor output is a molecule (`content--prose`).
A full content section with heading + prose + CTA button is an organism.

## Naming Methodology

### Component Names

| Rule | Correct | Wrong |
|------|---------|-------|
| Name = visual treatment | `button--primary` | `hero-button`, `card-cta` |
| BEM double-dash for variants | `card--horizontal` | `card-horizontal`, `cardHorizontal` |
| Context-agnostic | `heading` | `hero-title`, `sidebar-heading` |
| Singular component, plural directory | `button.twig` in `buttons/` | `buttons.twig` in `button/` |
| Project-specific = domain noun | `card--job` | `card--go4jobs-teaser` |

See `atomic-design.md` for the full naming principles (context-agnostic naming,
plural directories / singular files).

### File Naming

```
_component--props.twig      ← Props base (underscore prefix, --props suffix)
component--variant.twig     ← Variant (no underscore, --variant suffix)
```

One props file per category, shared across all variants:

```
buttons/
├── _button--props.twig     ← Shared by ALL button variants
├── button--primary.twig
├── button--secondary.twig
├── button--tertiary.twig
├── button--icon.twig
└── button--hamburger.twig
```

### Category Directories

Always plural. Standard categories per tier:

**Atoms:** `buttons/`, `links/`, `texts/`, `images/`, `icons/`, `badges/`, `embeds/`, `svgs/`
**Molecules:** `cards/`, `contents/`, `ctas/`, `quotes/`, `media/`, `navigations/`
**Organisms:** `heroes/`, `grids/`, `builders/`, `navigations/`, `footers/`, `forms/`, `sliders/`, `callouts/`, `ctas/`

Add new categories when none of the above fit. Don't force a component into the
wrong category just because it exists.

## Props Design Methodology

### How to Design a Props Interface

1. **Start with content.** What does this component display?
   Each piece of content = a prop: `text`, `heading`, `content`, `image`, `url`.

2. **Add behavior props.** What varies at runtime?
   `type` (button submit/reset), `size` (text size class), `position` (icon placement).

3. **Derive, don't accept.** External link detection, target, rel — all derived
   from the URL. Never passed by the caller.

4. **Add `utilities`.** Every component accepts a `utilities` prop for additive
   Tailwind classes from the parent scope.

5. **Don't add variant props.** Visual variants = separate files via extends/block.
   Never a `variant: 'outline'` prop with conditionals.

### Prop Defaults Convention

| Type | Default | When to use |
|------|---------|-------------|
| String content | `''` or `null` | `text`, `heading`, `content` |
| Optional reference | `null` | `url`, `image`, `icon`, `button` |
| Enum string | Named default | `position: 'after'`, `size: 'text-base'` |
| Additive classes | `null` | `utilities` — always null default |
| Derived boolean | Computed | `external` — never in defaults, always computed |

### Standard Atom Props by Category

**Buttons** — `text`, `url`, `icon`, `position`, `size`, `type`, `label`, `utilities`
Plus derived: `external`, `target`, `rel`.

**Links** — `text`, `url`, `icon`, `active`, `utilities`
Plus derived: `external`, `target`, `rel`.

**Texts** — `content`, `tag` (element override), `utilities`

**Images** — `image` (Asset), `preset`, `alt`, `ratio`, `utilities`

**Icons** — `icon` (FA class string), `size`, `label`, `utilities`

**Badges** — `text`, `icon`, `utilities`

These are the scaffold defaults. Molecules and organisms define their own props
per variant — there's no universal molecule props pattern.

## Scaffold Component Guidelines

The scaffold ships with every project. These are the categories and typical
variant patterns — not an exhaustive list, because variants are design-driven.

### Atom Categories

| Category | Typical Scaffold Variants | Notes |
|----------|--------------------------|-------|
| `buttons/` | `--primary`, `--secondary`, `--tertiary`, `--icon`, `--hamburger` | Actions. HTML resolved from props. |
| `links/` | `--primary`, `--navigation`, `--logo`, `--breadcrumb` | Navigation. Always `<a>`. |
| `texts/` | `--h1` through `--h4`, `--prose`, `--standfirst` | Typography. `tag` prop overrides element. |
| `images/` | `--responsive` | One variant. Preset-driven. See `image-presets.md`. |
| `icons/` | `--fa` | FontAwesome. Decorative unless `label` provided. |
| `badges/` | `--primary` | Add more when design needs them. |
| `embeds/` | `--video` | Responsive iframe wrapper. |
| `svgs/` | `--logo` | Inline SVG. Always project-specific implementation. |

### Molecule Categories

| Category | Typical Scaffold Variants | Notes |
|----------|--------------------------|-------|
| `cards/` | `--blog`, `--callout` | Content teasers. Compose image + heading + text + link atoms. |
| `contents/` | `--prose`, `--heading` | Rich text compositions with optional heading/CTA. |
| `ctas/` | `--image`, `--text` | Call-to-action blocks. |
| `quotes/` | `--text`, `--image` | Blockquote with optional author photo. |
| `media/` | `--embed` | Responsive media wrapper around embed atom. |
| `navigations/` | `--breadcrumb`, `--footer`, `--language`, `--socials` | Simple link list compositions. No complex interactivity. |

### Organism Categories

| Category | Typical Scaffold Variants | Notes |
|----------|--------------------------|-------|
| `heroes/` | `--primary`, `--secondary` | Page header sections. Primary = with image, secondary = text-only. |
| `grids/` | Design-driven | Card grids. Variants match the card type they compose. |
| `builders/` | `--blocks`, `--content`, `--landing` | Matrix block renderers. One per builder field style. |
| `layouts/` | Design-driven | Structural embed skeletons. See `atomic-patterns.md` embed pattern. |
| `navigations/` | `--site`, `--primary`, `--mobile` | Complex nav with dropdowns, Alpine/DataStar interactivity. |
| `footers/` | `--primary` | Site footer. |
| `forms/` | `--primary` | Form wrapper (Formie or native). |
| `sliders/` | Design-driven | Carousels. Variants match content type. |

## When to Promote

Components start project-specific. Promote to common when:

1. **3+ projects** use functionally identical versions
2. **Props interfaces converge** — if each project needs different props, not ready
3. **No project-specific content** baked in — purely structural
4. **Variants are consistent** — same names mean the same thing

**Don't promote prematurely.** Three project-specific versions that work are
better than one premature abstraction that fits none of them.

## When to Add a Common Component

Common-tier components are documented patterns you pull in when the design calls
for them. Add them by:

1. Creating the files in the correct category directory
2. Following the same props/extends/block pattern as scaffold components
3. Using the `--{domain-noun}` naming convention for the variant

Examples of common-tier additions: `card--review` (testimonials), `hero--video`
(background video), `grid--spotlight` (featured + grid), `callout--tip`
(informational callout), `list--properties` (key-value pairs).

## Project-Specific Naming Convention

Follow `component--{domain-noun}`:

```
card--job.twig              ← Job listing teaser
card--sector.twig           ← Sector overview
hero--search.twig           ← Search-driven hero
grid--jobs.twig             ← Job listing grid
form--login.twig            ← Authentication form
navigation--account.twig    ← Authenticated user nav
```

The domain noun describes the content domain, not the project name.

## Audit Checklist

When reviewing an existing project's components:

1. **List every `{% include %}` call** — reveals actual component usage
2. **Group by visual similarity** — components that look the same should be the same
3. **Check for ambient variables** — any component reading non-prop variables needs refactoring
4. **Check for duplicate logic** — 80%+ identical code should share a base via extends/block
5. **Verify tier classification** — atoms with child includes = misclassified molecules
6. **Check naming** — context-specific names (`hero-button`) → rename to visual treatment (`button--primary`)
7. **Check `only`** — every include must use `only`, no exceptions