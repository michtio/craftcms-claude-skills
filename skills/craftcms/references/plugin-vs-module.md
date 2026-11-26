# Plugin vs Module Differences

What changes between a plugin and a module in bootstrapping and registration, with the registration code a module needs for template roots, translations and console commands. Everything else (services, elements, controllers, events) follows the same patterns in both.

## Comparison

Plugins and modules share the same architecture patterns. The differences are in bootstrapping and registration:

| Feature | Plugin | Module |
|---------|--------|--------|
| CP template root | Automatic (by handle) | Manual via `EVENT_REGISTER_CP_TEMPLATE_ROOTS` |
| Site template root | Manual via event | Same — manual for both |
| Translation category | Automatic (by handle) | Manual `PhpMessageSource` in `init()` |
| Settings model | Built-in `createSettingsModel()` | Env vars, config files, or private plugin (`_` prefix) |
| Install migration | `migrations/Install.php` | Content migrations only |
| Console commands | Automatic `controllerNamespace` | Must set before `parent::init()`, must be bootstrapped |
| CP nav section | `$hasCpSection = true` | `EVENT_REGISTER_CP_NAV_ITEMS` |
| Project config | Settings auto-tracked | Manual `ProjectConfig::set()` only |
| Namespace alias | Automatic via Composer | Must call `Craft::setAlias()` |

## Module Template Root Registration

```php
use craft\events\RegisterTemplateRootsEvent;
use craft\web\View;

Event::on(View::class, View::EVENT_REGISTER_CP_TEMPLATE_ROOTS,
    function(RegisterTemplateRootsEvent $event) {
        $event->roots['my-module'] = __DIR__ . '/templates';
    }
);
```

## Module Translation Registration

```php
Craft::$app->i18n->translations['my-module'] = [
    'class' => \craft\i18n\PhpMessageSource::class,
    'sourceLanguage' => 'en',
    'basePath' => __DIR__ . '/translations',
    'allowOverrides' => true,
];
```

## Module Console Command Registration

```php
public function init()
{
    Craft::setAlias('@mymodule', __DIR__);

    if (Craft::$app->getRequest()->getIsConsoleRequest()) {
        $this->controllerNamespace = 'modules\\mymodule\\console\\controllers';
    } else {
        $this->controllerNamespace = 'modules\\mymodule\\controllers';
    }

    parent::init(); // MUST come after setting controllerNamespace
}
```

The module **must** be bootstrapped in `config/app.php` for console commands to be discoverable.