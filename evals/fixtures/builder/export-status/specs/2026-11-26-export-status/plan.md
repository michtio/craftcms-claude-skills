---
id: PLAN-2026-11-26-export-status
prd: SPEC-2026-11-26-export-status
status: approved
approved_by: Acme
approved_on: 2026-11-26
---

# Plan: Filter the order export by status

## Slices

### S1: Status filter

- **Deliverable:** `ExportController::actionDownload()` reads an optional `status` body param and passes it to `OrdersService::exportRows()`, which adds a `status` condition when it is set.
- **Requirements:** R1
- **Layers:** `src/controllers/ExportController.php`, `src/services/OrdersService.php`.
- **Verification gate:** no DDEV project in this fixture: `git diff` shows only the two files; PHPDocs updated.
- **Size:** S
