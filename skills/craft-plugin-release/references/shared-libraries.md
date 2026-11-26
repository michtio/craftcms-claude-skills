# Shared Libraries: Release Order and Runtime Blast Radius

When plugins share a library (an SDK package, a kit module), library releases interact with **already-released consumers** through their version constraints. "Additive" describes the API surface, not the runtime.

**Release the dependency first, verify Packagist serves it (p2, see SKILL.md, "Verifying Packagist"), then bump and release the consumer.** Tagging a consumer whose code needs an unreleased dependency guarantees red CI — and that is the *mild* version of what follows.

**An additive minor of a library can silently break released consumers.** The observed failure shape, worth checking for before any library release that touches schema:

1. The library adds a column and starts writing to it.
2. Consumers only reach that schema through **their own** migrations — the library has no migration track of its own (see below).
3. Every released consumer's caret constraint (`^1.2`) admits the new minor immediately, so anyone running `composer update` gets new code against old schema.
4. The library's write path wraps everything in `try { … } catch (Throwable $e) { Craft::warning(…) }` as "best-effort bookkeeping" — so the entire write fails on every request, silently, with one log line nobody reads.

The rules that fall out:

- Before releasing a library that adds schema, ask what a **released** consumer on a caret constraint does when it resolves the new minor **before** running any migration. If the answer is "breaks," the change isn't additive, whatever the API diff says.
- A best-effort `catch (Throwable)` around bookkeeping writes converts a schema mismatch into invisible data loss. When a library writes to a schema its consumers own the migrations for, that catch is the hazard, not the safety net.
- Where a consumer must ship a migration to receive a library change, **say so in the library's release notes.** A constraint bump alone changing nothing at runtime is deeply unobvious.

## Library-shipped Yii modules have no CLI migration track

`craft migrate/up --track=module:<handle>` fails with `Invalid migration track`. Craft's `MigrateController` resolves only `craft`, `content`, and `plugin:<handle>` tracks (plus an `EVENT_REGISTER_MIGRATOR` escape hatch that nothing wires up for you) — verified against `craftcms/cms` 5.10.12, `src/console/controllers/MigrateController.php:467`.

So a library-shipped module's migrations reach an install **only** when a consumer plugin runs them from its own dated migration:

```php
// In the consumer plugin's dated migration
\acme\kit\Kit::getInstance()->getMigrator()->up();
```

— and the consumer must also bump its own `schemaVersion`, or that dated migration never runs. Bumping the library constraint alone changes nothing at runtime; each consumer needs a migration + `schemaVersion` bump of its own.

