# Extending MCP and OAuth from a Plugin or Module [5.12+]

How a plugin or module adds MCP tools, resources and prompts, makes its field types work with MCP, protects its own API with Craft's OAuth server, and offers personal access token scopes. All of it needs Craft 5.12 or later; set the plugin's `craftcms/cms` constraint to `^5.12.1` if you rely on snake_case naming or `McpOutputFieldInterface`. [5.12+]

Sources: [`src/services/Mcp.php`](https://github.com/craftcms/cms/blob/5.12.4/src/services/Mcp.php), [`src/mcp/CapabilityRegistry.php`](https://github.com/craftcms/cms/blob/5.12.4/src/mcp/CapabilityRegistry.php), [`src/mcp/CapabilityDiscovery.php`](https://github.com/craftcms/cms/blob/5.12.4/src/mcp/CapabilityDiscovery.php), [`src/mcp/attributes/`](https://github.com/craftcms/cms/tree/5.12.4/src/mcp/attributes), [`src/base/InputSchemaFieldInterface.php`](https://github.com/craftcms/cms/blob/5.12.4/src/base/InputSchemaFieldInterface.php), [`src/base/McpOutputFieldInterface.php`](https://github.com/craftcms/cms/blob/5.12.4/src/base/McpOutputFieldInterface.php), [`src/oauth/Resource.php`](https://github.com/craftcms/cms/blob/5.12.4/src/oauth/Resource.php), [`src/services/PersonalAccessTokens.php`](https://github.com/craftcms/cms/blob/5.12.4/src/services/PersonalAccessTokens.php). SDK: `mcp/sdk` ~0.9.0. Docs: https://craftcms.com/docs/5.x/extend/mcp.html (its examples still use dotted names; follow the snake_case rule below).

## Contents

- [Registering capabilities](#registering-capabilities)
- [A complete tool](#a-complete-tool)
- [Naming](#naming)
- [Scopes and gating attributes](#scopes-and-gating-attributes)
- [Hiding capabilities per user](#hiding-capabilities-per-user)
- [Custom field types](#custom-field-types)
- [Protecting your own API with OAuth](#protecting-your-own-api-with-oauth)
- [Personal access token scope groups](#personal-access-token-scope-groups)
- [Other hooks](#other-hooks)
- [GraphQL schema components](#graphql-schema-components)
- [Common Pitfalls](#common-pitfalls)

## Registering Capabilities

Append class names on `craft\services\Mcp::EVENT_REGISTER_CAPABILITY_TYPES` (a `RegisterComponentTypesEvent`):

```php
use craft\events\RegisterComponentTypesEvent;
use craft\services\Mcp;
use myvendor\myplugin\mcp\OrderTools;
use yii\base\Event;

// In Plugin::init() (or a private _registerMcpCapabilities() called from it)
Event::on(Mcp::class, Mcp::EVENT_REGISTER_CAPABILITY_TYPES, function(RegisterComponentTypesEvent $event) {
    $event->types[] = OrderTools::class;
});
```

- No base class or interface. The class must be instantiable; Craft reflects its **public, non-static** methods carrying the SDK attributes `Mcp\Capability\Attribute\McpTool`, `McpResource`, `McpResourceTemplate` or `McpPrompt`.
- Constructor arguments are injected by `craft\mcp\CapabilityContainer`: Yii container definitions, every `craft\services\*` service by class (`craft\services\Elements $elements`), `GeneralConfig`, `Security`, a PSR logger.
- The input schema comes from the method signature, PHPDoc `@param` text and `#[Mcp\Capability\Attribute\Schema(...)]` on parameters (core uses `description:`, `format:`, `enum:`, `minimum:`, `items:`, `type:`). The output schema comes from the return type and `@return`; since `mcp/sdk` 0.9 a tool whose result doesn't match its `outputSchema` returns an error [5.12.1+].
- Report errors with `Mcp\Exception\ToolCallException`; the message goes to the client.
- `McpTool` parameters in `mcp/sdk` 0.9: `name`, `title`, `description`, `annotations` (`Mcp\Schema\ToolAnnotations`), `icons`, `meta`, `outputSchema`. `ToolAnnotations` takes `title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`.

## A Complete Tool

```php
<?php

namespace myvendor\myplugin\mcp;

use Craft;
use craft\elements\User;
use craft\mcp\attributes\RequiresPermission;
use Mcp\Capability\Attribute\McpTool;
use Mcp\Capability\Attribute\Schema;
use Mcp\Exception\ToolCallException;
use Mcp\Schema\ToolAnnotations;
use myvendor\myplugin\Plugin;

/**
 * MCP tools for My Plugin's orders.
 *
 * @author My Vendor
 * @since 1.4.0
 */
class OrderTools
{
    // =========================================================================
    // Public Methods
    // =========================================================================

    /**
     * Lists the current user's recent orders.
     *
     * @param int $limit The maximum number of orders to return.
     * @return array{orders: list<array{id: int, reference: string, total: string}>}
     * @throws ToolCallException if no user is signed in
     * @author My Vendor
     * @since 1.4.0
     */
    #[McpTool(
        name: 'my_plugin_orders_list',
        description: 'Lists the signed-in user’s most recent orders.',
        annotations: new ToolAnnotations(readOnlyHint: true),
    )]
    #[RequiresPermission('my-plugin:view-orders')]
    public function list(#[Schema(minimum: 1)] int $limit = 20): array
    {
        $user = Craft::$app->getUser()->getIdentity();
        if (!$user instanceof User) {
            throw new ToolCallException('A signed-in user is required.');
        }

        // Attributes only gate discovery: scope every query to what this user may see.
        $orders = Plugin::getInstance()->getOrders()->getRecentOrdersForUser($user, min($limit, 100));

        return ['orders' => array_map(fn($order) => [
            'id' => $order->id,
            'reference' => $order->reference,
            'total' => (string)$order->total,
        ], $orders)];
    }
}
```

- `readOnlyHint: true` is what lets a Read-only client see the tool. Omit it only for tools that change something; they then need `mcp:write`. Add `destructiveHint: true` for deletes and overwrites, as core does.
- The identity is the OAuth user (HTTP) or the `--user` (stdio). On the public server there is none.
- For element access inside a handler use `Craft::$app->getElements()->canView($element, $user)` / `canSave()` / `canDelete()`.

## Naming

- snake_case, prefixed with the plugin handle in snake_case: `my_plugin_orders_list`, `my_plugin_orders_refund` [changed 5.12.1]. Craft renamed its own tools in 5.12.1 because some MCP clients reject or rename tools with dots. Before 5.12.1: core used dot-separated names; don't copy that, and don't copy the dotted examples on the extend docs page.
- A name that collides with core or another plugin throws `LogicException('Duplicate MCP capability identities: …')` during discovery, which breaks capability listing for **every** user, not only yours. Resource URIs and templates collide the same way: use your own scheme or a `craft://my-plugin/…` path.
- Without `name:`, the method name is used, which collides easily (`list`). Always set it.

## Scopes and Gating Attributes

All in `craft\mcp\attributes`, method-level:

| Attribute | Effect |
|---|---|
| `#[RequiresPermission('handle')]` | `$user->can('handle')`; repeatable, all must pass. Use your plugin's kebab-case permission handles |
| `#[RequiresAdmin]` | Admin users only; HTTP tokens need `mcp:admin` |
| `#[RequiresAdminChanges]` | Admin, `allowAdminChanges` on, and `mcp:admin`; for anything that changes project config |
| `#[RequiresHttp]` | Omitted from stdio, e.g. a tool returning URLs authenticated by the access token |
| `#[PublicMcp]` | Moves the capability to the public server only (approvable in Settings → MCP); it is then absent from the authenticated and stdio servers |

Scope required on HTTP: `mcp:admin` with `RequiresAdmin`/`RequiresAdminChanges`; otherwise `mcp:write` for a tool without `readOnlyHint: true`; otherwise `mcp:read`. Resources and prompts need `mcp:read`. stdio ignores scopes. A capability with no attribute is visible to every authenticated user, so record-level checks inside the handler are mandatory.

`#[PublicMcp]` tools run with no user. They must enforce their own content restrictions; Settings → MCP content approvals don't apply to plugin tools.

## Hiding Capabilities per User

```php
use craft\mcp\events\DiscoveringCapability;
use craft\services\Mcp;

Event::on(Mcp::class, Mcp::EVENT_DISCOVERING_CAPABILITY, function(DiscoveringCapability $event) {
    // $event->reference (Mcp\Capability\Registry\ElementReference), $event->user (?User)
    if ($event->user && !$event->user->can('my-plugin:use-ai')) {
        $event->allowed = false;
    }
});
```

It fires for each capability that passed Craft's own checks on the authenticated and stdio servers, never for the public server, and can only hide.

## Custom Field Types

Both interfaces extend `craft\base\FieldInterface`. Implementing either interface needs the constraint bump (`^5.12.0` for `InputSchemaFieldInterface`, `^5.12.1` for `McpOutputFieldInterface`): an `implements` clause fails at class load on older Craft and can't sit behind a `version_compare` guard. Only the `Mcp::EVENT_REGISTER_CAPABILITY_TYPES` registration can be guarded (`class_exists(\craft\services\Mcp::class)`).

| Interface | Method | Since | Without it |
|---|---|---|---|
| `craft\base\InputSchemaFieldInterface` | `getInputSchema(): array` (JSON Schema of accepted values) | [5.12+] | Schema inferred from `getContentGqlMutationArgumentType()`; if that throws, the field accepts anything |
| `craft\base\McpOutputFieldInterface` | `getMcpValue(mixed $value, ElementInterface $element, McpOutputContext $context): mixed` | [5.12.1+] | `serializeValue($value, $element)` |

`craft\mcp\McpOutputContext` [5.12.1+] has `public` (going to the public server) and `requested` (named in the tool's `fields` argument). Elements, queries and collections in the returned value are expanded or summarized as nested elements under the user's permissions. Full examples and core implementers: the `craftcms` skill's `field-types-custom.md`.

```php
use craft\base\ElementInterface;
use craft\base\Field;
use craft\base\InputSchemaFieldInterface;
use craft\base\McpOutputFieldInterface;
use craft\mcp\McpOutputContext;

class Rating extends Field implements InputSchemaFieldInterface, McpOutputFieldInterface
{
    public function getInputSchema(): array
    {
        return ['type' => 'integer', 'minimum' => 1, 'maximum' => 5];
    }

    public function getMcpValue(mixed $value, ElementInterface $element, McpOutputContext $context): mixed
    {
        return $value === null ? null : ['stars' => (int)$value, 'outOf' => 5];
    }
}
```

## Protecting Your Own API with OAuth

Register a resource on `craft\services\OAuth::EVENT_REGISTER_RESOURCES` (`craft\events\RegisterOAuthResourcesEvent`, a `$resources` map of ID to config array or `craft\oauth\Resource`), or under `resources` in `config/oauth.php`:

```php
use craft\events\RegisterOAuthResourcesEvent;
use craft\helpers\UrlHelper;
use craft\services\OAuth;

Event::on(OAuth::class, OAuth::EVENT_REGISTER_RESOURCES, function(RegisterOAuthResourcesEvent $event) {
    $event->resources['my-plugin'] = [
        'scopes' => [
            'my-plugin:read' => 'View your orders.',
            'my-plugin:write' => 'Create and refund your orders.',
        ],
        'defaultScopes' => ['my-plugin:read'],
        'scopeLevels' => ['my-plugin:read', 'my-plugin:write'],
        'permissions' => ['my-plugin:view-orders'],
        'resourceUrl' => fn() => UrlHelper::siteUrl('api/my-plugin'),
        'consentDescription' => 'It will be able to use My Plugin’s API on your behalf.',
    ];
});
```

| `Resource` property | Notes |
|---|---|
| `id` | Map key; `^[a-zA-Z0-9_-]{1,64}$` |
| `scopes` | Required: scope ID to consent text. A scope may belong to one resource only |
| `defaultScopes` | Requested when the client sends none |
| `scopeLevels`, `scopeLabels` | Ordered levels for the consent screen, narrowest first |
| `userScopes` | `Closure(User $user, string[] $scopes): string[]`, the scopes this user may get |
| `permissions` | Checked on every request; without `accessCp` users sign in through the front-end `loginPath` |
| `resourceUrl` | Required: absolute http(s) URL (string or closure) with a path distinct from every other resource |
| `consentDescription` | Shown on the consent screen |

Invalid definitions throw `InvalidConfigException` when resources load. Registering a resource creates no route: authenticate in your own controller.

```php
use GuzzleHttp\Psr7\ServerRequest;
use League\OAuth2\Server\Exception\OAuthServerException;

// In a controller action with $allowAnonymous for this action and CSRF disabled for token-only requests
try {
    $user = Craft::$app->getOAuth()->authenticate(ServerRequest::fromGlobals(), 'my-plugin', ['my-plugin:read'], $scopes);
} catch (OAuthServerException) {
    $this->response->getHeaders()->set(
        'WWW-Authenticate',
        'Bearer resource_metadata="' . Craft::$app->getOAuth()->resourceMetadataUrl('my-plugin') . '"',
    );
    throw new \yii\web\UnauthorizedHttpException();
}
// $user is a craft\elements\User but is NOT logged in; check permissions yourself.
```

Signature: `authenticate(ServerRequestInterface $request, string $resource, array $requiredScopes = [], ?array &$scopes = null): User`. It reads only the `Authorization: Bearer` header. Scopes never grant more than the user's permissions.

## Personal Access Token Scope Groups

```php
use craft\oauth\ScopeGroup;

Craft::$app->getPersonalAccessTokens()->registerScopeGroup('my-plugin', fn() => new ScopeGroup(
    handle: 'my-plugin',
    label: 'My Plugin',
    scopes: ['my-plugin:read' => 'View your orders.'],
    userScopes: fn(\craft\elements\User $user, array $scopes) => $user->can('my-plugin:view-orders') ? $scopes : [],
));
```

- The scopes must belong to a registered OAuth resource. The factory returns `null` when the API is unavailable.
- Registering the same handle twice throws `yii\base\InvalidArgumentException`, as does a factory returning a group with a different handle.
- Users then pick these scopes on My Account → Tokens; your controller authenticates PATs with the same `authenticate()` call.

## Other Hooks

| Hook | Use |
|---|---|
| `craft\mcp\serializers\ElementSerializer::EVENT_SERIALIZING` (`craft\mcp\events\ElementSerializing`) | Adjust how elements are serialized for MCP |
| `craft\mcp\AdminInstructions::EVENT_COLLECT_INSTRUCTIONS`, `EVENT_COLLECT_SERVER_INSTRUCTIONS` | Add guidance to `info_get` and the server instructions |
| `craft\mcp\elements\ElementAdapterRegistry::EVENT_REGISTER_ADAPTERS` | Make a custom element type work with the `elements_*` tools (`craft\mcp\elements\ElementAdapter`, `BaseElementAdapter`); `supports()` [5.12.1+] |
| `Craft::$app->get('mcp')->getCheckRegistry()->register()` | Add a `content_model_audit` check (`craft\mcp\contentmodel\Check`) |

## GraphQL Schema Components

Plugins that add GraphQL schema components can mark them for OAuth/PAT-authenticated requests with the `authenticated` component key [5.12+]. That belongs to the GraphQL coverage: see the `craftcms` skill's `graphql.md`.

## Common Pitfalls

1. **Dotted or unprefixed tool names.** Use `my_plugin_orders_list`. A duplicate breaks discovery for everyone.
2. **Read tool without `readOnlyHint: true`.** Read-only clients never see it.
3. **Relying on attributes for record access.** They only gate discovery. Check each record against the user.
4. **Static or private handler methods.** Ignored by the registry.
5. **Inventing `Craft::$app->getMcp()` or a base class.** Neither exists: `Craft::$app->get('mcp')`, plain classes.
6. **A PAT scope group whose scopes no resource defines.** Register the OAuth resource first.
