# Architecture

- Business logic in services. Controllers are thin: validate, delegate, respond.
- Services extend `yii\base\Component`.
- Module must set `controllerNamespace` before `parent::init()` for console commands.
- Template roots, translations, and aliases registered manually in `init()`.
- `Craft::$app->onInit()` for deferred initialization needing a fully-booted app.
- Events for extensibility: fire before/after events on all significant operations.
