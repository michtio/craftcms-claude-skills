# Hello

A minimal Craft 5.12 plugin, used as a fixture for the gated-build evals. It is not a real plugin.

The fixture has no DDEV project and no Craft install. `vendor/bin/pest` is a small stand-in that runs the suite's tests with PHP only, so a gate test can go red for a real reason (a missing class or a wrong value) without a database. Run it from the project root.
