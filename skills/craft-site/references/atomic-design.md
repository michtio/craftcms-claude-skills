# Atomic Design Methodology

> Brad Frost's hierarchical composition model for building user interfaces.
> Technology-independent — this is the thinking model, not the implementation.
> For the Craft CMS Twig implementation, see `atomic-patterns.md`.

## Documentation

- Atomic Design book (free): https://atomicdesign.bradfrost.com/
- Chapter 2 — the methodology: https://atomicdesign.bradfrost.com/chapter-2/
- Original blog post (2013): https://bradfrost.com/blog/post/atomic-web-design/
- Extending Atomic Design: https://bradfrost.com/blog/post/extending-atomic-design/

## Common Pitfalls

- Treating the five tiers as a build sequence — they're a mental model for
  holding abstraction levels simultaneously, not a manufacturing pipeline.
- Building atoms first and composing upward — start from the design, decompose
  downward. The atoms emerge naturally from the repeated patterns.
- Debating molecule vs organism classification endlessly — the boundary is
  intentionally fuzzy. If the debate blocks progress, the answer doesn't matter.
- Over-atomizing — not every HTML element needs its own atom. Create components
  for reusable visual treatments, not for every tag.
- Naming by context or content — "homepage-carousel" limits where it can live,
  "product-card" limits what can go inside. Name by visual treatment.
- Forcing every component into the hierarchy — some things are utilities,
  helpers, or layout primitives that don't fit the atom/molecule/organism model.

## What Atomic Design Is

Atomic design is a mental model for building user interfaces as interconnected
systems of components rather than as collections of pages. Brad Frost introduced
it in 2013, borrowing from chemistry: all matter in the universe reduces to a
finite set of atomic elements that combine into molecules, which combine into
organisms. Interfaces work the same way — a finite set of base UI elements
combines into progressively complex structures.

The methodology exists because the web industry was stuck thinking in "pages."
Teams scoped work as "a five-page website" when the web had become fluid,
responsive, and multi-device. Frost's guiding principle, from Stephen Hay:
"We're not designing pages, we're designing systems of components."

The specific tier labels (atoms, molecules, organisms, templates, pages) are
not the point. Frost confirmed in a 2025 Design Systems Collective interview
that he doesn't use his own terminology in the design systems he makes. What
endures is the principle: **UI should be understood
simultaneously as a cohesive whole and as a collection of composable parts
at every level of abstraction.**

## The Five Canonical Tiers

### Atoms

The foundational building blocks. HTML elements that can't be broken down
further without ceasing to be functional: form labels, inputs, buttons,
headings, images, icons. Each carries intrinsic properties (dimensions,
color, typography).

Atoms in isolation aren't very useful — a button with no context. But they
demonstrate all base styles at a glance and serve as the vocabulary of the
design system.

### Molecules

Relatively simple groups of atoms functioning together as a unit. Frost's
canonical example: a search form — a label atom, an input atom, and a button
atom combine into something with purpose. The label now defines the input.
The button now submits the form.

Molecules embody the single responsibility principle: do one thing and do it
well. They are simple, portable, and reusable — droppable anywhere their
function is needed.

### Organisms

Relatively complex compositions of molecules, atoms, and/or other organisms
that form distinct sections of an interface. A header organism might contain a
logo atom, a navigation molecule, and a search form molecule. A product grid
organism repeats the same product-card molecule.

Organisms provide context — they show smaller components in action and
represent complete, recognizable sections of a page.

### Templates

Page-level objects that place components into a layout and define the content
structure. They use placeholder content to demonstrate how organisms, molecules,
and atoms arrange spatially. Templates answer: "what is the underlying content
structure of this page type?"

### Pages

Specific instances of templates with real representative content. Pages are
what users actually see and stakeholders actually approve. They test the
resilience of the design system — how do patterns hold up with a 40-character
headline vs a 340-character one? With one cart item vs ten?

## The 5-to-3 Compression

In practice, most teams implement three component tiers, not five. Frost
himself endorsed this — the specific labels were never the point.

The compression works because **templates and pages map to infrastructure**,
not to the component system:

- Templates become the CMS template layer — layouts, page skeletons, content
  region definitions. This is architectural scaffolding, not a design system
  component.
- Pages become what the server renders at a URL — a route, a view, a specific
  instance populated with real content. The CMS handles this natively.

The resulting three-tier component library:

| Tier | Contains | Scale |
|------|----------|-------|
| **Atoms** | Base UI elements, design tokens applied | Single element |
| **Molecules** | Small functional groups of atoms | Reusable unit |
| **Organisms** | Complete interface sections | Page region |

Layout scaffolding and page-level routing live outside the component system —
they're the infrastructure that *consumes* components, not components themselves.

