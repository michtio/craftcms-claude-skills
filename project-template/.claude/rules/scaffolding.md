# Scaffolding

- Entry file and class name match the plugin handle in PascalCase: handle `forum` → `src/Forum.php` / `class Forum`; handle `userProfile` → `src/UserProfile.php` / `class UserProfile`. The Craft starter ships with `src/Plugin.php` / `class Plugin` — rename both.
- `composer.json` `extra.class` must point to the renamed FQN (e.g. `"class": "vendor\\handle\\Handle"`). Update it whenever the entry class is renamed.
- Always use `ddev craft make <type> --with-docblocks` to scaffold new components. Never manually create boilerplate that the generator handles.
- After scaffolding, customize: add section headers, `@author YourVendor`, `@since` version, `@throws` chains, and project naming conventions.
- Available generators: `element-type`, `service`, `controller`, `command`, `queue-job`, `model`, `record`, `field-type`, `validator`, `widget-type`, `utility`, `asset-bundle`, `behavior`, `twig-extension`, `element-action`, `element-condition-rule`, `element-exporter`, `gql-directive`.
- New services land in `src/services/`. Add a typed accessor (`getX(): X { return $this->get('x'); }`) to `src/services/ServicesTrait.php` and register the class in its `static config()` `components` array.
- Event listeners, URL rule registration, and plugin lifecycle overrides (`getSettingsResponse()`, `getReadOnlySettingsResponse()`, `createSettingsModel()`) belong in `src/base/PluginTrait.php` — never inline in the main plugin class.
- The main plugin class stays a thin shell: property declarations, `use ServicesTrait; use PluginTrait;`, and an `init()` that calls `parent::init()`, sets `self::$plugin`, registers the namespace alias, and invokes the private `_register*` methods on the trait.
