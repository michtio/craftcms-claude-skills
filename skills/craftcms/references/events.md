# Events

## Contents

- Common Pitfalls
- Event Anatomy (sender, name, event object)
- Registering Handlers (class-level, instance-level, deferred)
- Event Naming Conventions (REGISTER, DEFINE, BEFORE, AFTER, SET, AUTHORIZE)
- Key Event Sources (Element, Elements service, Fields, FieldLayout, UrlManager, View, Permissions, Plugins, ProjectConfig, Gql, Dashboard, Console, CP nav)
- Other Registerable Component Types (Utilities, Filesystems, Image Transformers, Auth Methods, Mail Transports)
- Behaviors
- Twig Extensions
- Registration Pattern (full plugin init example)
- Custom Events in Your Plugin
- Discovering Events

## Documentation

- Events: https://craftcms.com/docs/5.x/extend/events.html
- Event code generator: https://craftcms.com/docs/5.x/extend/events.html#event-code-generator
- Class reference: https://docs.craftcms.com/api/v5/craft-events-modelevent.html

## Common Pitfalls

- Registering handlers after events have already fired — Craft bootstraps plugins sequentially, and some events (like component registration) fire during that process. Wrap init logic in `Craft::$app->onInit()` for deferred bootstrapping.
- Setting `$event->handled = true` unnecessarily — this stops all subsequent handlers from running, breaking other plugins that listen for the same event.
- Not type-hinting the event object — without the correct type hint (e.g., `ModelEvent`, `RegisterComponentTypesEvent`), you miss event-specific properties like `$event->isNew` or `$event->types`.
- Using string event names instead of class constants — no IDE autocomplete, no deprecation warnings when Craft renames events, and typos fail silently.
- Confusing `CancelableEvent->isValid` with model validation — `isValid = false` tells the sender to halt the operation (e.g., cancel a save), it doesn't add validation errors.
- Listening for element events on `Element::class` when you only want entries — your handler fires for every element type (assets, users, categories). Use `Entry::class` to scope.

## Event Anatomy

Every event has three parts:

- **Sender** — the class instance that emits the event (available as `$event->sender`)
- **Name** — a string constant on the sender class (e.g., `Element::EVENT_BEFORE_SAVE`)
- **Event Object** — a `yii\base\Event` instance or subclass carrying event-specific data

## Registering Handlers

### Class-Level (Most Common)

Listens for ALL occurrences of an event across all instances of a class:

```php
use craft\elements\Entry;
use craft\events\ModelEvent;
use yii\base\Event;

Event::on(
    Entry::class,
    Entry::EVENT_BEFORE_SAVE,
    function(ModelEvent $event) {
        /** @var Entry $entry */
        $entry = $event->sender;
        $isNew = $event->isNew;
    }
);
```

### Instance-Level (Less Common)

Listens on a specific object instance:

```php
Craft::$app->on(
    \yii\base\Application::EVENT_AFTER_REQUEST,
    function(Event $e) {
        // Runs after every request
    }
);
```

### Deferred Registration

Wrap handler registration in `onInit()` so events that fire during bootstrapping aren't missed:

```php
Craft::$app->onInit(function() {
    Event::on(/* ... */);
});
```

## Event Naming Conventions

Craft follows consistent naming patterns. Understanding these tells you what an event does:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `EVENT_REGISTER_*` | Add items to a registry (types, components) | `Fields::EVENT_REGISTER_FIELD_TYPES` |
| `EVENT_DEFINE_*` | Modify a computed value or list | `Element::EVENT_DEFINE_SIDEBAR_HTML` |
| `EVENT_BEFORE_*` | Pre-action hook, often cancelable | `Element::EVENT_BEFORE_SAVE` |
| `EVENT_AFTER_*` | Post-action hook, action already committed | `Element::EVENT_AFTER_SAVE` |
| `EVENT_SET_*` | Authoritatively replace a value | `Element::EVENT_SET_ROUTE` |
| `EVENT_AUTHORIZE_*` | Permission check delegation | `Element::EVENT_AUTHORIZE_VIEW` |

### Cancelable Events

Events extending `CancelableEvent` can be halted by setting `$event->isValid = false`:

```php
Event::on(Entry::class, Entry::EVENT_BEFORE_SAVE,
    function(ModelEvent $event) {
        $entry = $event->sender;

        if ($someCondition) {
            $event->isValid = false; // Prevents the save
        }
    }
);
```

## Key Event Sources

### Element Events (~47 on Element class)

Already documented in `references/elements.md`. These fire on the **element instance itself** — `$event->sender` is the element. Use `Entry::class` or `MyElement::class` as the first argument to scope to a specific element type.

