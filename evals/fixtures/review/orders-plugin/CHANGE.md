# Change under review (1.1.0)

New in this change, against 1.0.0:

- `src/controllers/ExportController.php` (new)
- `src/services/OrdersService.php`: `exportRows()` (new method)
- `src/migrations/m261120_000000_add_exported_at.php` (new)
- `src/templates/export/_csv.twig` (new)
- `src/controllers/NotesController.php`: `actionSave()` now reads `noteId` before the permission check (moved line)

Unchanged: `src/Plugin.php`, `src/records/`, `composer.json`.
