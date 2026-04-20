# Permissions

Complete reference for the Craft CMS 5 permissions system: built-in permission handles, custom permissions, checking authorization in PHP and Twig, user groups, admin status, and element authorization events. For CP navigation gating based on permissions, see `cp.md`. For event registration patterns, see `events.md`.

## Documentation

- User management: https://craftcms.com/docs/5.x/system/user-management.html
- User permissions: https://craftcms.com/docs/5.x/extend/user-permissions.html

## Common Pitfalls

- Assuming admins have permissions -- they bypass all checks entirely, so `can()` always returns `true` for admins. You cannot restrict an admin with permissions.
- Checking permissions in templates but not in controllers -- always validate server-side too. A template `{% if %}` is UI convenience, not security.
- Using hardcoded UIDs for per-section permissions -- UIDs differ between environments. Look up dynamically via `Craft::$app->getEntries()->getSectionByHandle('blog')->uid`.
- Not understanding `moderateUsers` vs `administrateUsers` -- moderate allows editing names/usernames and sending activation emails. Administrate allows changing emails, resetting passwords, and deactivating accounts. Administrate enables privilege escalation.
- Forgetting that permissions are additive across groups -- removing a user from one group does not revoke permissions granted by another group. The user gets the union of all group permissions plus any direct permissions.
- Granting `administrateUsers` to non-admins -- this permission enables privilege escalation because it allows changing passwords and email addresses. Treat it as near-admin access.
- Checking `currentUser.can()` without null-checking `currentUser` first -- anonymous visitors have no user object, causing a Twig error.
- Not prefixing custom permission handles with the plugin handle -- leads to collisions between plugins.
- Checking a non-existent permission handle via `requirePermission()` -- Craft does not throw an error. Admins pass (they bypass all checks). Non-admins get a 403 because the permission is never granted — which looks "correct" but is wrong for the wrong reason. Assigning that handle in the CP has no effect since it's not registered. Define permission handles as class constants and reference them in both registration and checking to prevent mismatches.
- Using string literals for permission handles across multiple files -- a typo in one file (`'my-plugin:delete-cookies'` vs `'my-plugin:remove-cookies'`) creates a phantom permission that silently behaves wrong. Constants eliminate this class of bug entirely.

## Contents

