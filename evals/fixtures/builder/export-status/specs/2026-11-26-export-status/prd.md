---
id: SPEC-2026-11-26-export-status
title: Filter the order export by status
status: approved
owner: Acme
approved_by: Acme
approved_on: 2026-11-26
---

# Filter the order export by status

## Requirements

- **R1** The export download MUST accept an optional `status` body parameter and, when given, export only orders with that status. (MUST)

## Acceptance criteria

- **AC1 (R1)** Given orders with statuses `paid` and `pending`, when the export is posted with `status=paid`, then only paid orders are in the CSV.
- **AC2 (R1)** Given no `status` parameter, when the export is posted, then every order of the customer is exported, as before.

## Open questions

None.
