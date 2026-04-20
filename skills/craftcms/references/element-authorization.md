# Element Authorization — Defense-in-Depth

Complete reference for authorizing element operations in Craft CMS 5: the four-layer defense model, authorization events on the Elements service, element `can*()` methods, query-level scoping via `EVENT_BEFORE_PREPARE`, and controller-level enforcement. For static permission handles and registration, see `permissions.md`. For element lifecycle and save flow, see `elements.md`.

## Documentation

- Element types: https://craftcms.com/docs/5.x/extend/element-types.html
- User permissions: https://craftcms.com/docs/5.x/extend/user-permissions.html
- Controller actions: https://craftcms.com/docs/5.x/extend/controllers.html

## Common Pitfalls

- Relying on template permission checks alone (`currentUser.can()`) — these are UI convenience, not security. Always enforce at the controller and/or authorization layer.
- Listening on `Element::class` for authorization events — the element-level events are deprecated since 4.3.0. Use `Elements::class` (the service) instead.
- Setting `$event->authorized = true` without `$event->handled = true` — a later handler can override your authorization. Use `handled` when your decision must be final.
- Forgetting the site authorization check — `Elements::canView()` and `Elements::canSave()` check `editSite:{siteUid}` before firing element authorization events. A site permission failure blocks the action regardless of event handlers.
- Assuming element queries filter by permission — they do not. A `craft.entries()` call returns all matching entries regardless of who is viewing. Permission enforcement happens at the element level (`can*()` methods) and the controller level, not the query level.
- Using `EVENT_BEFORE_PREPARE` without context guards — always check `isCpRequest()`, console context, and admin status before modifying queries. Scoping front-end queries or console commands breaks bulk operations, migrations, and queue jobs.
- Using `->where()` instead of `->andWhere()` on scoped queries — `where()` replaces all internal conditions including status filters and soft-delete filters. Always use `$event->sender->subQuery->andWhere()`.

## Contents

