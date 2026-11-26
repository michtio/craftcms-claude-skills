---
name: craft-mcp
description: "Craft CMS 5.12+ MCP servers, OAuth server and personal access tokens: authenticated, public and stdio (mcp/serve) servers, mcp:read/write/admin levels, Settings → MCP, config/mcp.php and config/oauth.php, oauth/generate-keys and CRAFT_OAUTH_PRIVATE_KEY/PUBLIC_KEY on DDEV, production, Cloud, Servd and fortrabbit, connecting Claude Code or another client, the snake_case tool catalogue, and plugin MCP tools, field interfaces and OAuth resources."
when_to_use: "Triggers on: Craft MCP server, connect Claude Code or an AI assistant to Craft, claude mcp add, /admin/mcp/auth, mcp/serve, oauth/generate-keys, CRAFT_OAUTH_PRIVATE_KEY, config/mcp.php, config/oauth.php, redirectDomains, public MCP server, personal access token, My Account → Tokens, elements_list, craft_query, register an MCP tool from a plugin, McpTool, EVENT_REGISTER_CAPABILITY_TYPES, InputSchemaFieldInterface, McpOutputFieldInterface, OAuth resource. Do NOT trigger for Chrome DevTools or other non-Craft MCP servers, GraphQL schema tokens, Cloud or Servd deploys without MCP, or plain plugin controller auth."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft MCP, OAuth Server and Personal Access Tokens

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.12+]`, `[5.12.1+]`, `[changed 5.12.1]`).

## MCP Needs Craft 5.12 [5.12+]

Everything in this skill is new in Craft 5.12 (2026-11-03). On 5.11 or older there is no MCP server, OAuth server or Tokens screen in core. Before 5.12: upgrade first (`ddev composer require craftcms/cms:^5.12.4 -W`, then `ddev craft up`, commit `composer.lock` and `config/project/`; checklist: the `craftcms` skill's `upgrade-5.12.md`). Target 5.12.4 or later, not 5.12.0: 5.12.1 renamed every tool to snake_case and 5.12.1 through 5.12.3 fixed several security issues (see `references/security.md`). [5.12+]

Source of truth: Craft's CHANGELOG and the 5.12.4 source (`src/mcp/`, `src/services/Mcp.php`, `src/services/OAuth.php`, `src/controllers/McpController.php`, `src/controllers/OauthController.php`). Craft's own docs pages still show the pre-5.12.1 dot-separated tool names; the source wins. [5.12+]

## Companion Skills: Load When Needed

- **`craftcms`**: Plugin or module PHP around an MCP capability (services, permissions, controllers), GraphQL OAuth details in `references/graphql.md`, config files in `references/config-*.md`.
- **`craft-php-guidelines`**: Whenever you write the PHP for an MCP tool, field interface or OAuth resource.
- **`ddev`**: Local environment; the stdio server runs through `ddev craft`.
- **`craft-cloud`**, **`servd`**, **`craft-fortrabbit`**: host-specific env var and filesystem handling for the signing keys.
- **`craft-content-modeling`**: When an MCP client is used to author sections, fields or entry types (project config workflow still applies).

## Documentation

- MCP: https://craftcms.com/docs/5.x/system/mcp.html
- Extending MCP: https://craftcms.com/docs/5.x/extend/mcp.html
- OAuth and personal access tokens: https://craftcms.com/docs/5.x/system/oauth.html
- Source: https://github.com/craftcms/cms/tree/5.12.4/src/mcp

## The Three Servers at a Glance [5.12+]

| Server | Transport | Who it acts as | Default endpoint | Default state |
|---|---|---|---|---|
| Authenticated | Streamable HTTP | The user who authorized the client via OAuth, capped by the access level they chose | `/{cpTrigger}/mcp` + `/{cpTrigger}/mcp/auth`; `/mcp` + `/mcp/auth` when public registration is on or `cpTrigger` is empty | Off |
| Public | Streamable HTTP | Nobody; only capabilities and content approved in Settings → MCP | `/mcp` | Off |
| stdio | `craft mcp/serve --user=<id\|username\|email>` | The named user, no access-level cap | n/a | Always available, ignores both switches |

Clients connect to the **authorization endpoint** (`…/mcp/auth`). Settings live in project config under `mcp`; saving Settings → MCP needs an admin and `allowAdminChanges`. Details: `references/servers-and-access.md`.

## Quick Recipe: Claude Code on a Local DDEV Site [5.12+]

```bash
ddev craft oauth/generate-keys                     # once per checkout; writes storage/oauth-*.key
# CP → Settings → MCP → enable the authenticated server, save, commit config/project/
claude mcp add --transport http my-site https://my-site.ddev.site/admin/mcp/auth
# in Claude Code: /mcp → authenticate → browser: CP login, pick Read only / Read and write / Full access
```

`ddev share` hosts are rejected (403 "Invalid Host header") unless they are also a site base URL. A personal access token cannot carry MCP scopes; use OAuth or stdio. Full recipes (stdio, TLS trust, production, Cloud/Servd/fortrabbit): `references/client-setup.md`.

## Common Pitfalls (Cross-Cutting)

- **Recommending MCP on a pre-5.12 site.** There is nothing to enable. Give the upgrade path above.
- **Dotted tool names.** Since 5.12.1 core tools are snake_case (`elements_list`, not the old dot-separated form) and plugin tools should be too, prefixed with the plugin handle: `my_plugin_orders_list`. Some clients reject dots. [changed 5.12.1]
- **Pointing a client at `/admin/mcp` instead of `/admin/mcp/auth`.** Use the authorization endpoint; opening either in a browser shows copy-paste setup snippets.
- **Using a personal access token for MCP.** The `mcp` scope group offers no grantable scopes, so `create()` throws "Invalid scopes" even for admins, and a GraphQL PAT sent to the MCP endpoint gets a 401. PATs are for GraphQL and plugin APIs. See `references/personal-access-tokens.md`.
- **Keys in `storage/` on an ephemeral or load-balanced host.** Set `CRAFT_OAUTH_PRIVATE_KEY` and `CRAFT_OAUTH_PUBLIC_KEY` instead (multiline PEM, or newlines replaced by spaces; never stripped whitespace or literal `\n`). See `references/oauth-server.md`.
- **Rotating `securityKey`.** It derives the OAuth encryption key: refresh tokens and pending auth codes die, every client must authorize again. Regenerating the RSA keys kills access tokens only.
- **Expecting schema tools on production.** Tools marked `RequiresAdminChanges` (configuration writes, plugin install, project config apply/write, field layout updates, group permissions) disappear when `allowAdminChanges` is off. Make schema changes in dev and deploy project config.
- **Treating stdio as scoped.** `mcp/serve` skips the enable switches and OAuth access levels and gets everything the named user can do. Run it as a least-privileged user. [5.12+]
- **Stopping at the first page of `tools/list`.** Over stdio as an admin, 5.12.4 returns 69 tools in two pages (50 + cursor); `elements_*` are on page 2. [5.12+]
- **A plugin tool without `readOnlyHint: true`.** It then requires `mcp:write` and is hidden from Read-only clients. A duplicate tool name throws a `LogicException` that breaks discovery for every user. See `references/plugin-extension.md`.
- **Leaving `redirectDomains` at `['*']` on production.** Restrict it to the clients you expect, keeping `http://localhost` for local desktop clients. See `references/security.md`.

