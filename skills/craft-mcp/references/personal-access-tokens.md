# Personal Access Tokens [5.12+]

Personal access tokens (PATs) let a user hand a script or app a token that acts as them, without an OAuth authorization flow. In core they're for the GraphQL API; plugins can offer their own scopes. **They can't be used for MCP.**

Sources: [`src/services/PersonalAccessTokens.php`](https://github.com/craftcms/cms/blob/5.12.4/src/services/PersonalAccessTokens.php), [`src/controllers/UsersController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/UsersController.php) (`actionTokens`, `actionCreateToken`), [`src/controllers/EditUserTrait.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/EditUserTrait.php) (`showTokensScreen`). Docs: https://craftcms.com/docs/5.x/system/oauth.html#personal-access-tokens

## The Tokens Screen

**My Account → Tokens** (`myaccount/tokens`). It lists the user's PATs and the apps they've authorized (MCP clients included), and is where both are revoked.

The screen is shown when all of these hold:

- the user is looking at their own account;
- some scope group offers them a grantable scope (GraphQL when `enableGql` is on, or a plugin group), or they have grants to list;
- they're an admin, or OAuth signing keys exist [5.12.1+]. Without keys, admins see setup instructions and everyone else doesn't see the screen. Before 5.12.1: the screen showed for everyone and token creation failed with a server error.

## Creating a Token

- **New token** needs an elevated session (password re-entry) and OAuth keys.
- Name, one or more scopes, and an expiry of **7, 30, 90 or 365 days**; nothing else is accepted.
- The token is shown once and isn't stored, so copy it immediately. Scopes can't be changed later (they're signed into the JWT); the name can.
- A PAT is an OAuth access token (a JWT with two dots) issued through an auto-created "Personal Access Client". One token can carry scopes from several resources; each resource only counts its own.

Programmatic creation (scripts, migrations, tests):

```php
use DateInterval;

$token = Craft::$app->getPersonalAccessTokens()->create(
    $user,                                  // craft\elements\User
    'Nightly export',
    ['graphql:read'],
    new DateInterval('P30D'),
);
// Throws yii\base\InvalidArgumentException('Invalid scopes.') if the user may not grant one of them.
```

`OAuth::createPersonalAccessToken()` is internal; use the service.

## Why MCP Can't Use a PAT

The core `mcp` scope group exists only so authorized MCP clients appear on the Tokens screen. Its `userScopes` closure returns `[]`, so `mcp:read`/`mcp:write`/`mcp:admin` are never grantable: `create()` throws "Invalid scopes" even for admins, and the CP never offers them. A GraphQL-scoped PAT sent to the MCP endpoint gets the same 401 challenge as no token.

To connect an MCP client: complete the OAuth flow (`client-setup.md`), or run the stdio server with `craft mcp/serve --user=…`.

## Using a PAT with GraphQL

| Detail | Value |
|---|---|
| Scopes | `graphql:read` (queries), `graphql:write` (mutations, and queries too); requires `enableGql` |
| Header | `Authorization: Bearer <token>` |
| Runs as | The token's user: an "Authenticated Schema" built from their permissions, with `currentUser` available |
| Field layout conditions | Respected [5.12.1+]: fields hidden for the user are left out of the schema (or resolve to `null` for element-specific conditions) |
| Offline system | Works for users who may access the site or CP while it's offline [5.12.3+] |

`X-Craft-Authorization: Bearer <PAT>` alone returns 401: Craft spots the JWT through `Request::getBearerToken()` (which prefers `X-Craft-Authorization`), but `OAuth::authenticate()` only reads the `Authorization` header. On Apache or FastCGI setups that strip `Authorization`, fix the server (`CGIPassAuth On` or a rewrite rule) rather than switching headers. Schema tokens (no dots) are unaffected. Full GraphQL authentication matrix: the `craftcms` skill's `graphql.md`.

```bash
curl -s https://example.com/api \
  -H "Authorization: Bearer $CRAFT_PAT" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ currentUser { id username } }"}'
```

## Plugin Scope Groups

Plugins offer their own API scopes on the Tokens screen with `registerScopeGroup()`. The scopes must belong to a registered OAuth resource. See `plugin-extension.md`.

## Common Pitfalls

1. **Telling a user to make a PAT for their MCP client.** Impossible by design. Use OAuth or stdio.
2. **"I don't see Tokens under My Account."** GraphQL is off and no plugin offers scopes, or (non-admins) OAuth keys are missing. Run `craft oauth/generate-keys` or set the key env vars.
3. **Expecting a token value back from the list.** Tokens aren't stored; revoke and create a new one.
4. **Sending the PAT in `X-Craft-Authorization` only.** 401. Use `Authorization`.