### Elements Service (`craft\services\Elements`) — 33+ events

These fire on the **Elements service**, not on the element instance. `$event->sender` is the service, and the element is available as a property on the event object (e.g., `$event->element`). Use these when you want to react to ALL element types, not just one:

| Event | When |
|-------|------|
| `EVENT_BEFORE_SAVE_ELEMENT` | Before any element save |
| `EVENT_AFTER_SAVE_ELEMENT` | After any element save |
| `EVENT_BEFORE_DELETE_ELEMENT` | Before any element delete |
| `EVENT_AFTER_DELETE_ELEMENT` | After any element delete |
| `EVENT_BEFORE_RESTORE_ELEMENT` | Before soft-delete restore |
| `EVENT_AFTER_RESTORE_ELEMENT` | After soft-delete restore |
| `EVENT_REGISTER_ELEMENT_TYPES` | Register custom element types |
| `EVENT_BEFORE_UPDATE_SLUG_AND_URI` | Before slug/URI computation |
| `EVENT_AUTHORIZE_VIEW` | View permission check |
| `EVENT_AUTHORIZE_SAVE` | Save permission check |
| `EVENT_AUTHORIZE_CREATE_DRAFTS` | Draft creation permission |
| `EVENT_AUTHORIZE_DELETE` | Delete permission check |

### Fields Service (`craft\services\Fields`)

| Event | When |
|-------|------|
| `EVENT_REGISTER_FIELD_TYPES` | Register custom field types |
| `EVENT_BEFORE_SAVE_FIELD` | Before a field is saved |
| `EVENT_AFTER_SAVE_FIELD` | After a field is saved |
| `EVENT_BEFORE_DELETE_FIELD` | Before a field is deleted |
| `EVENT_AFTER_DELETE_FIELD` | After a field is deleted |
| `EVENT_BEFORE_SAVE_FIELD_LAYOUT` | Before a field layout is saved |
| `EVENT_AFTER_SAVE_FIELD_LAYOUT` | After a field layout is saved |

### Field Layout (`craft\models\FieldLayout`)

| Event | When |
|-------|------|
| `EVENT_DEFINE_NATIVE_FIELDS` | Register native field layout elements |
| `EVENT_DEFINE_UI_ELEMENTS` | Register UI layout elements |

### URL Manager (`craft\web\UrlManager`)

| Event | When |
|-------|------|
| `EVENT_REGISTER_CP_URL_RULES` | Register CP routes |
| `EVENT_REGISTER_SITE_URL_RULES` | Register site/webhook routes |

### View (`craft\web\View`)

| Event | When |
|-------|------|
| `EVENT_REGISTER_CP_TEMPLATE_ROOTS` | Register CP template roots (modules) |
| `EVENT_REGISTER_SITE_TEMPLATE_ROOTS` | Register site template roots |
| `EVENT_BEFORE_RENDER_TEMPLATE` | Before template render |
| `EVENT_AFTER_RENDER_TEMPLATE` | After template render |

### User Permissions (`craft\services\UserPermissions`)

| Event | When |
|-------|------|
| `EVENT_REGISTER_PERMISSIONS` | Register custom permissions |

### Plugins (`craft\services\Plugins`)

| Event | When |
|-------|------|
| `EVENT_BEFORE_INSTALL_PLUGIN` | Before plugin install |
| `EVENT_AFTER_INSTALL_PLUGIN` | After plugin install |
| `EVENT_BEFORE_UNINSTALL_PLUGIN` | Before plugin uninstall |
| `EVENT_AFTER_UNINSTALL_PLUGIN` | After plugin uninstall |

### Project Config (`craft\services\ProjectConfig`)

| Event | When |
|-------|------|
| `EVENT_REBUILD` | When `project-config/rebuild` runs |
| `EVENT_AFTER_WRITE_YAML_FILES` | After YAML files are written |

### GQL (`craft\services\Gql`)

See `references/graphql.md` for the full 10-event GraphQL event reference.

### Dashboard (`craft\services\Dashboard`)

| Event | When |
|-------|------|
| `EVENT_REGISTER_WIDGET_TYPES` | Register custom dashboard widgets |

### Console Controller (`craft\console\Controller`)

| Event | When |
|-------|------|
| `EVENT_DEFINE_ACTIONS` | Add custom actions to existing controllers |

### CP Navigation (`craft\web\twig\variables\Cp`)

| Event | When |
|-------|------|
| `EVENT_REGISTER_CP_NAV_ITEMS` | Register CP nav items (modules) |

## Other Registerable Component Types

