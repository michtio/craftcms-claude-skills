# Hello

Craft 5.12 plugin (handle `hello`, namespace `acme\hello`).

- Gate tests: locked
- Pest: `vendor/bin/pest` from the project root. There is no DDEV project in this fixture, so skip every ddev, phpstan and check-cs gate and say so.
- Services live in `src/services/` and extend `yii\base\Component`.
