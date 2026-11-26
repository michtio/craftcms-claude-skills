# MCP Servers and Access [5.12+]

How Craft's three MCP servers are switched on, where they answer, who they act as, and what decides which capabilities a client sees. Everything here is Craft 5.12 or later. [5.12+]

Sources: [`src/mcp/Settings.php`](https://github.com/craftcms/cms/blob/5.12.4/src/mcp/Settings.php), [`src/services/Mcp.php`](https://github.com/craftcms/cms/blob/5.12.4/src/services/Mcp.php), [`src/mcp/CapabilityDiscovery.php`](https://github.com/craftcms/cms/blob/5.12.4/src/mcp/CapabilityDiscovery.php), [`src/controllers/McpController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/McpController.php), [`src/config/McpConfig.php`](https://github.com/craftcms/cms/blob/5.12.4/src/config/McpConfig.php). Docs: https://craftcms.com/docs/5.x/system/mcp.html

## Contents

- [The three servers](#the-three-servers) -- transports, identities, defaults
- [Endpoints and routing](#endpoints-and-routing) -- default paths, shared paths, CP access
- [Access levels](#access-levels) -- `mcp:read`, `mcp:write`, `mcp:admin`, consent
- [Capability gating](#capability-gating) -- the attributes and how scope is derived
- [Settings → MCP](#settings--mcp) -- who can save, project config, public approvals
- [config/mcp.php](#configmcpphp) -- `instructions`, `filters()`
- [Sessions, discovery and offline mode](#sessions-discovery-and-offline-mode)
- [Common Pitfalls](#common-pitfalls)

## The Three Servers

| | Authenticated | Public | stdio |
|---|---|---|---|
| Transport | Streamable HTTP (`POST`, `DELETE`, `OPTIONS`) | Streamable HTTP | stdin/stdout |
| Identity | The user who authorized the OAuth client | None | `--user` (ID, username or email) |
| Limit | User's permissions, capped by the token's access level | Only capabilities and content approved in Settings → MCP | User's permissions, no level cap |
| Switch | Settings → MCP → Authenticated (`mcp.enabled`) | Settings → MCP → Public (`mcp.publicEnabled`) | None: works with both switches off and no `config/mcp.php` |
| Capabilities | All except `#[PublicMcp]` ones | Only approved `#[PublicMcp]` ones | All except `#[PublicMcp]` and `#[RequiresHttp]` ones |

- Both HTTP servers are off by default.
- `craft mcp/serve` exits 64 (`USAGE`) without `--user`, and with `NOPERM` for an inactive, suspended or locked user. Its stdout is clean JSON-RPC, so `ddev craft mcp/serve --user=…` works as a stdio command.
- `mcp/serve` sees project config changes made by other processes [5.12.2+] and saves its own project config changes immediately [5.12.1+]. Before 5.12.2: restart it after editing project config elsewhere. Restart it after permission or instruction changes either way.

## Endpoints and Routing

| Setting (project config `mcp.*`) | Model default | Effective default |
|---|---|---|
| `route` (authenticated) | `/mcp` | `/{cpTrigger}/mcp` when a `cpTrigger` is set and public registration is off |
| `authorizationRoute` | `/mcp/auth` | `/{cpTrigger}/mcp/auth` under the same condition |
| `publicRoute` | `/mcp` | `/mcp` |

- Give clients the **authorization endpoint**. It always requires a bearer token, so an unauthenticated request gets a 401 with `WWW-Authenticate: Bearer resource_metadata="…/.well-known/oauth-protected-resource/admin/mcp/auth", scope="mcp:read mcp:write mcp:admin"`, which is how clients discover the OAuth server.
- An endpoint inside the CP (`/admin/…`) needs "Access the control panel": the request goes through the normal CP checks after the token authenticates. Turning on public registration moves the authenticated server to `/mcp`, so non-CP users can connect.
- When both servers share a path, a request goes to the authenticated server if it sends an `Authorization` header or is a `GET`; anything else goes to the public server. Separate paths are clearer.
- Path rules: non-empty `[a-zA-Z0-9_-]` segments, not starting with `actionTrigger` or `.well-known`, no clash with `config/routes.php` or CP-defined routes. The public route can't be inside the CP.
- A `GET` with `Accept: text/html` renders a setup page with copy-paste snippets for several clients; other `GET`s return 405.
- The authenticated server answers only at its own routes, never at an action URL.
- A CP on its own domain with no `cpTrigger` works for MCP sign-in [5.12.1+].

## Access Levels

The `mcp` OAuth resource defines three ordered scopes; each includes the narrower ones.

| Level (consent label) | Scope | Adds |
|---|---|---|
| Read only | `mcp:read` | Resources, prompts, tools with `readOnlyHint: true` |
| Read and write | `mcp:write` | Tools without `readOnlyHint: true` (create, update, delete) |
| Full access | `mcp:admin` | Tools marked `RequiresAdmin` or `RequiresAdminChanges`; offered to admins only |

- The level only narrows; the user's permissions still apply to every record.
- Re-authorizing while an unexpired grant exists skips the consent screen and keeps the earlier level. Clients send `prompt=consent` to choose again.
- Constants: `craft\services\Mcp::SCOPE_READ`, `SCOPE_WRITE`, `SCOPE_ADMIN`.

## Capability Gating

`CapabilityDiscovery` filters every tool, resource, resource template and prompt per request:

1. `#[PublicMcp]` capabilities are excluded from the authenticated and stdio servers.
2. `#[RequiresAdmin]`: user must be an admin. `#[RequiresAdminChanges]`: admin and `allowAdminChanges` on. `#[RequiresPermission('handle')]` (repeatable): `$user->can()` for each. No attribute: every user sees it, and the handler does record-level checks.
3. HTTP only: the token must grant the required scope. `RequiresAdmin`/`RequiresAdminChanges` need `mcp:admin`; a tool without `readOnlyHint: true` needs `mcp:write`; everything else needs `mcp:read`.
4. stdio only: `#[RequiresHttp]` capabilities are dropped (no core tool uses it in 5.12.4). [5.12+]
5. `Mcp::EVENT_DISCOVERING_CAPABILITY` lets plugins hide a capability per user (`$event->allowed = false`). It doesn't fire for the public server.

On production (`allowAdminChanges` off) every `RequiresAdminChanges` tool disappears, even for admins with Full access. See `tool-catalogue.md` for which tools those are.

MCP and OAuth aren't edition-gated, but public registration (which changes the default endpoint) and per-user permissions are Pro features.

## Settings → MCP

- Route `settings/mcp`, under the Settings page's new "Extend" section. Viewing needs an admin; **saving needs an admin and `allowAdminChanges`**. On production, configure locally and deploy `config/project/`.
- Saved to project config under `mcp` (`enabled`, `route`, `authorizationRoute`, `publicEnabled`, `publicRoute` and the public approvals), so the YAML must be committed. `ddev craft project-config/set mcp.enabled true` works too.
- The page explains missing or invalid OAuth keys [5.12.1+]. Before 5.12.1: the authenticated server returned a server error instead of an OAuth challenge when keys were missing.

### Public server approvals

| Setting | What it approves |
|---|---|
| `publicTools`, `publicResources`, `publicResourceTemplates`, `publicPrompts` | `#[PublicMcp]` capabilities. Core has two tools: `craft_context_get` and `craft_query` |
| `publicSiteHandles`, `publicSectionHandles`, `publicNestedEntryFieldHandles`, `publicVolumeHandles`, `publicUserGroupHandles`, `publicElementTypes` | Content the core public tools may return |
| `publicAllowDrafts`, `publicAllowRevisions`, `publicAllowInactive` | Element states, all `false` by default |

Empty lists expose nothing. `craft_query` returns 25 results by default, clamped to 100. Categories, tags and global sets aren't available via MCP. A plugin's approved `#[PublicMcp]` tool enforces its own restrictions and can leak data outside these approvals. Approvals were migrated to snake_case names automatically [changed 5.12.1].

## config/mcp.php

`craft\config\McpConfig`, env prefix `CRAFT_MCP_`.

| Key | Default | Notes |
|---|---|---|
| `instructions` | `''` | Appended to the instructions the `info_get` tool returns. `CRAFT_MCP_INSTRUCTIONS` |
| `filters` | `[]` | Yii action filters applied **only to the authenticated server** (each gets `only => ['authenticated']`). Fluent `->filters()` [5.12.1+]. Arrays aren't env-settable |

```php
<?php

use craft\config\McpConfig;
use yii\filters\RateLimiter;

return McpConfig::create()
    ->instructions('Follow the editorial style guide when changing article content.')
    ->filters([
        'rateLimiter' => [
            'class' => RateLimiter::class,
            'enableRateLimitHeaders' => false,
            // 300 requests per minute per IP; pick a number that fits your clients
            'user' => fn() => new \craft\filters\IpRateLimitIdentity([
                'keyPrefix' => 'mcp-authenticated',
                'limit' => 300,
                'window' => 60,
            ]),
        ],
    ]);
```

Set your own `limit` and `window`. Don't use `IpRateLimitIdentity::createDefault($key)` here: it takes `defaultRateLimit` per `defaultRateLimitDuration` (10 per 60 seconds by default), and one client's connect sequence (initialize, paginated `tools/list`, first calls) already sends several requests, so a working client gets 429s. `ip` defaults to the request's user IP, which is why `trustedHosts` and `ipHeaders` matter behind a proxy. The public server has no filter hook: throttle it at the web server or CDN.

Read the config with `Craft::$app->getConfig()->getMcp()`. The service has no `getMcp()` accessor on the app: use `Craft::$app->get('mcp')`.

## Sessions, Discovery and Offline Mode

- HTTP MCP sessions live in the data cache for an hour (`Mcp-Session-Id` header), keyed by server, user and scopes. Clearing caches makes clients initialize again. Multi-server setups need a shared cache or sticky sessions.
- `/.well-known/ai-catalog.json` and `<endpoint>/server-card` (SEP-2127) advertise the public server, and the authenticated server only when public registration is on. Servers on CP URLs are never advertised. The server card shows only the major Craft version. Both are rate-limited by `defaultRateLimit`.
- While the system is offline, `OPTIONS` and `GET` on the authenticated endpoint still answer; MCP calls need a user who may access the site or CP while it's off.

## Common Pitfalls

1. **Saving Settings → MCP on production.** Blocked without `allowAdminChanges`. Enable locally, commit `config/project/`, deploy.
2. **Assuming "disabled" covers stdio.** `mcp/serve` ignores `mcp.enabled`. Anyone with shell access can run it as any active user.
3. **A non-CP user can't connect.** The default authenticated endpoint lives in the CP. Grant CP access or move the routes outside the CP.
4. **Expecting `filters` to protect the public server.** They only apply to the authenticated action.
5. **Clients that never see `elements_list`.** `tools/list` is paginated (50 per page); a client that ignores `nextCursor` misses half the catalogue.
