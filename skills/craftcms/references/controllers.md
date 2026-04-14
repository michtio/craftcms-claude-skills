# Controllers

## Documentation

- Controllers: https://craftcms.com/docs/5.x/extend/controllers.html
- CP edit pages: https://craftcms.com/docs/5.x/extend/cp-edit-pages.html

## Common Pitfalls

- **Hardcoding the CP trigger in URLs** — The CP trigger (`admin` by default) is configurable via `cpTrigger` in `config/general.php`. When generating URLs in PHP, use the right helper: `UrlHelper::actionUrl('my-plugin/controller/action')` for action endpoints, `UrlHelper::cpUrl('my-plugin/path')` for CP pages (or `{{ cpUrl('my-plugin/path') }}` in Twig). When documenting endpoints in READMEs, write action URLs as `actions/my-plugin/controller/action` and CP URLs as `{cpTrigger}/my-plugin/path` — never assume `/admin/`. CP URL rules in `EVENT_REGISTER_CP_URL_RULES` define the path *after* the trigger, so the rule `my-plugin/items/<itemId:\d+>` resolves to `{cpTrigger}/my-plugin/items/123` at runtime.
- Forgetting `$this->requirePostRequest()` on mutating actions — without it, state-changing actions are accessible via GET, which browsers prefetch and bots crawl.
- Returning `null` from a save action without passing the entity back via `setRouteParams()` — the template re-renders but the entity (with its validation errors and filled-in values) is lost, showing a blank form.
- Webhook controllers without `$enableCsrfValidation = false` — external services don't have a CSRF token, so every POST returns 400.
- Using `requireAdmin()` for view actions that should work when admin changes are disabled — use `requireAdmin(false)` for read-only screens, otherwise admins can't even view settings on production.
- Registering webhook routes in CP URL rules instead of site URL rules — CP rules require authentication, so external services get redirected to the login page.
- Not distinguishing view vs mutate actions in `beforeAction()` — view actions should be accessible even when `allowAdminChanges` is `false`, so admins can still review settings without being able to change them.
- **Over-engineering with CP URL rules when action URLs suffice** — If the endpoint is an API call, AJAX handler, or utility action, the default `actions/{pluginHandle}/{controller}/{action}` URL works out of the box with query params (`?itemId=123`). CP URL rules with `<itemId:\d+>` path params are only worth the complexity for pretty URLs in CP nav or browser-facing pages. Don't register routes for endpoints that will only be called from JavaScript or `UrlHelper::actionUrl()`.

## Controller Access Patterns

Plugin controllers are accessible at `actions/{pluginHandle}/{controllerKebab}/{actionKebab}` by default — no route registration needed. The `actionTrigger` is `actions` by default (configurable in `config/general.php`). Craft resolves the plugin handle, controller class, and action method automatically from the URL segments.

For example, `MyPlugin\controllers\ItemsController::actionEditItem()` with plugin handle `my-plugin` resolves to:

```
actions/my-plugin/items/edit-item
```

In PHP, generate these with `UrlHelper::actionUrl('my-plugin/items/edit-item', ['itemId' => 123])`.

### When to register URL rules

| Pattern | Register? | Why |
|---------|-----------|-----|
| AJAX/API endpoint called from JS | No — action URL with query params | `actions/my-plugin/items/edit-item?itemId=123` works immediately |
| CP nav page with pretty URL | Yes — CP URL rule | Users see `{cpTrigger}/my-plugin/settings/items/42` in their browser |
| Public webhook or redirect | Yes — site URL rule | External services hit `my-plugin/webhook/receive` on the site URL |
| Form POST target | No — action URL via hidden input | `<input type="hidden" name="action" value="my-plugin/items/save-item">` |

The rule of thumb: register a route only when the URL is visible to humans (browser address bar, CP nav) or must be on the site domain (webhooks). For everything else, action URLs just work.

## Table of Contents