### Design Tokens as Subatomic Particles

Frost later positioned design tokens below atoms: colors, spacing values, font
stacks, breakpoints. A token like `color-brand-blue` is a critical UI ingredient
but isn't functional on its own — it needs to be applied to an atom to come alive.
This gives many teams a four-layer mental model: tokens → atoms → molecules →
organisms, with layout and routing handled separately.

## Core Principles

### Composability

Small components nest inside larger ones, like Russian nesting dolls, until
entire screens emerge. But this isn't sequential manufacturing. Frost quotes
Frank Chimero: design is "a dance of switching contexts" between the whole and
the parts. The parts influence the whole, and the whole influences the parts.

### Context-Agnostic Naming

The more agnostic a component name is, the more versatile and reusable it
becomes. Frost's technique: blur out the content inside a pattern so the team
focuses on structure, not semantics. Components named by visual treatment
("card," "media block," "carousel") travel freely across contexts. Components
named by location ("homepage-hero") or content ("product-card") are trapped.

### Plural Directories, Singular Files

Component libraries organize by **category** (plural) containing **components**
(singular). The directory is a collection — buttons, cards, heroes — while each
file inside is a single component or variant.

```
buttons/                  ← plural: the category (a collection of button components)
├── _button--props.twig   ← singular: one component's data interface
├── button--primary.twig  ← singular: one visual variant
├── button--secondary.twig
└── button--icon.twig

cards/                    ← plural
├── _card--props.twig     ← singular
├── card--blog.twig
└── card--callout.twig

heroes/                   ← plural
├── _hero--props.twig     ← singular
└── hero--primary.twig
```

This convention mirrors natural language: you go to the `buttons/` shelf to
find the `button--primary` component. It also avoids the ambiguity of a file
and its parent directory sharing the same name (`button/button.twig`).

The principle applies at every tier and to every directory in the component
system: `_atoms/texts/`, `_molecules/navigations/`, `_organisms/footers/`,
`_views/`, `_builders/`.

### Interface Segregation

Components don't know their parents. A search form molecule works identically
in a header organism, a sidebar organism, or a standalone page region. Components
depend on their own props/parameters — abstractions — not on the concrete
context that consumes them.

### Single Responsibility

Especially at the molecule tier: do one thing and do it well. Complex
molecules that handle validation, state, layout, and display are organisms
trying to pass as molecules. When a component accumulates responsibilities,
it's time to split.

### Simultaneous Abstraction and Concreteness

Frost calls this atomic design's biggest advantage: the ability to see an
interface broken down to its atomic elements and also see how those elements
combine into the final experience. The tiers are not workflow steps — they're
a lens for holding both views at once.

## The Classification Problem

The molecule-versus-organism boundary is intentionally fuzzy and the
methodology's most debated aspect. Is a card (image + heading + text + link)
a molecule or organism? Frost offers a heuristic — "if you break a component
down and get basic tags, it's a molecule" — but practitioners consistently
find this insufficient for edge cases.

A practical heuristic from trivago's pattern library: **atoms never nest atoms**.
Once you're composing atoms together or adding structural HTML around an atom,
it becomes a molecule. If a molecule reaches page-section scale (it represents a
distinct region like a header, footer, or hero), it's an organism.

When the classification debate blocks progress, it's a signal to stop debating
and pick one. The tier assignment matters less than the composition structure
being clear and consistent.

## The Decompose-Downward Workflow

A critical lesson from practitioners: **don't build atoms first and compose
upward.** Frost's colleague Dan Mall discovered this mistake early: "Rather
than starting out by building buttons and components, focus instead on building
flows and working backward from there."

The effective workflow:

1. **Start from the design** — a mockup, a wireframe, a sketch of a real page
2. **Identify the page sections** — these are candidate organisms
3. **Within each section, spot the repeated units** — these are candidate molecules
4. **Within each unit, identify the base elements** — these are the atoms
5. **Name everything by visual treatment**, not by content or context
6. **Build the atoms**, then compose molecules, then compose organisms

The atoms emerge from decomposition. They don't need to be invented in advance.

## Atomic Design Is Not

- **A build process.** The tiers are a mental model, not a manufacturing sequence.
- **A folder structure mandate.** `atoms/molecules/organisms/` is a common
  convention, not a requirement. Some teams use different names entirely.
- **A naming convention.** The chemistry metaphor opens the door to systematic
  thinking. You don't need to keep the vocabulary.
- **Technology-specific.** The principles apply to React, Twig, Vue, native
  mobile, email templates — any composable UI system.
- **A replacement for design.** It's a structural methodology, not a visual one.
  It says nothing about aesthetics, brand, or visual language.