- [Four-Layer Defense Model](#four-layer-defense-model)
- [Layer 1: Template Checks (UI)](#layer-1-template-checks-ui)
- [Layer 2: Controller Authorization (Route)](#layer-2-controller-authorization-route)
- [Layer 3: Query Scoping (Data)](#layer-3-query-scoping-data)
- [Layer 4: Element Authorization Events (Safety Net)](#layer-4-element-authorization-events-safety-net)
- [Element can*() Methods](#element-can-methods)
- [Built-in Authorization Logic by Element Type](#built-in-authorization-logic-by-element-type)
- [Defense Patterns for Plugins](#defense-patterns-for-plugins)

## Four-Layer Defense Model

Craft CMS authorization works in four layers. Each layer serves a different purpose. Layers 1-3 are opt-in (the developer adds them). Layer 4 is built into Craft's CP controllers.

| Layer | Mechanism | Scope | Who Adds It |
|-------|-----------|-------|-------------|
| **UI** | Twig `currentUser.can()`, conditional rendering | Hides buttons/links from unauthorized users | Developer (templates) |
| **Route** | Controller `requirePermission()`, `$allowAnonymous`, `beforeAction()` | Blocks unauthorized HTTP requests | Developer (controllers) |
| **Query** | `EVENT_BEFORE_PREPARE` on element queries | Filters result sets by permission | Developer/plugin (event handler) |
| **Authorization** | `Elements::EVENT_AUTHORIZE_*` events + element `can*()` methods | Per-element, per-action gate | Craft built-in + plugin overrides |

**Key insight:** Front-end templates bypass layer 4 entirely. Craft's CP controllers call `Elements::canView()`/`canSave()` before rendering edit screens or processing saves, but front-end Twig templates access elements directly through queries. If your plugin needs to restrict front-end element access, you must implement layers 2-3 yourself.

## Layer 1: Template Checks (UI)

Template checks prevent UI elements from rendering for unauthorized users. They are cosmetic — they do not prevent access.

```twig
{# Always null-check currentUser — anonymous visitors have no user object #}
{% if currentUser and currentUser.can('my-plugin:manage-items') %}
    <a href="{{ cpUrl('my-plugin/items/new') }}">New Item</a>
{% endif %}

{# Require login for entire template #}
{% requireLogin %}

{# Require specific permission #}
{% requirePermission 'my-plugin:view-reports' %}
```

Never rely on this layer alone. A user who knows the URL can bypass template rendering entirely.

## Layer 2: Controller Authorization (Route)

Controllers enforce authorization on HTTP requests. This is the first real security boundary.

### $allowAnonymous

Controls which actions are accessible without authentication:

```php
// Default: all actions require login
protected int|string|array $allowAnonymous = self::ALLOW_ANONYMOUS_NEVER; // 0

// Specific actions for anonymous users (live site only)
protected int|string|array $allowAnonymous = [
    'webhook' => self::ALLOW_ANONYMOUS_LIVE,
];

// Bitwise: allow anonymous live AND offline
protected int|string|array $allowAnonymous = self::ALLOW_ANONYMOUS_LIVE | self::ALLOW_ANONYMOUS_OFFLINE;
```

Constants: `ALLOW_ANONYMOUS_NEVER` (0), `ALLOW_ANONYMOUS_LIVE` (1), `ALLOW_ANONYMOUS_OFFLINE` (2).

### beforeAction() flow

Controller `beforeAction()` enforces in this order:
1. Disables CSRF for Live Preview requests
2. Calls parent `beforeAction()`
3. Checks `$allowAnonymous` against the current action
4. For CP requests: calls `requireLogin()` then checks `accessCp` permission
5. For front-end guests when system is offline: checks `accessSiteWhenSystemIsOff`

### Authorization methods

```php
// Require authenticated user (redirects guests to login)
$this->requireLogin();

// Require admin status (calls requireLogin() first)
// Pass false to skip allowAdminChanges check
$this->requireAdmin();

// Require specific permission (throws 403)
$this->requirePermission('my-plugin:manage-items');

// Require elevated session (password re-entry modal)
$this->requireElevatedSession();

// Fail-closed route whitelisting via EVENT_BEFORE_ACTION
use yii\base\ActionEvent;

Event::on(
    Controller::class,
    Controller::EVENT_BEFORE_ACTION,
    function(ActionEvent $event) {
        // Block all actions except whitelisted ones
        $allowed = ['index', 'view', 'webhook'];
        if (!in_array($event->action->id, $allowed)) {
            throw new ForbiddenHttpException('Action not permitted');
        }
    }
);
```

## Layer 3: Query Scoping (Data)

Element queries do **not** automatically filter by permissions. A `craft.entries()` or `Entry::find()` returns all matching entries regardless of who is viewing.

To restrict what a user sees, use `EVENT_BEFORE_PREPARE` on the relevant query class.

### EVENT_BEFORE_PREPARE

Defined on `craft\elements\db\ElementQuery`. Fires at the start of `prepare()`, before Craft builds the SQL. The event object is `yii\base\Event` — the query instance is `$event->sender`.

```php
use craft\elements\db\UserQuery;
use yii\base\Event;

Event::on(
    UserQuery::class,
    UserQuery::EVENT_BEFORE_PREPARE,
    function(Event $event) {
        /** @var UserQuery $query */
        $query = $event->sender;

        $request = Craft::$app->getRequest();

        // Guard 1: skip console requests (CLI, queue workers, migrations)
        if ($request->getIsConsoleRequest()) {
            return;
        }

        // Guard 2: only scope CP requests
        if (!$request->getIsCpRequest()) {
            return;
        }

        // Guard 3: admins see everything
        $currentUser = Craft::$app->getUser()->getIdentity();
        if (!$currentUser || $currentUser->admin) {
            return;
        }

        // Guard 4: only scope if plugin feature is active
        if (!$currentUser->can('my-plugin:scoped-access')) {
            return;
        }

        // Apply scoping — always andWhere(), never where()
        $scopedGroupIds = MyPlugin::getInstance()
            ->getScopingService()
            ->getScopedGroupIds($currentUser);

        $query->subQuery->andWhere([
            'users.id' => (new \craft\db\Query())
                ->select('userId')
                ->from('{{%usergroups_users}}')
                ->where(['groupId' => $scopedGroupIds]),
        ]);
    }
);
```

### Targeting specific element types

The event fires on the query class, so you target element types by class:

| Element | Query Class |
|---------|-------------|
| Entries | `craft\elements\db\EntryQuery` |
| Users | `craft\elements\db\UserQuery` |
| Assets | `craft\elements\db\AssetQuery` |
| Addresses | `craft\elements\db\AddressQuery` |
| Custom | Your `MyElementQuery` class |

No type checking is needed inside the handler — the class attachment handles targeting.

### Guard order matters

Always apply guards in this order:
1. **Console check** — never scope CLI/queue/migration context
2. **Request type** — CP vs front-end (most scoping is CP-only)
3. **Admin bypass** — admins typically see everything
4. **Feature check** — only scope when the plugin feature is active
5. **Apply scoping** — the actual query modification

Skipping guards breaks: queue workers (Guard 1), front-end template queries (Guard 2), admin bulk operations (Guard 3).

### Memoization pattern

Scope resolution (e.g., "which groups can this user see?") may require database queries. Cache per-request in a service property:

```php
class ScopingService extends Component
{
    private ?array $_scopedGroupIds = null;

    public function getScopedGroupIds(User $user): array
    {
        if ($this->_scopedGroupIds === null) {
            $this->_scopedGroupIds = $this->_resolveScopedGroups($user);
        }

        return $this->_scopedGroupIds;
    }
}
```

PHP is share-nothing per request — the property resets automatically. No cache invalidation needed.

### EVENT_AFTER_PREPARE

Fires after Craft finishes building the query. Use when you need to:
- Add `SELECT` columns that depend on Craft's prepared JOINs
- Add custom JOINs to `$event->sender->query` (the outer query)
- Collect cache tags based on the final query structure

```php
Event::on(
    EntryQuery::class,
    EntryQuery::EVENT_AFTER_PREPARE,
    function(Event $event) {
        /** @var EntryQuery $query */
        $query = $event->sender;

        // Add a column from a custom join
        $query->query
            ->leftJoin('{{%my_metadata}} meta', '[[meta.entryId]] = [[elements.id]]')
            ->addSelect(['meta.score AS metaScore']);
    }
);
```

### Canceling queries

Set `$event->isValid = false` to cancel the query entirely (returns empty results):

```php
Event::on(
    UserQuery::class,
    UserQuery::EVENT_BEFORE_PREPARE,
    function(Event $event) {
        if ($this->shouldBlockAccess()) {
            $event->isValid = false; // Query returns no results
        }
    }
);
```

## Layer 4: Element Authorization Events (Safety Net)

Authorization events fire when Craft checks whether a user can perform a specific action on a specific element. They live on `craft\services\Elements` (not on the element class — the element-level events are deprecated since 4.3.0).

### All authorization events

| Constant on `Elements` | Value | Since | Checks |
|------------------------|-------|-------|--------|
| `EVENT_AUTHORIZE_VIEW` | `'authorizeView'` | 4.3.0 | View element's edit page |
| `EVENT_AUTHORIZE_SAVE` | `'authorizeSave'` | 4.3.0 | Save element |
| `EVENT_AUTHORIZE_CREATE_DRAFTS` | `'authorizeCreateDrafts'` | 4.3.0 | Create drafts |
| `EVENT_AUTHORIZE_DUPLICATE` | `'authorizeDuplicate'` | 4.3.0 | Duplicate element |
| `EVENT_AUTHORIZE_DUPLICATE_AS_DRAFT` | `'authorizeDuplicateAsDraft'` | 5.0.0 | Duplicate as unpublished draft |
| `EVENT_AUTHORIZE_COPY` | `'authorizeCopy'` | 5.7.0 | Copy for duplication elsewhere |
| `EVENT_AUTHORIZE_DELETE` | `'authorizeDelete'` | 4.3.0 | Delete element |
| `EVENT_AUTHORIZE_DELETE_FOR_SITE` | `'authorizeDeleteForSite'` | 4.3.0 | Delete for specific site |

### Event object: AuthorizationCheckEvent

```php
use craft\events\AuthorizationCheckEvent;

// Properties:
$event->element;    // ?ElementInterface — the element being authorized
$event->user;       // User — the user being authorized
$event->authorized; // ?bool — null by default
```

### Resolution logic

The `Elements::_authCheck()` method fires the event and uses null-coalesce:

```
_authCheck($element, $user, EVENT_AUTHORIZE_VIEW) ?? $element->canView($user)
```

- **`$event->authorized = true`** — authorizes the action, overrides element's `can*()` method
- **`$event->authorized = false`** — denies the action, overrides element's `can*()` method
- **`$event->authorized = null`** (default) — defers to the element's own `can*()` method
- **`$event->handled = true`** — prevents later event handlers from changing the result

### Registration pattern

```php
use craft\services\Elements;
use craft\events\AuthorizationCheckEvent;
use yii\base\Event;

Event::on(
    Elements::class,
    Elements::EVENT_AUTHORIZE_SAVE,
    function(AuthorizationCheckEvent $event) {
        $element = $event->element;
        $user = $event->user;

        // Only apply to entries in a specific section
        if (!$element instanceof Entry || $element->section?->handle !== 'classifieds') {
            return;
        }

        // Deny saving if user hasn't accepted TOS
        if (!$user->acceptedTos) {
            $event->authorized = false;
            $event->handled = true; // Prevent other handlers from overriding
        }
    }
);
```

### Restricting admins

Authorization events are the **only** mechanism that can restrict admins. Since `User::can()` always returns `true` for admins, static permissions cannot gate admin actions. An event handler that sets `$event->authorized = false` with `$event->handled = true` blocks even admins.

### Site authorization pre-check

Before firing element authorization events, `Elements::canView()` and `Elements::canSave()` call `_siteAuthCheck()`, which requires `editSite:{siteUid}` permission for localized elements in multi-site installs. This runs before the element authorization event — a site permission failure blocks the action regardless of event handlers.

## Element can*() Methods

These methods are declared `public` on `ElementInterface`. Override them in your element class. Always call `parent::` to preserve the authorization event chain.

| Method | Base Default | Corresponding Event |
|--------|-------------|-------------------|
| `canView(User $user)` | `false` | `EVENT_AUTHORIZE_VIEW` |
| `canSave(User $user)` | `false` | `EVENT_AUTHORIZE_SAVE` |
| `canDelete(User $user)` | `false` | `EVENT_AUTHORIZE_DELETE` |
| `canDeleteForSite(User $user)` | `false` | `EVENT_AUTHORIZE_DELETE_FOR_SITE` |
| `canDuplicate(User $user)` | `false` | `EVENT_AUTHORIZE_DUPLICATE` |
| `canDuplicateAsDraft(User $user)` | Delegates to `canDuplicate()` | `EVENT_AUTHORIZE_DUPLICATE_AS_DRAFT` |
| `canCreateDrafts(User $user)` | `false` | `EVENT_AUTHORIZE_CREATE_DRAFTS` |
| `canCopy(User $user)` | Delegates to `canView()` | `EVENT_AUTHORIZE_COPY` |

### Custom element type pattern

```php
protected function canView(User $user): bool
{
    if (parent::canView($user)) {
        return true;
    }

    return $user->can("my-plugin:view-items:{$this->getCategoryUid()}");
}

protected function canSave(User $user): bool
{
    if (parent::canSave($user)) {
        return true;
    }

    // New elements: check create permission
    if (!$this->id) {
        return $user->can('my-plugin:create-items');
    }

    // Existing: check manage permission + author/peer logic
    if ($this->authorId === $user->id) {
        return $user->can('my-plugin:save-own-items');
    }

    return $user->can('my-plugin:save-peer-items');
}

protected function canDelete(User $user): bool
{
    if (parent::canDelete($user)) {
        return true;
    }

    return $user->can("my-plugin:delete-items:{$this->getCategoryUid()}");
}

public function canCreateDrafts(User $user): bool
{
    // Allow anyone with view access to create drafts
    return $this->canView($user);
}
```

## Built-in Authorization Logic by Element Type

### Entry

| Method | Logic |
|--------|-------|
| `canView()` | `viewEntries:{sectionUid}` + author/peer check via `viewPeerEntries:{sectionUid}` + draft creator check |
| `canSave()` | New: `createEntries:{sectionUid}`. Existing: `saveEntries:{sectionUid}` + peer check. Drafts: creator or `savePeerEntryDrafts` |
| `canDelete()` | Singles: always false. Drafts: creator or `deletePeerEntryDrafts`. Published: `deleteEntries:{sectionUid}` + peer check |
| `canDuplicate()` | `createEntries` + `saveEntries` (not singles) |
| `canCreateDrafts()` | Returns `true` — everyone with view access can create drafts |

### User

| Method | Logic |
|--------|-------|
| `canView()` | Self (`$user->id === $this->id`) OR `viewUsers` permission |
| `canSave()` | New: `canRegisterUsers()`. Self: always true. Others: `editUsers` |
| `canDelete()` | Not self, `deleteUsers` required, can only delete admins if you're an admin |
| `canDuplicate()` | Always `false` — users cannot be duplicated |

### Asset

| Method | Logic |
|--------|-------|
| `canView()` | `viewAssets:{volumeUid}` + peer check |
| `canSave()` | `saveAssets:{volumeUid}` + peer check |
| `canDelete()` | `deleteAssets:{volumeUid}` + peer check |

## Defense Patterns for Plugins

### Minimum viable authorization (most plugins)

For plugins that add element types:

1. **Register permissions** in `permissions.md` pattern (view, create, save, delete)
2. **Override `can*()` methods** on the element class (see pattern above)
3. **Call `requirePermission()`** in controller actions

This gives you layers 2 + 4. Add layer 1 (template checks) for CP nav gating.

### Full defense-in-depth (security-sensitive plugins)

For plugins that restrict access to existing Craft elements (users, entries):

1. **Register permissions** with parameterized UIDs
2. **Scope queries** via `EVENT_BEFORE_PREPARE` (layer 3)
3. **Gate controllers** via `requirePermission()` (layer 2)
4. **Override authorization** via `EVENT_AUTHORIZE_*` events (layer 4)
5. **Gate UI** in templates (layer 1)

This is required when your plugin needs to restrict what a user can see in the CP element index, not just what they can edit.

### Relation field scoping

When scoping element access, also scope relation field modals. Relation fields use element queries internally, so `EVENT_BEFORE_PREPARE` scoping automatically applies to modal selection. However, verify that the scoping context guards allow CP modal requests — they are CP requests but operate differently from index pages.

### GraphQL query scoping

GraphQL resolvers build element queries internally. Your `EVENT_BEFORE_PREPARE` handlers apply to GraphQL queries too, but the `isCpRequest()` guard will skip them. If you need to scope GraphQL results, add a separate guard that checks the GraphQL context instead of skipping non-CP requests entirely:

```php
// Instead of: if (!$request->getIsCpRequest()) return;
// Use:
if ($request->getIsConsoleRequest()) {
    return;
}

$isCp = $request->getIsCpRequest();
$isGraphql = $this->_isGraphqlRequest($request);

if (!$isCp && !$isGraphql) {
    return;
}
```

### Export pipeline scoping

Element exporters use element queries. Scoping via `EVENT_BEFORE_PREPARE` automatically restricts CSV/JSON/XML exports to the scoped set. No additional work needed if the context guards pass for CP requests.
