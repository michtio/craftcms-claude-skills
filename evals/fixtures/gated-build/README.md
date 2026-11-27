# Hello

A minimal Craft 5.12 plugin, used as a fixture for the gated-build evals. It is not a real plugin.

The fixture has no DDEV project and no Craft install. `vendor/bin/pest` is a small sh stand-in that runs no PHP: it decides red or green from marker comments in the tests (see `CLAUDE.md`), so a gate test can go red for a real reason (a missing file or text) without a database. Run it from the project root.