- [Admin Status](#admin-status)
- [Built-in Permissions (Complete Reference)](#built-in-permissions-complete-reference)
- [User Groups](#user-groups)
- [Checking Permissions in Twig](#checking-permissions-in-twig)
- [Checking Permissions in PHP](#checking-permissions-in-php)
- [Registering Custom Permissions (Plugins)](#registering-custom-permissions-plugins)
- [Element Authorization Events](#element-authorization-events)
- [Permission Strategies](#permission-strategies)

## Admin Status

Admins bypass ALL permission checks. `can()` always returns `true` for admin users regardless of what permission is being checked. This is by design and cannot be overridden.

Key facts about admin status:

- Admins can modify all settings when `allowAdminChanges` is `true` in general config.
- Admins can make other users admin.
- Admin status is a separate flag from permissions -- it is not a permission itself.
- Reserve admin status for essential team members only.
- In production, set `allowAdminChanges` to `false` to prevent even admins from changing structure (sections, fields, etc.).

## Built-in Permissions (Complete Reference)

### System Access

| Handle | Purpose | Notes |
|--------|---------|-------|
| `accessSiteWhenSystemIsOff` | Access the front-end site in maintenance mode | |
| `accessCp` | Control panel access | Includes limited read-only element access |
| `accessCpWhenSystemIsOff` | CP access during maintenance mode | Requires `accessCp` as well |
| `performUpdates` | Manage Craft and plugin updates | |
| `accessPlugin-{pluginHandle}` | Plugin-specific CP access | Per-plugin, e.g. `accessPlugin-commerce` |

### User Management

| Handle | Purpose | Since | Notes |
|--------|---------|-------|-------|
| `viewUsers` | Read-only user access | 5.6.0 | |
| `editUsers` | Edit custom fields and non-critical data | | |
| `registerUsers` | Create new user accounts | | |
| `moderateUsers` | Edit names, usernames, send activation emails | 5.8.0 | Limited scope |
| `administrateUsers` | Change emails, reset passwords, deactivate | | Dangerous -- enables escalation |
| `impersonateUsers` | Log in as another user | | |
| `assignUserPermissions` | Grant permissions to other users | | |
| `assignUserGroup:{groupUid}` | Add users to a specific group | | Per-group, uses group UID |
| `deleteUsers` | Delete user accounts | | |

### Content Permissions (per section -- appended with `:uid`)

| Handle Pattern | Purpose |
|---------------|---------|
| `viewEntries:{sectionUid}` | View entries in a section |
| `createEntries:{sectionUid}` | Create new entries |
| `saveEntries:{sectionUid}` | Edit own entries |
| `deleteEntries:{sectionUid}` | Delete own entries |
| `viewPeerEntries:{sectionUid}` | View entries by other authors |
| `savePeerEntries:{sectionUid}` | Edit entries by other authors |
| `deletePeerEntries:{sectionUid}` | Delete entries by other authors |

### Asset Permissions (per volume -- appended with `:uid`)

| Handle Pattern | Purpose |
|---------------|---------|
| `viewAssets:{volumeUid}` | View assets in a volume |
| `saveAssets:{volumeUid}` | Upload and edit assets |
| `deleteAssets:{volumeUid}` | Delete assets |
| `replaceFiles:{volumeUid}` | Replace asset files |
| `editImages:{volumeUid}` | Use the image editor |
| `viewPeerAssets:{volumeUid}` | View assets uploaded by others |
| `savePeerAssets:{volumeUid}` | Edit assets uploaded by others |
| `deletePeerAssets:{volumeUid}` | Delete assets uploaded by others |

### Category Permissions (per group -- appended with `:uid`)

| Handle Pattern | Purpose |
|---------------|---------|
| `viewCategories:{groupUid}` | View categories in a group |
| `saveCategories:{groupUid}` | Create and edit categories |
| `deleteCategories:{groupUid}` | Delete categories |

### Global Set and Site Permissions

| Handle Pattern | Purpose |
|---------------|---------|
| `editGlobalSet:{globalSetUid}` | Edit a specific global set |
| `editSite:{siteUid}` | Edit content for a specific site |

### Utility Permissions (prefixed `utility:`)

| Handle | Utility |
|--------|---------|
| `utility:updates` | Updates |
| `utility:system-report` | System Report |
| `utility:php-info` | PHP Info |
| `utility:system-messages` | System Messages |
| `utility:asset-indexes` | Asset Indexes |
| `utility:queue-manager` | Queue Manager |
| `utility:clear-caches` | Clear Caches |
| `utility:deprecation-errors` | Deprecation Warnings |
| `utility:db-backup` | Database Backup |
| `utility:find-replace` | Find and Replace |
| `utility:migrations` | Migrations |

## User Groups

User groups are the primary mechanism for organizing permissions. Created in Settings > Users.

- **Craft Pro** supports unlimited groups.
- **Craft Team** has a single configurable group.
- Each group has a Name, Handle, and a set of assigned Permissions.
- Permissions are additive -- a user in multiple groups gets the union of all permissions from every group.
- Direct user permissions (assigned to a specific user, not via group) also stack on top of group permissions.
- Group membership is checked via `user.isInGroup('handle')` or `user.isInGroup(groupId)`.
- Group UIDs are used in permission handles like `assignUserGroup:{groupUid}`.

### Looking Up Group UIDs

```php
// By handle
$group = Craft::$app->getUserGroups()->getGroupByHandle('editors');
$uid = $group->uid;

// All groups
$groups = Craft::$app->getUserGroups()->getAllGroups();
```

## Checking Permissions in Twig

### Basic permission check

```twig
{# Always null-check currentUser for anonymous visitors #}
{% if currentUser and currentUser.can('accessCp') %}
    <a href="{{ cpUrl() }}">Control Panel</a>
{% endif %}
```

### Per-section permission check (dynamic UID lookup)

```twig
{% set section = craft.app.entries.getSectionByHandle('blog') %}
{% if currentUser and section and currentUser.can("createEntries:#{section.uid}") %}
    <a href="{{ siteUrl('blog/new') }}">New Post</a>
{% endif %}
```

### Custom plugin permission check (dynamic UID)

For plugin entities (channels, forms, item types) where permissions are scoped per-entity:

```twig
{# Assume 'channel' is passed to the template from a controller or route #}
{% if currentUser and currentUser.can("my-plugin:manage:#{channel.uid}") %}
    <a href="{{ actionUrl('my-plugin/channels/edit', { id: channel.id }) }}">Edit Channel</a>
{% endif %}
```

### Group membership

```twig
{% if currentUser and currentUser.isInGroup('editors') %}
    {# Show editor-specific tools #}
{% endif %}
```

### Require tags (hard gates)

```twig
{# Require login -- redirects anonymous visitors to loginPath #}
{% requireLogin %}

{# Require specific permission -- throws 403 if missing #}
{% requirePermission 'accessCp' %}

{# Require admin status -- throws 403 for non-admins #}
{% requireAdmin %}

{# Require guest -- redirects logged-in users away #}
{% requireGuest %}
```

These tags halt template rendering immediately. `{% requirePermission %}` and `{% requireAdmin %}` throw a `ForbiddenHttpException` (403). `{% requireLogin %}` redirects to the configured login path. Place them at the top of templates before any output.

## Checking Permissions in PHP

### In controllers

```php
// Require a permission -- throws ForbiddenHttpException if missing
$this->requirePermission('my-plugin:manage-items');

// Require login -- throws ForbiddenHttpException if guest
$this->requireLogin();
```

### On the current user

```php
$user = Craft::$app->getUser()->getIdentity();

if ($user && $user->can('my-plugin:manage-items')) {
    // authorized
}
```

### Per-section check with dynamic UID

```php
$section = Craft::$app->getEntries()->getSectionByHandle('blog');

if ($section && $someUser->can('viewEntries:' . $section->uid)) {
    // authorized for this section
}
```

### Checking group membership

```php
if ($user->isInGroup('editors')) {
    // user belongs to the "editors" group
}
```

### Important notes

- `$this->requirePermission()` is for controllers only -- it is a method on `craft\web\Controller`.
- Always look up UIDs dynamically. Never hardcode UIDs -- they differ between environments and are regenerated on fresh installs.
- `can()` always returns `true` for admins. If you need to restrict admins, use element authorization events instead (though even those can be overridden).

## Registering Custom Permissions (Plugins)

Register custom permissions in your plugin's `init()` method using the `EVENT_REGISTER_PERMISSIONS` event.

```php
use craft\events\RegisterUserPermissionsEvent;
use craft\services\UserPermissions;
use yii\base\Event;

Event::on(
    UserPermissions::class,
    UserPermissions::EVENT_REGISTER_PERMISSIONS,
    function(RegisterUserPermissionsEvent $event) {
        $event->permissions[] = [
            'heading' => 'My Plugin',
            'permissions' => [
                'my-plugin:manage-items' => [
                    'label' => 'Manage items',
                ],
                'my-plugin:delete-items' => [
                    'label' => 'Delete items',
                ],
                'my-plugin:view-reports' => [
                    'label' => 'View reports',
                    'nested' => [
                        'my-plugin:export-reports' => [
                            'label' => 'Export reports',
                        ],
                    ],
                ],
            ],
        ];
    }
);
```

### Convention

Prefix all custom permission handles with your plugin handle and a colon: `my-plugin:action-name`. Use kebab-case for both the plugin prefix and the action name. This prevents collisions between plugins and matches the convention used by Craft core and first-party plugins.

### Permission handle constants

Define permission handles as class constants. This prevents phantom mismatches where a typo in one file creates a permission that silently behaves wrong (denies non-admins, passes for admins — hard to debug).

```php
namespace myplugin;

class Permissions
{
    public const PERMISSION_SETTINGS = 'my-plugin:settings';
    public const PERMISSION_MANAGE = 'my-plugin:manage';
    public const PERMISSION_VIEW = 'my-plugin:view';
    public const PERMISSION_DELETE = 'my-plugin:delete';
}
```

Use constants everywhere — registration, controllers, templates, element `can*()` methods:

```php
// Controller
$this->requirePermission(Permissions::PERMISSION_MANAGE . ":{$item->uid}");

// Element canView()
return $user->can(Permissions::PERMISSION_VIEW . ":{$this->getItemUid()}");
```

```twig
{# Template — can't use PHP constants, so reference the string value #}
{% if currentUser.can('my-plugin:manage:' ~ item.uid) %}
```

### Dynamic per-entity permissions (parameterized UIDs)

For plugins that manage multiple entities (e.g., forms, channels, item types), generate one permission handle per entity using its UID. This follows Craft's own convention:

| Craft Handle | Pattern |
|-------------|---------|
| `assignUserGroup:{uid}` | Per user group |
| `editSite:{uid}` | Per site |
| `viewEntries:{uid}` | Per section |
| `viewAssets:{uid}` | Per volume |
| `my-plugin:manage-group:{uid}` | Plugin convention |

Wire the constants (from `Permissions` class above) into a builder method on your plugin class, then call it from the `EVENT_REGISTER_PERMISSIONS` handler:

```php
private function _buildPermissions(): array
{
    $permissions = [
        Permissions::PERMISSION_SETTINGS => [
            'label' => Craft::t('my-plugin', 'Manage settings'),
        ],
    ];

    foreach (MyPlugin::getInstance()->getItems()->getAllItems() as $item) {
        $suffix = $item->uid;
        $permissions[Permissions::PERMISSION_MANAGE . ":{$suffix}"] = [
            'label' => Craft::t('my-plugin', 'Manage {name}', ['name' => $item->name]),
            'nested' => [
                Permissions::PERMISSION_VIEW . ":{$suffix}" => [
                    'label' => Craft::t('my-plugin', 'View entries'),
                ],
                Permissions::PERMISSION_DELETE . ":{$suffix}" => [
                    'label' => Craft::t('my-plugin', 'Delete entries'),
                    'warning' => Craft::t('my-plugin', 'Allows permanent deletion'),
                ],
            ],
        ];
    }

    return $permissions;
}
```

### How doesUserHavePermission() resolves handles

Permission handles are stored **lowercase** in the database. `doesUserHavePermission()` calls `strtolower()` on the handle before checking. This means `'My-Plugin:Manage'` and `'my-plugin:manage'` resolve to the same permission. Convention: always use lowercase kebab-case.

Resolution order:
1. If `$user->admin` is `true` → returns `true` immediately (no DB lookup)
2. If Craft edition is Solo → returns `true` unconditionally
3. Looks up the handle in the user's stored permission set via `in_array()`
4. If handle not found → returns `false`

**Key implication:** A non-existent permission handle is effectively a deny for non-admins but invisible to admins. If you register `my-plugin:manage` but check `my-plugin:mannage` (typo), admins pass silently and non-admins get a 403. Constants prevent this.

This pattern gives admins granular control over which plugin entities each user group can manage. Always pair with element-level `canView()` / `canSave()` checks (see `elements.md` and `element-authorization.md`).

### Nested permissions and extra properties

The `nested` key creates a hierarchy in the CP permissions UI. A nested permission is only checkable when its parent is checked. This is a UI convenience -- Craft does not enforce the hierarchy in `can()` checks. If you grant a nested permission directly (e.g., via database), `can()` will return `true` even if the parent is unchecked.

Permission entries support these properties:

| Property | Type | Purpose |
|----------|------|---------|
| `label` | `string` | Required. Display text for the permission. |
| `nested` | `array` | Child permissions (indented in CP, require parent check). |
| `info` | `string` | Tooltip text shown on hover. Use for clarification. |
| `warning` | `string` | Warning text shown below the permission. Use for dangerous permissions. |

### Gating CP nav items based on permission

Cross-reference with `cp.md` for the full pattern. The short version:

```php
use craft\events\RegisterCpNavItemsEvent;
use craft\web\twig\variables\Cp;
use yii\base\Event;

Event::on(
    Cp::class,
    Cp::EVENT_REGISTER_CP_NAV_ITEMS,
    function(RegisterCpNavItemsEvent $event) {
        $user = Craft::$app->getUser()->getIdentity();
        if ($user && $user->can('my-plugin:manage-items')) {
            $event->navItems[] = [
                'url' => 'my-plugin/items',
                'label' => 'Items',
                'icon' => '@my-plugin/icon.svg',
            ];
        }
    }
);
```

### Gating controller actions

Always pair template-level permission checks with controller-level enforcement:

```php
public function actionEdit(int $id = null): Response
{
    $this->requirePermission('my-plugin:manage-items');

    // ... controller logic
}

public function actionDelete(): Response
{
    $this->requirePermission('my-plugin:delete-items');

    // ... controller logic
}
```

## Element Authorization Events

For fine-grained, context-aware authorization that goes beyond static permissions, see `element-authorization.md`. That reference covers:

- All 8 authorization events on `Elements::class` (VIEW, SAVE, CREATE_DRAFTS, DUPLICATE, DUPLICATE_AS_DRAFT, COPY, DELETE, DELETE_FOR_SITE)
- The four-layer defense model (UI → Route → Query → Authorization)
- Query scoping via `EVENT_BEFORE_PREPARE` with context guards
- Element `can*()` method overrides with parent delegation
- Built-in authorization logic for Entry, User, and Asset elements
- Defense-in-depth patterns for security-sensitive plugins

Key facts for quick reference:

- Authorization events live on `craft\services\Elements`, not on the element class (element-level events deprecated since 4.3.0)
- Setting `$event->authorized = false` with `$event->handled = true` is the only way to restrict admins
- Element queries do NOT filter by permission — scoping requires `EVENT_BEFORE_PREPARE`

## Permission Strategies

### Member area (gated content)

1. Create a user group "Members" with view permissions for the gated section.
2. Set the default user group in Settings > Users so new registrations are automatically assigned.
3. In templates, use `{% requireLogin %}` at the top, then check group membership:

```twig
{% requireLogin %}
{% if not currentUser.isInGroup('members') %}
    {% redirect 'upgrade' %}
{% endif %}

{# Member-only content here #}
```

### Editor workflow (author/editor/publisher)

Organize by escalating content privileges:

- **Group "Authors"**: `createEntries`, `saveEntries` on relevant sections. Can create and edit own entries.
- **Group "Editors"**: `viewPeerEntries`, `savePeerEntries`, `deletePeerEntries` on the same sections. Can review and edit anyone's entries.
- **Group "Publishers"**: All entry permissions including `deleteEntries`. Full content control.

Each group also needs `accessCp` and `editSite:{siteUid}` for the relevant sites.

### Plugin-specific features

1. Register custom permissions with nested structure (see [Registering Custom Permissions](#registering-custom-permissions-plugins)).
2. Check in controllers with `$this->requirePermission()`.
3. Check in templates with `currentUser.can()`.
4. Gate CP nav items based on permission (see above and `cp.md`).
5. Use the `accessPlugin-{pluginHandle}` permission for top-level plugin access, then use custom permissions for finer-grained control within the plugin.

### Multi-site permissions

When a Craft install has multiple sites, per-site editing is controlled by `editSite:{siteUid}`:

```php
$site = Craft::$app->getSites()->getSiteByHandle('french');
if ($user->can('editSite:' . $site->uid)) {
    // user can edit content for the French site
}
```

Content permissions (entries, assets, categories) apply across all sites. A user with `saveEntries:{sectionUid}` can edit entries in that section on any site they have `editSite` permission for. Both permissions are required -- the content permission AND the site permission.
