# Architecture

- Business logic in services. Controllers are thin: validate, delegate, respond.
- Element operations through services, not controllers or helpers.
- Services live in `src/services/` and register via `src/services/ServicesTrait.php`: `static config()` returns the `components` array, typed `getX(): X` accessors wrap `$this->get('x')` with `assert($component instanceof X)` to narrow Yii's `?object` return for PHPStan level 8. The trait owns the `@property X $name` tags on its docblock — never duplicate them on the main plugin class. Adopt the trait once a plugin has 2+ services.
- Event listeners, URL rules, and plugin lifecycle overrides live in `src/base/PluginTrait.php`. The main plugin class is a thin shell — `use ServicesTrait; use PluginTrait;` plus an orchestrating `init()`. Its class-level docblock describes what the plugin does, not the services it registers (drift-prone — the trait owns that map).
- Abstract base classes for shared controller structure. Traits for cross-cutting concerns.
- `MemoizableArray` for cached service lookups — always reset on data changes.
- Project config for entities that sync across environments. Runtime data stays in DB only.
- Events for extensibility: fire before/after events on all significant operations.
- `addSelect()` not `select()` in `beforePrepare()` — never wipe Craft's base columns.
- `site('*')` in queue workers — workers run in primary site context.
- Scope element queries by owning context (site, section, owner) — never query globally without filters.
