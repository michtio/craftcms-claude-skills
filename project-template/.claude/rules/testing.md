---
paths:
  - "tests/**/*"
---

# Testing Conventions

- Pest exclusively. Never PHPUnit class syntax.
- Descriptive names with `it()`: `it('prevents duplicate bulk operations')`.
- One assertion per test where practical.
- Factories for all elements and models.
- Mirror source path: `src/services/Instances.php` → `tests/services/InstancesTest.php`.
- Always `->site('*')` in test element queries to avoid site-context issues.
- Run with `ddev craft pest/test`.
- Reference implementation: `putyourlightson/craft-blitz` tests.
