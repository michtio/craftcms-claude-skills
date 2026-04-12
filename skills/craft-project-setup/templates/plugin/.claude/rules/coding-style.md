# Coding Style

- PHPDocs on every class, method, and property. No exceptions.
- `@author {{authorName}}` and `@since` tags at the bottom of every docblock, after a blank line.
- `@throws` chains: document every exception including uncaught from called methods.
- `@inheritdoc` only when parent has a meaningful doc comment.
- Section headers with `// =========================================================================` on every class.
- Private methods/properties prefixed with underscore: `_myMethod()`, `$_myProp`.
- Imports alphabetical, grouped: PHP → Craft → Plugin → Third-party.
- `match` over `switch`. Early returns over `else`. Curly brackets always.
- `declare(strict_types=1)` is NOT used in plugin source files.
- `DateTimeHelper` in elements/queries, `Carbon` in services. Never mix in same class.