Craft's component architecture extends beyond elements, fields, and controllers. These are less common but follow the same `EVENT_REGISTER_*` pattern. For detailed implementation, `WebFetch` the linked documentation.

### Utilities (`craft\services\Utilities`)

CP utility pages for admin tools, diagnostics, and batch operations. Extend `craft\base\Utility`. Each utility gets its own permission automatically.

Doc: https://craftcms.com/docs/5.x/extend/utilities.html
Scaffold: `ddev craft make utility --with-docblocks`

```php
Event::on(Utilities::class, Utilities::EVENT_REGISTER_UTILITIES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyUtility::class;
    }
);
```

Key methods: `displayName()`, `id()`, `icon()`, `contentHtml()`, `badgeCount()`. The `contentHtml()` method returns the utility's CP page content. Badge counts show in the CP nav.

### Filesystem Types (`craft\services\Fs`)

Custom storage backends for assets (S3, Google Cloud, Azure). Extend `craft\base\Fs` or use a Flysystem adapter via `craft\flysystem\base\FlysystemFs`.

Doc: https://craftcms.com/docs/5.x/extend/filesystem-types.html
Scaffold: `ddev craft make filesystem-type --with-docblocks`

```php
Event::on(Fs::class, Fs::EVENT_REGISTER_FILESYSTEM_TYPES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyFs::class;
    }
);
```

### Widget Types (`craft\services\Dashboard`)

Dashboard widgets for the CP home screen. Extend `craft\base\Widget`. Content comes from `getBodyHtml()`, settings from `getSettingsHtml()`.

Doc: https://craftcms.com/docs/5.x/extend/widget-types.html
Scaffold: `ddev craft make widget-type --with-docblocks`

```php
Event::on(Dashboard::class, Dashboard::EVENT_REGISTER_WIDGET_TYPES,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyWidget::class;
    }
);
```

### Image Transformers (`craft\services\ImageTransforms`)

Custom image transform backends (Imgix, Thumbor, Cloudinary). Implement `craft\base\imagetransforms\ImageTransformerInterface`.

Doc: https://craftcms.com/docs/5.x/extend/image-transforms.html

```php
Event::on(ImageTransforms::class, ImageTransforms::EVENT_REGISTER_IMAGE_TRANSFORMERS,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyTransformer::class;
    }
);
```

### Auth Methods (`craft\services\Auth`)

Custom MFA/authentication methods (Craft 5). Extend `craft\auth\methods\BaseAuthMethod`.

```php
Event::on(Auth::class, Auth::EVENT_REGISTER_METHODS,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyAuthMethod::class;
    }
);
```

### Mail Transport Adapters (`craft\helpers\MailerHelper`)

Custom email delivery backends (Postmark, Mailgun, SES). Extend `craft\mail\transportadapters\BaseTransportAdapter`.

```php
Event::on(MailerHelper::class, MailerHelper::EVENT_REGISTER_MAILER_TRANSPORTS,
    function(RegisterComponentTypesEvent $event) {
        $event->types[] = MyTransportAdapter::class;
    }
);
```

## Behaviors

Behaviors let you attach methods and properties to existing Craft classes (entries, users, assets, queries, etc.) without modifying their source. Useful for adding computed attributes or helper methods to built-in element types.

Doc: https://craftcms.com/docs/5.x/extend/behaviors.html

```php
Event::on(Entry::class, Entry::EVENT_DEFINE_BEHAVIORS,
    function(DefineBehaviorsEvent $event) {
        $event->behaviors['my-plugin:post'] = PostBehavior::class;
    }
);
```

Key points:
- `$this->owner` gives access to the element the behavior is attached to. Type-hint with `@property` docblock.
- Behaviors survive `clone()` via `CloneFixTrait` — instance-level event handlers don't.
- `EVENT_DEFINE_BEHAVIORS` is available on all subclasses of `craft\base\Model`, `craft\db\ActiveRecord`, `craft\db\Query`, and `craft\web\Controller`.
- Name your behavior (`'my-plugin:post'`) to avoid collisions with other plugins.

## Twig Extensions

Plugins can expose custom Twig functions, filters, and variables to template developers. This is how plugins like SEOmatic, Blitz, and Navigation expose their template APIs.

### Via CraftVariable (most common)

Attach a variable class to `craft.myPlugin`:

```php
use craft\web\twig\variables\CraftVariable;

Event::on(CraftVariable::class, CraftVariable::EVENT_INIT,
    function(\yii\base\Event $event) {
        /** @var CraftVariable $variable */
        $variable = $event->sender;
        $variable->set('myPlugin', MyVariable::class);
    }
);
```

