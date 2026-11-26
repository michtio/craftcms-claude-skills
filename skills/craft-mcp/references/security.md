# MCP and OAuth Security [5.12+]

What turning on Craft's MCP servers exposes, how to harden a production site, and the security fixes in the 5.12 patch releases. [5.12+]

Sources: [`src/mcp/CapabilityDiscovery.php`](https://github.com/craftcms/cms/blob/5.12.4/src/mcp/CapabilityDiscovery.php), [`src/controllers/McpController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/McpController.php), [`src/controllers/OauthController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/OauthController.php), [`src/console/controllers/McpController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/console/controllers/McpController.php), Craft's CHANGELOG.

## What Each Server Exposes

| Server | A connected client can |
|---|---|
| Authenticated | Everything the authorizing user can do, within the level they chose. An admin with Full access on an environment with `allowAdminChanges` on can install and uninstall plugins, apply, write or rebuild project config, take the system offline, edit sections and fields, and change group permissions |
| stdio (`mcp/serve`) | Everything the `--user` can do, with no level cap, and regardless of the Settings → MCP switches. Anyone who can run console commands can start it as any active user |
| Public | Only the approved `#[PublicMcp]` tools and the approved sites, sections, volumes, user groups and element types; drafts, revisions and disabled elements off unless approved. A plugin's public tool can return data outside these approvals |

An MCP client is an automated agent acting with a real user's authority; prompt-injected content (an entry body, an uploaded file name) can steer it. Treat write and admin levels as you would handing someone that user's session.

## Production Hardening

1. Keep `allowAdminChanges` off in production: every `RequiresAdminChanges` tool disappears, even for admins.
2. Recommend Read only or Read and write for day-to-day clients; Full access only when needed.
3. For stdio, use a dedicated least-privileged user, not an admin.
4. Restrict `redirectDomains` in `config/oauth.php` to the clients you expect, keeping `http://localhost` (and `http://127.0.0.1` if a client uses it) for desktop clients. The default `['*']` lets any registered client redirect anywhere; PKCE and the consent screen (which shows the redirect host) mitigate but don't remove phishing risk.
5. Rate-limit the authenticated endpoint with `config/mcp.php` `filters` (`servers-and-access.md`). The public endpoint has no Craft-level limit or filter hook: throttle it at the web server, CDN or WAF.
6. Behind proxies, set `trustedHosts` and `ipHeaders` so rate limits count per client.
7. Keep signing keys in env vars or files outside the web root and git, with a separate pair per environment. Keep `securityKey` stable and secret.
8. Only enable the public server when you've decided exactly which content is public; empty approvals expose nothing.
9. Run 5.12.4 or later (below). [5.12+]

## Rate Limits

| What | Limit | Source |
|---|---|---|
| `mcp/catalog`, `mcp/server-card` (discovery) | `defaultRateLimit` per `defaultRateLimitDuration` (10 per 60 s), per IP | `McpController::behaviors()` |
| Authenticated MCP endpoint | None by default; add via `config/mcp.php` `filters` | |
| Public MCP endpoint | None, no hook | |
| OAuth `register`, `authorize`, `token` | 60 per 60 s per IP, fixed | `OauthController::behaviors()` |
| OAuth `register` | `registrationRateLimit` per `registrationRateLimitDuration` (10 per hour) | `config/oauth.php` |
| `users/login` (POST), `users/send-password-reset-email`, `auth/verify-totp`, `auth/verify-recovery-code` | `defaultRateLimit` per `defaultRateLimitDuration` | `config/general.php` |

`false` disables `defaultRateLimit` or `registrationRateLimit`. Over a limit Craft answers 429. Counters live in the data cache.

## Revocation

- Users revoke authorized apps (MCP clients) and PATs on My Account → Tokens. Revoking an app revokes its access and refresh tokens.
- Suspending a user, locking them, or removing a permission a resource requires takes effect on the next request.
- No admin UI in 5.12.4 revokes other users' grants. To cut everyone off at once: rotate the RSA pair (kills access tokens) **and** `securityKey` (kills refresh tokens and auth codes; also every session and encrypted value, so plan it), or revoke rows in the `oauth_*` tables. [5.12+]
- Disabling the authenticated server in Settings → MCP makes its endpoint 404, but doesn't stop `mcp/serve`.

## Security Fixes in 5.12.x [5.12+]

The CHANGELOG names these without detail; until the advisories are published, reference them by ID and severity only.

| Release | Advisory | Severity, type |
|---|---|---|
| 5.12.0 [5.12+] | GHSA-hgwm-4xxx-w8jq | Moderate, information disclosure |
| 5.12.0 [5.12+] | GHSA-vvm6-wrc8-5fgh | Moderate, authorization bypass |
| 5.12.1 [5.12.1+] | GHSA-pcf5-h66c-9wxw | Web installer restricted to Dev Mode; install with `craft install` otherwise (severity not stated) |
| 5.12.2 [5.12.2+] | GHSA-24vg-rp56-rf5c | Low, authorization bypass |
| 5.12.2 [5.12.2+] | GHSA-53c3-ggrg-m3hg | Moderate, SSRF |
| 5.12.2 [5.12.2+] | GHSA-r4pw-6wr6-6rm8 | Moderate, authorization bypass |
| 5.12.2 [5.12.2+] | GHSA-2xwp-6jjc-hfmm | Moderate, RCE |
| 5.12.3 [5.12.3+] | (no ID published) | Low, sandboxed templates could replace `Twig\Markup` content |
| 5.12.3 [5.12.3+] | (no ID published) | Low, authorization bypass |

Which of these touch MCP or OAuth isn't stated. The 5.12.1 changes that are MCP-relevant and public: field values on nested entries, Content Block fields and addresses now respect field layout conditions on save, and the MCP permission tools reject unknown permissions [changed 5.12.1]. Advise any site exposing MCP to run 5.12.4 or later.

## Common Pitfalls

1. **"MCP is disabled, so we're safe."** stdio ignores the switch; restrict shell access.
2. **Full access as the default.** Pick the narrowest level; the consent screen preselects Read only for a reason.
3. **Public server without an edge limit.** Craft won't throttle it.
4. **`redirectDomains` left at `['*']` on a site with sensitive content.** Restrict it.
5. **Copying a production database (with `oauth_*` tables) to a box with the same keys and `securityKey`.** Production tokens would then validate there. Use per-environment keys.
