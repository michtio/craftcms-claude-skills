---
paths:
  - "src/migrations/**/*"
---

# Migration Safety

- Every step must be idempotent: check before INSERT, check column before ADD.
- `muteEvents = true` on `ProjectConfig::set()` inside migrations. Reset after.
- Never generate random UIDs when project config YAML already ships the UID from dev.
- Foreign keys: `CASCADE` for owned data, `SET NULL` for references, `RESTRICT` for protected.
- Use `null` for FK name — Craft generates deterministic names.
- Include `postDate` and `expiryDate` indexes on element tables.
- `TRUNCATE cache` to clear stale mutex locks on Craft Cloud after failed migrations.
- Test with `ddev craft up` locally before deploying.