Then in Twig: `craft.myPlugin.someMethod()`.

### Variable Class Pattern

The variable class exposes your plugin's data to Twig templates. Typically returns element queries and service results:

```php
class MyPluginVariable
{
    /**
     * Returns a new element query.
     *
     * @param array $criteria
     * @return MyElementQuery
     */
    public function items(array $criteria = []): MyElementQuery
    {
        $query = MyElement::find();
        Craft::configure($query, $criteria);
        return $query;
    }

    /**
     * Returns a service result.
     */
    public function getSettings(): ?SettingsModel
    {
        return MyPlugin::$plugin->getSettings();
    }
}
```

Twig usage:
```twig
{% set items = craft.myPlugin.items({ limit: 10 }).all() %}
{% set settings = craft.myPlugin.settings %}
```

The `Craft::configure($query, $criteria)` pattern lets Twig authors pass query params directly — consistent with how `craft.entries()` works.

### Via Twig Extension (advanced)

For custom functions, filters, or global variables, register a Twig extension in your plugin's `init()`:

```php
if (Craft::$app->getRequest()->getIsSiteRequest()) {
    Craft::$app->getView()->registerTwigExtension(new MyTwigExtension());
}
```

Extend `\Twig\Extension\AbstractExtension` and override `getFunctions()`, `getFilters()`, or `getGlobals()`.

## Registration Pattern

The most common event pattern in plugin development — registering your component types:

```php
public function init(): void
{
    parent::init();

    // Element types
    Event::on(Elements::class, Elements::EVENT_REGISTER_ELEMENT_TYPES,
        function(RegisterComponentTypesEvent $event) {
            $event->types[] = MyElement::class;
        }
    );

    // Field types
    Event::on(Fields::class, Fields::EVENT_REGISTER_FIELD_TYPES,
        function(RegisterComponentTypesEvent $event) {
            $event->types[] = MyField::class;
        }
    );

    // Widget types
    Event::on(Dashboard::class, Dashboard::EVENT_REGISTER_WIDGET_TYPES,
        function(RegisterComponentTypesEvent $event) {
            $event->types[] = MyWidget::class;
        }
    );

    // CP URL rules
    Event::on(UrlManager::class, UrlManager::EVENT_REGISTER_CP_URL_RULES,
        function(RegisterUrlRulesEvent $event) {
            $event->rules['my-plugin/settings'] = 'my-plugin/settings/index';
        }
    );

    // Permissions
    Event::on(UserPermissions::class, UserPermissions::EVENT_REGISTER_PERMISSIONS,
        function(RegisterUserPermissionsEvent $event) {
            $event->permissions[] = [
                'heading' => Craft::t('my-plugin', 'My Plugin'),
                'permissions' => $this->_buildPermissions(),
            ];
        }
    );
}
```

## Custom Events in Your Plugin

Fire events so other plugins can extend your code:

### Define the Event Class

```php
class MyEntityEvent extends Event
{
    public MyEntity $entity;
    public bool $isNew = false;
}
```

### Fire Events in Your Service

```php
public const EVENT_BEFORE_SAVE_ITEM = 'beforeSaveItem';
public const EVENT_AFTER_SAVE_ITEM = 'afterSaveItem';

public function saveItem(MyEntity $item): bool
{
    $isNew = !$item->id;

    // Before event — cancelable
    if ($this->hasEventHandlers(self::EVENT_BEFORE_SAVE_ITEM)) {
        $this->trigger(self::EVENT_BEFORE_SAVE_ITEM, new MyEntityEvent([
            'entity' => $item,
            'isNew' => $isNew,
        ]));
    }

    // ... save logic ...

    // After event
    if ($this->hasEventHandlers(self::EVENT_AFTER_SAVE_ITEM)) {
        $this->trigger(self::EVENT_AFTER_SAVE_ITEM, new MyEntityEvent([
            'entity' => $item,
            'isNew' => $isNew,
        ]));
    }

    return true;
}
```

The `hasEventHandlers()` check is a performance optimization — avoids creating event objects when nobody's listening.

## Discovering Events

- **Debug toolbar** — shows all events emitted per request when `devMode` is on
- **Event code generator** — https://craftcms.com/docs/5.x/extend/events.html#event-code-generator
- **Xdebug breakpoint** on `yii\base\Event::trigger()` — shows every event during a request
- **Search source** for `EVENT_` constants in `vendor/craftcms/cms/src/`
- **Class reference** — every class page lists its events: https://docs.craftcms.com/api/v5/

An Entry class alone has ~47 events when you include inherited ones from Element, Model, and Yii base classes.
