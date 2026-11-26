# Client Setup Recipes [5.12+]

Connecting an MCP client to Craft: Claude Code over HTTP against a local DDEV site, the stdio alternative, production, and the hosting-specific key handling for Craft Cloud, Servd and fortrabbit. Every step needs Craft 5.12 or later; target 5.12.4. [5.12+]

Sources: [`src/controllers/McpController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/McpController.php), [`src/mcp/HttpTransportMiddleware.php`](https://github.com/craftcms/cms/blob/5.12.4/src/mcp/HttpTransportMiddleware.php), [`src/console/controllers/McpController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/console/controllers/McpController.php), [`src/templates/mcp/_endpoint.twig`](https://github.com/craftcms/cms/blob/5.12.4/src/templates/mcp/_endpoint.twig). Claude Code: https://code.claude.com/docs/en/mcp and https://code.claude.com/docs/en/network-config

## Contents

- [Claude Code over HTTP on DDEV](#claude-code-over-http-on-ddev)
- [TLS trust for mkcert certificates](#tls-trust-for-mkcert-certificates)
- [stdio via ddev craft mcp/serve](#stdio-via-ddev-craft-mcpserve)
- [Other clients](#other-clients)
- [Production](#production)
- [Craft Cloud, Servd, fortrabbit](#craft-cloud-servd-fortrabbit)
- [Troubleshooting](#troubleshooting)

## Claude Code over HTTP on DDEV

1. **Keys**, once per checkout: `ddev craft oauth/generate-keys` (writes `storage/oauth-*.key`; keep them out of git).
2. **Enable** the authenticated server: CP → Settings → MCP → Authenticated → on, save (needs an admin and `allowAdminChanges`, normally on locally). Or `ddev craft project-config/set mcp.enabled true`. Commit the `config/project/` change so other environments get it.
3. **Endpoint**: the authorization endpoint, by default `https://<project>.ddev.site/admin/mcp/auth` (`/mcp/auth` when public registration is on or `cpTrigger` is empty). Opening it in a browser shows the exact snippet for this site.
4. **Add it** to Claude Code:

   ```bash
   claude mcp add --transport http my-site https://my-site.ddev.site/admin/mcp/auth
   # --scope project writes .mcp.json for the team; the default (local) is just you
   ```

5. **Authorize**: in Claude Code run `/mcp`, pick the server, authenticate. The browser opens Craft's login (2FA applies), then the consent screen; pick Read only, Read and write, or Full access (admins). Claude Code receives the code on its `http://localhost` loopback redirect, which the default `redirectDomains` allows. `claude mcp login my-site` does the same from the shell.

The user needs "Access the control panel" for the default CP endpoint. Tools appear per that user's permissions and the chosen level (`tool-catalogue.md`).

**`ddev share` doesn't work** for this: the transport only accepts the hosts of the CP URL, `baseCpUrl`, the site base URLs, and `localhost`/`127.0.0.1`/`[::1]`. A tunnel host gets 403 "Forbidden: Invalid Host header" unless you add it as a site base URL. CORS origins are limited to the same list.

## TLS Trust for mkcert Certificates

DDEV serves HTTPS with a mkcert CA that `mkcert -install` puts in the OS trust store. Claude Code trusts the OS store by default when its runtime can read it: always with the native installer, and on npm installs with Node 22.15 or later. Otherwise point it at the CA before launching Claude Code:

```bash
export NODE_EXTRA_CA_CERTS="$(mkcert -CAROOT)/rootCA.pem"
```

Claude Code applies its CA settings to MCP sign-in requests (network-config docs). For `claude mcp login`, set the variable in the shell or `~/.claude/settings.json`, not project settings.

## stdio via ddev craft mcp/serve

No OAuth, no keys, no Settings → MCP switch:

```bash
claude mcp add my-site-stdio -- ddev craft mcp/serve --user=editor
```

- Run Claude Code from the project directory so `ddev` finds the project. `ddev exec php craft mcp/serve --user=editor` is equivalent.
- `--user` takes an ID, username or email and is required. The user must be active and not suspended or locked.
- No access-level cap: the client gets everything that user can do, including `RequiresAdmin` tools for an admin. Prefer a non-admin user created for the purpose.
- `#[RequiresHttp]` capabilities are omitted (none in core). Local file paths work in `assets_create` / `assets_replace` over stdio only [5.12.1+]; `assets_upload_url` over stdio builds URLs from the site's base URL, which must be absolute [5.12.1+].
- Restart the server after changing the user's permissions or `config/mcp.php` instructions.

## Other Clients

Opening the endpoint in a browser lists copy-paste setup for Claude Code, Codex, Gemini CLI, Cursor, Claude and VS Code. Any client that supports Streamable HTTP plus OAuth discovery, dynamic client registration and PKCE S256 can connect; clients that need a client secret or a client credentials grant can't.

## Production

1. **Keys** on every node: `CRAFT_OAUTH_PRIVATE_KEY` / `CRAFT_OAUTH_PUBLIC_KEY`, or the same key files deployed to each node. Same `CRAFT_SECURITY_KEY` on every node. A separate pair per environment.
2. **Enable in dev, deploy project config**: Settings → MCP can't be saved with `allowAdminChanges` off.
3. **HTTPS**, and give clients `https://<host>/admin/mcp/auth`.
4. **`Authorization` must reach PHP.** Apache/FastCGI often strip it: `CGIPassAuth On` or a rewrite rule. Without it every call is a 401.
5. **`.well-known/oauth-*` must reach Craft**: don't block dotfiles there; forward from the domain root for subdirectory installs.
6. **Proxies/CDNs**: set `trustedHosts` and `ipHeaders` so rate limits count per client. Craft checks the host it resolved (honouring `X-Forwarded-Host` from trusted proxies), not the raw `Host`.
7. **Shared cache** (Redis or DB) for multi-node: MCP sessions and rate-limit counters live in the data cache.
8. **Expect fewer tools**: `RequiresAdminChanges` tools are gone with `allowAdminChanges` off. That's intended.
9. **Restrict `redirectDomains`** to the clients you expect (keep `http://localhost` for desktop clients). See `security.md`.

## Craft Cloud, Servd, fortrabbit

| Host | Keys | Notes |
|---|---|---|
| Craft Cloud | Env vars `CRAFT_OAUTH_PRIVATE_KEY` / `CRAFT_OAUTH_PUBLIC_KEY` in Console | `storage/` is ephemeral. Env var changes apply on the next deployment. Craft's host check is written with Cloud's gateway in mind. Not verified on Cloud: that the edge forwards `/.well-known/oauth-*` to Craft and never caches the public `/mcp` path; test a client sign-in on a preview environment and see `craft-cloud` for cache rules |
| Servd | Env vars per environment | `storage/` resets and isn't shared between instances. The data cache is Redis, so MCP sessions survive across instances |
| fortrabbit | ENV vars (preferred), or `php craft oauth/generate-keys` over SSH | Persistent storage keeps `storage/` across deployments with the merge strategy; ENV vars survive any strategy |

Generate the pair locally (`ddev craft oauth/generate-keys` in a scratch checkout, or `openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096` plus `openssl pkey -pubout`) and paste each file's contents. Multiline is best; a single line only works with newlines turned into spaces.

## Troubleshooting

| Symptom | Cause |
|---|---|
| 404 on `/mcp` | Authenticated server lives at `/admin/mcp` (a `cpTrigger` is set and public registration is off), or the server is disabled |
| 401 `invalid_token` on every call | No or expired token, `Authorization` stripped by the web server, a PAT used for MCP, or the token was issued with a different key pair |
| "The OAuth private key file … doesn't exist" / "isn't a valid PEM-encoded key" | Keys missing or mangled; see `oauth-server.md` |
| 403 "Invalid Host header" | Tunnel or proxy host not among the CP/site URLs |
| 405 on `GET` | Normal: only `POST`, `DELETE`, `OPTIONS`; a browser `GET` gets the setup page |
| 429 during sign-in | OAuth's 60/60 s or registration limit; behind a proxy, fix `ipHeaders` |
| Client sees no `elements_*` tools | It ignored `nextCursor`; `tools/list` is paginated |
| Schema or plugin tools missing | `allowAdminChanges` off, user isn't admin, or the level isn't Full access |
| Old notes use dot-separated tool names | Renamed to snake_case [changed 5.12.1]; reconnect so the client reloads the list |