- [Controller Access Patterns](#controller-access-patterns)
- [Scaffold](#scaffold)
- [Controller Types](#controller-types)
- [CP Entity Controller Pattern](#cp-entity-controller-pattern)
- [Webhook/API Controller Pattern](#webhookapi-controller-pattern)
- [CP Screen Response](#cp-screen-response)
- [Action Routing](#action-routing)
- [Authorization Summary](#authorization-summary)

## Scaffold

```bash
ddev craft make controller --with-docblocks
```

## Controller Types

1. **CP Entity Controllers** — CRUD for managed entities (instances, match fields, settings)
2. **Webhook/API Controllers** — External service endpoints (anonymous, no CSRF, JSON responses)
3. **Settings Controllers** — Plugin settings pages

## CP Entity Controller Pattern

### The `$variables` Pattern

Build a `$variables` array with everything the template needs. Keys: `title`, `readOnly`, `docTitle` (browser tab), `crumbs` (breadcrumb trail), the entity, and any context data (claimed IDs, API responses, type options):

```php
class ItemsController extends Controller
{
    protected array|bool|int $allowAnonymous = false;

    private bool $readOnly;

    public function beforeAction($action): bool
    {
        if (!parent::beforeAction($action)) {
            return false;
        }

        $this->requireCpRequest();

        $currentUser = Craft::$app->getUser()->getIdentity();
        if (!$currentUser || !$currentUser->can('my-plugin:settings')) {
            throw new ForbiddenHttpException('You do not have permission.');
        }

        // View actions: admin without allowAdminChanges check
        $viewActions = ['index', 'edit-item'];
        if (in_array($action->id, $viewActions)) {
            $this->requireAdmin(false);
        } else {
            $this->requireAdmin();
        }

        $this->readOnly = !Craft::$app->getConfig()->getGeneral()->allowAdminChanges;

        return true;
    }

    public function actionIndex(): Response
    {
        $pluginName = 'My Plugin';
        $templateTitle = Craft::t('my-plugin', 'Items');

        $variables = [];
        $variables['title'] = $templateTitle;
        $variables['readOnly'] = $this->readOnly;
        $variables['docTitle'] = "{$pluginName} - {$templateTitle}";
        $variables['crumbs'] = [
            ['label' => $pluginName, 'url' => UrlHelper::cpUrl('my-plugin')],
            ['label' => Craft::t('my-plugin', 'Settings'), 'url' => UrlHelper::cpUrl('my-plugin/settings')],
        ];
        $variables['items'] = MyPlugin::$plugin->getItems()->getAllItems();

        return $this->renderTemplate('my-plugin/settings/items/_index', $variables);
    }
}
```

### Edit Action with Entity Resolution

The edit action handles three states: new entity, existing entity from DB, or re-render after validation failure (entity passed as parameter):

```php
public function actionEditItem(?int $itemId = null, ?MyEntity $item = null): Response
{
    if ($itemId === null && $this->readOnly) {
        throw new ForbiddenHttpException('Administrative changes are disallowed.');
    }

    $itemsService = MyPlugin::$plugin->getItems();
    $pluginName = 'My Plugin';

    $variables = [
        'itemId' => $itemId,
        'brandNewItem' => false,
    ];

    if ($itemId !== null) {
        if ($item === null) {
            $item = $itemsService->getItemById($itemId);
            if (!$item) {
                throw new NotFoundHttpException('Item not found');
            }
        }

        $variables['title'] = trim($item->name) ?: Craft::t('my-plugin', 'Edit Item');
    } else {
        if ($item === null) {
            $item = new MyEntity();
            $variables['brandNewItem'] = true;
        }

        $variables['title'] = Craft::t('my-plugin', 'Create a new item');
    }

    $variables['readOnly'] = $this->readOnly;
    $variables['docTitle'] = "{$pluginName} - {$variables['title']}";
    $variables['crumbs'] = [
        ['label' => $pluginName, 'url' => UrlHelper::cpUrl('my-plugin')],
        ['label' => Craft::t('my-plugin', 'Settings'), 'url' => UrlHelper::cpUrl('my-plugin/settings')],
        ['label' => Craft::t('my-plugin', 'Items'), 'url' => UrlHelper::cpUrl('my-plugin/settings/items')],
    ];
    $variables['item'] = $item;
    $variables['claimedSiteIds'] = $itemsService->getSiteIdsClaimedByOtherItems($item->id);

    return $this->renderTemplate('my-plugin/settings/items/_edit', $variables);
}
```

### Save Action with Validation Failure Handling

When save fails, pass the entity back via `setRouteParams()` so validation errors display and form values are preserved:

```php
public function actionSaveItem(): ?Response
{
    $this->requirePostRequest();

    $itemsService = MyPlugin::$plugin->getItems();
    $itemId = $this->request->getBodyParam('itemId');

    if ($itemId) {
        $item = $itemsService->getItemById((int)$itemId);
        if (!$item) {
            throw new BadRequestHttpException("Invalid item ID: $itemId");
        }
    } else {
        $item = new MyEntity();
    }

    $item->name = $this->request->getBodyParam('name');
    $item->handle = $this->request->getBodyParam('handle');
    $item->enabled = (bool)$this->request->getBodyParam('enabled', $item->enabled);

    if (!$itemsService->saveItem($item)) {
        $this->setFailFlash(Craft::t('my-plugin', 'Couldn\'t save item.'));

        Craft::$app->getUrlManager()->setRouteParams([
            'item' => $item,
        ]);

        return null;
    }

    $this->setSuccessFlash(Craft::t('my-plugin', 'Item saved.'));
    return $this->redirectToPostedUrl($item);
}
```

### Delete and Reorder (JSON Endpoints)

```php
public function actionDeleteItem(): Response
{
    $this->requirePostRequest();
    $this->requireAcceptsJson();

    $itemId = $this->request->getRequiredBodyParam('id');
    $item = MyPlugin::$plugin->getItems()->getItemById((int)$itemId);

    if (!$item) {
        throw new BadRequestHttpException("Invalid item ID: $itemId");
    }

    MyPlugin::$plugin->getItems()->deleteItem($item);

    return $this->asSuccess();
}

public function actionReorderItems(): Response
{
    $this->requirePostRequest();
    $this->requireAcceptsJson();

    $ids = $this->request->getRequiredBodyParam('ids');
    $itemsService = MyPlugin::$plugin->getItems();

    foreach ($ids as $sortOrder => $id) {
        $item = $itemsService->getItemById((int)$id);
        if ($item) {
            $item->sortOrder = $sortOrder;
            $itemsService->saveItem($item, false);
        }
    }

    return $this->asSuccess(Craft::t('my-plugin', 'Items reordered.'));
}
```

## Webhook/API Controller Pattern

For receiving external service calls — anonymous access, no CSRF, JSON responses:

```php
class WebhookController extends Controller
{
    protected array|bool|int $allowAnonymous = ['receive', 'verify'];

    public $enableCsrfValidation = false;

    public function actionVerify(): Response
    {
        return $this->asRaw('echo');
    }

    public function actionReceive(): Response
    {
        $request = Craft::$app->getRequest();

        if ($request->getIsGet()) {
            return $this->asRaw('echo');
        }

        $this->requirePostRequest();
        $startTime = microtime(true);

        try {
            $payload = $webhooksService->validateRequest($request, $secret);
            $webhooksService->routeWebhook($payload, $instanceId);

            return $this->asJson([
                'success' => true,
                'message' => 'Webhook processed',
            ]);

        } catch (BadRequestHttpException $e) {
            return $this->asJson([
                'success' => false,
                'message' => $e->getMessage(),
            ])->setStatusCode(400);

        } catch (Throwable $e) {
            return $this->asJson([
                'success' => false,
                'message' => $e->getMessage(),
            ])->setStatusCode(400);
        }
    }
}
```

### Key Webhook Patterns

- `$allowAnonymous` lists specific action names — not `true` for the whole controller
- `$enableCsrfValidation = false` — external services can't send CSRF tokens
- `$this->asJson()` for JSON responses, chain `->setStatusCode(400)` for errors
- `$this->asRaw()` for plain text responses (verification probes)
- Validate webhook signatures via a dedicated service method
- Track processing time for observability

## CP Screen Response

For element edit screens, use `CpScreenResponseBehavior`:

```php
/** @var Response|CpScreenResponseBehavior $response */
$response = $this->asCpScreen()
    ->title($element->title)
    ->editUrl($element->getCpEditUrl())
    ->action('my-plugin/elements/save');

return $response;
```

## Action Routing

### CP Routes

```php
Event::on(UrlManager::class, UrlManager::EVENT_REGISTER_CP_URL_RULES,
    function(RegisterUrlRulesEvent $event) {
        $event->rules['my-plugin/settings'] = 'my-plugin/settings/index';
        $event->rules['my-plugin/settings/items/new'] = 'my-plugin/items/edit-item';
        $event->rules['my-plugin/settings/items/<itemId:\d+>'] = 'my-plugin/items/edit-item';
    }
);
```

### Site Routes (Webhooks, API)

For webhook and API endpoints, register in **site** URL rules — not CP rules:

```php
Event::on(UrlManager::class, UrlManager::EVENT_REGISTER_SITE_URL_RULES,
    function(RegisterUrlRulesEvent $event) {
        $event->rules['my-plugin/webhook/receive'] = 'my-plugin/webhook/receive';
        $event->rules['my-plugin/webhook/verify'] = 'my-plugin/webhook/verify';
    }
);
```

## Authorization Summary

```php
$this->requireAdmin(false);                             // Admin, no allowAdminChanges check (view)
$this->requireAdmin();                                  // Admin + allowAdminChanges (mutate)
$this->requirePermission('my-plugin:settings');         // Custom permission (see permissions.md)
$this->requirePostRequest();                            // POST only
$this->requireAcceptsJson();                            // JSON endpoints
$this->requireCpRequest();                              // CP only
```

### Use-Case Mapping

| Endpoint type | Auth approach |
|---------------|---------------|
| Plugin settings page (view) | `requireCpRequest()` + `requireAdmin(false)` in `beforeAction()` for view actions — admins can view even with `allowAdminChanges` off |
| Plugin settings page (save) | `requireCpRequest()` + `requireAdmin()` — blocks when `allowAdminChanges` is `false` |
| CP feature gated by permission | `requireCpRequest()` + `requirePermission('my-plugin:manage-items')` — works for non-admin users with the permission |
| AJAX endpoint for CP UI | `requireCpRequest()` + `requireAcceptsJson()` + `requirePostRequest()` |
| Public webhook from external service | `$allowAnonymous = ['receive']` + `$enableCsrfValidation = false` — no auth, no CSRF |
| Preview/share URL for logged-in users | `requireLogin()` — any authenticated user, not just admins |
| Public API endpoint (headless) | `$allowAnonymous = true` — wide open, validate via API key/signature in the action |
