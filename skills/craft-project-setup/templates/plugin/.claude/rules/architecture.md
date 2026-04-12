# Architecture

- Business logic in services. Controllers are thin: validate, delegate, respond.
- Element operations through services, not controllers or helpers.
- Services extend `yii\base\Component`, registered via `static config()`.
- Abstract base classes for shared controller structure. Traits for cross-cutting concerns.
- `MemoizableArray` for cached service lookups — always reset on data changes.
- Project config for entities that sync across environments. Runtime data stays in DB only.
- Events for extensibility: fire before/after events on all significant operations.
- `addSelect()` not `select()` in `beforePrepare()` — never wipe Craft's base columns.
- `site('*')` in queue workers — workers run in primary site context.
- Scope element queries by owning context (site, section, owner) — never query globally without filters.