## Reference Files

**Task examples:**

- "Connect Claude Code to my Craft site over MCP" → `client-setup.md`
- "Expose our blog to any AI agent without login" → `servers-and-access.md` + `security.md`
- "Deploy MCP to Craft Cloud / Servd / fortrabbit" → `client-setup.md` + `oauth-server.md`
- "Why does MCP return 401 / 404 / 403?" → `client-setup.md` (troubleshooting)
- "Which tools can the client use, and why is X missing?" → `tool-catalogue.md`
- "Let a script call GraphQL as an editor" → `personal-access-tokens.md`
- "Register an MCP tool from my plugin" → `plugin-extension.md`
- "Make my custom field work with MCP" → `plugin-extension.md`
- "Protect my plugin's API with Craft's OAuth server" → `plugin-extension.md` + `oauth-server.md`
- "Rate-limit the MCP endpoint" → `servers-and-access.md` (`filters`) + `security.md`

| Reference | Scope | ~Lines |
|---|---|---:|
| `references/servers-and-access.md` | The three servers, routing and endpoints, access levels and gating attributes, Settings → MCP and public approvals, `config/mcp.php` (`instructions`, `filters`), sessions, discovery | ~135 |
| `references/oauth-server.md` | Signing keys and the generate command, env vars, `config/oauth.php` keys, endpoints and metadata, dynamic client registration, lifetimes, rotation, revocation, rate limits | ~130 |
| `references/personal-access-tokens.md` | Tokens screen and its gating, elevated session, expirations, scopes, using a PAT with GraphQL, programmatic creation | ~75 |
| `references/client-setup.md` | Claude Code over HTTP on DDEV, TLS trust, stdio via `ddev craft mcp/serve`, production checklist, Craft Cloud / Servd / fortrabbit keys, troubleshooting [5.12+] | ~100 |
| `references/tool-catalogue.md` | Every tool, resource and prompt in 5.12.4 with its scope and gating, upload tools, permission tools, `expectedRevision` [5.12+] | ~170 |
| `references/plugin-extension.md` | Registering capabilities, attribute signatures, naming, scopes, hiding per user, `InputSchemaFieldInterface`, `McpOutputFieldInterface`, OAuth resources, PAT scope groups, other hooks [5.12+] | ~270 |
| `references/security.md` | What each server exposes, production hardening, rate limits, `redirectDomains`, revocation, the 5.12.x advisories [5.12+] | ~75 |
