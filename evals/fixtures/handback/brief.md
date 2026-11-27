# Brief: S1 export status

Slice: S1
Project root: /work/orders-plugin
Craft version: 5.12.0
Gate commit: 3f2a9c1
Gate files: tests/Feature/ExportStatusTest.php
Pest command: ddev exec --dir /work/orders-plugin vendor/bin/pest --filter=ExportStatus

## R2

The export MUST include a status column.
AC2: Given an order with status shipped, when the CSV is exported, then the row has `shipped` in the status column.

## R5

The export MUST reject an unknown status filter.
AC5: Given the filter `status=bogus`, when the export runs, then it responds 400.

## Pointers

- skills/craftcms/references/pitfalls.md
- skills/craft-php-guidelines/SKILL.md

## Rules

- Never edit a gate file.
- Stop at a passing gate.
- At most 3 rounds.
