# Architecture

- Business logic in services. Controllers are thin: validate, delegate, respond.
- Element operations through services, not controllers or helpers.
- Services live in `src/services/` and register via a `ServicesTrait`: `static config()` returns the `components` array, typed `getX(): X` accessors wrap `$this->get('x')`. No `setComponents()` call in `init()`.
- Event listeners, URL rules, and plugin lifecycle overrides live in `src/base/PluginTrait.php`. The main plugin class is a thin shell — `use ServicesTrait; use PluginTrait;` plus an orchestrating `init()`.
- Abstract base classes for shared controller structure. Traits for cross-cutting concerns.
- `MemoizableArray` for cached service lookups — always reset on data changes.
- Project config for entities that sync across environments. Runtime data stays in DB only.
- Events for extensibility: fire before/after events on all significant operations.
- `addSelect()` not `select()` in `beforePrepare()` — never wipe Craft's base columns.
- `site('*')` in queue workers — workers run in primary site context.
- Scope element queries by owning context (site, section, owner) — never query globally without filters.
