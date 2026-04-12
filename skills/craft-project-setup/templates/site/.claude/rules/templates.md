# Template Conventions

- Atomic design: atoms → molecules → organisms. Components named by visual treatment, never by parent context.
- Every `{% include %}` uses `only`. No exceptions — prevents invisible variable coupling.
- `??` for null handling by default. `???` only if `nystudio107/craft-empty-coalesce` or `nystudio107/craft-seomatic` is installed.
- `.eagerly()` on every relational field access inside loops.
- `{% include '_builders/' ~ block.type.handle ignore missing only %}` for Matrix rendering.
- Props via `collect({})`, classes via named-key collections.
- Single descriptive words for variable names: `heading`, `image`, `button`. No camelCase.
- `{%-` and `-%}` whitespace control in low-level components.
- No macros for UI components — use includes with `only`.
- No hardcoded content that should come from fields.
