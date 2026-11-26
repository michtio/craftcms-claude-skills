# OAuth Authorization Server [5.12+]

Craft 5.12 ships an OAuth 2 authorization server (on `league/oauth2-server` ^9) that the authenticated MCP server, the GraphQL API and plugin APIs use. This file covers its keys, config, endpoints and token lifecycle. [5.12+]

Sources: [`src/services/OAuth.php`](https://github.com/craftcms/cms/blob/5.12.4/src/services/OAuth.php), [`src/controllers/OauthController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/controllers/OauthController.php), [`src/config/OAuthConfig.php`](https://github.com/craftcms/cms/blob/5.12.4/src/config/OAuthConfig.php), [`src/console/controllers/OauthController.php`](https://github.com/craftcms/cms/blob/5.12.4/src/console/controllers/OauthController.php). Docs: https://craftcms.com/docs/5.x/system/oauth.html

## Contents

- [Signing keys](#signing-keys) -- generate command, storage, env vars, what invalidates what
- [config/oauth.php](#configoauthphp) -- every key
- [Endpoints and metadata](#endpoints-and-metadata)
- [Dynamic client registration](#dynamic-client-registration)
- [Tokens: lifetimes, rotation, revocation](#tokens-lifetimes-rotation-revocation)
- [Rate limits](#rate-limits)
- [Common Pitfalls](#common-pitfalls)

## Signing Keys

```bash
ddev craft oauth/generate-keys            # writes storage/oauth-private.key + storage/oauth-public.key
ddev craft oauth/generate-keys --force    # replace them; invalidates every issued access token
```

- Generates a 4096-bit RSA pair (PKCS#8 `-----BEGIN PRIVATE KEY-----`), files `chmod 0600`. A second run without `--force` throws "OAuth keys already exist. Use --force to replace them and invalidate existing access tokens."
- The command always writes to `storage/`, whatever `privateKey`/`publicKey` say.
- Craft never generates keys during a web request. Until keys exist: the authenticated MCP server answers with an OAuth challenge and Settings → MCP explains the setup [5.12.1+], the Tokens screen is shown only to admins with setup instructions [5.12.1+], and token creation returns 400 [5.12.1+].
- `Craft::$app->getOAuth()->hasKeys()` [5.12.1+] reports whether valid keys are available.

### Keys as environment variables

`privateKey` and `publicKey` accept PEM contents, a file path, an alias or a `$ENV_VAR` reference, and can be set with `CRAFT_OAUTH_PRIVATE_KEY` / `CRAFT_OAUTH_PUBLIC_KEY`. Use this on every ephemeral, load-balanced or containerized host (Craft Cloud, Servd, Kubernetes) and wherever `storage/` isn't durable.

```php
<?php
// config/oauth.php (optional: the CRAFT_OAUTH_* env vars alone do the same)
// Return an array, not OAuthConfig::create([...]): see the warning below.
return [
    'privateKey' => '$OAUTH_PRIVATE_KEY',
    'publicKey' => '$OAUTH_PUBLIC_KEY',
];
```

**Return an array from `config/oauth.php`** [5.12+]. When the file returns an `OAuthConfig` object, Craft applies `CRAFT_OAUTH_*` overrides only through fluent setter methods, and `OAuthConfig` has none, so every `CRAFT_OAUTH_*` variable is silently ignored ([`Config::getConfigFromFile()`](https://github.com/craftcms/cms/blob/5.12.4/src/services/Config.php)). On an ephemeral host that surfaces as a missing `storage/oauth-private.key`; on a persistent host Craft quietly keeps using the old file keys. An array is merged with the env overrides as expected.

Value formats checked on 5.12.4 [5.12+]:

| Env var value | Works |
|---|---|
| Multiline PEM | Yes |
| One line, newlines replaced by spaces (how some dashboards flatten it) | Yes: Craft restores the line breaks |
| One line, all whitespace stripped (`-----BEGINPRIVATEKEY-----…`) | No |
| Literal `\n` escape sequences | No |

Generate the pair once locally, copy the file contents into the host's secret store, and keep the files out of git. Every server in one environment needs the same pair **and** the same `securityKey`. Use a different pair per environment, so a token from one environment can't validate against another after a database copy.

### What invalidates what

| Change | Access tokens | Refresh tokens and auth codes |
|---|---|---|
| New RSA pair (`--force`, new env var) | Invalid | Still valid, so clients refresh and carry on |
| New `securityKey` | Still valid until they expire | Invalid: the OAuth encryption key is `sha256("craft-oauth\0" . securityKey)` |

OAuth also refuses to run with an empty `securityKey`.

## config/oauth.php

`craft\config\OAuthConfig`, env prefix `CRAFT_OAUTH_`.

| Key | Default | Env var | Notes |
|---|---|---|---|
| `privateKey` | `null` (= `storage/oauth-private.key`) | `CRAFT_OAUTH_PRIVATE_KEY` (ignored if the file returns an `OAuthConfig` object) | PEM, path, alias or `$ENV` reference |
| `publicKey` | `null` (= `storage/oauth-public.key`) | `CRAFT_OAUTH_PUBLIC_KEY` | Same |
| `accessTokenDuration` | `'PT1H'` | `CRAFT_OAUTH_ACCESS_TOKEN_DURATION` | ISO 8601 interval string, not seconds |
| `refreshTokenDuration` | `'P30D'` | `CRAFT_OAUTH_REFRESH_TOKEN_DURATION` | Same |
| `authorizationCodeDuration` | `'PT10M'` | `CRAFT_OAUTH_AUTHORIZATION_CODE_DURATION` | Same |
| `redirectDomains` | `['*']` | array, not env-settable | Origins with optional path prefix, e.g. `'https://client.example'`. `*` allows any http(s) redirect. An `http://localhost` entry matches any port (loopback); `127.0.0.1` and `[::1]` need their own entries |
| `customSchemes` | `[]` | array | Extra redirect URI schemes for desktop apps; the URI still needs a host |
| `registrationRateLimit` | `10` (`int\|false`) | `CRAFT_OAUTH_REGISTRATION_RATE_LIMIT` | Client registrations per IP per window; `false` disables |
| `registrationRateLimitDuration` | `3600` (seconds) | `CRAFT_OAUTH_REGISTRATION_RATE_LIMIT_DURATION` | |
| `resources` | `[]` | array | Extra resource definitions keyed by ID (see `plugin-extension.md`) |

Production example, restricting redirects to loopback desktop clients and one web client you trust (replace the placeholder with the redirect origin your client registers):

```php
// config/oauth.php: an array, so CRAFT_OAUTH_* key variables still apply
return [
    'redirectDomains' => ['http://localhost', 'http://127.0.0.1', 'https://client.example'],
];
```

Check what your clients actually register (the consent screen shows the redirect host) before tightening; a client whose redirect isn't allowed fails at registration with `invalid_redirect_uri`.

## Endpoints and Metadata

- Resources: `mcp` (always), `graphql` (when `enableGql`), plus config and plugin resources. A scope belongs to exactly one resource, and a token is bound to a resource by its scopes.
- CP endpoints: `/{cpTrigger}/oauth/{resource}/register|authorize|approve|deny|token`. Front-end resources such as GraphQL are advertised as action URLs and never reveal the CP URL [changed 5.12.1].
- Metadata lives only at `.well-known` URLs: `/.well-known/oauth-protected-resource/<resource path>` and `/.well-known/oauth-authorization-server/<issuer path>`. For the default MCP setup: `/.well-known/oauth-protected-resource/admin/mcp/auth` and `/.well-known/oauth-authorization-server/admin/oauth/mcp`. The bare `/.well-known/oauth-*` paths are 404 by design.
- Subdirectory installs: forward `/.well-known/oauth-protected-resource/…` and `/.well-known/oauth-authorization-server/…` from the domain root to Craft. Web server rules that deny dotfiles must exempt `.well-known`.
- Grants: authorization code with PKCE (**S256 only**) and refresh token. Public clients only (`token_endpoint_auth_method: none`); no client credentials grant.
- `metadata`, `resource`, `register` and `token` work while the system is offline; `authorize`, `approve` and `deny` need it live.
- If a resource's `permissions` lack `accessCp`, users sign in through the front-end `loginPath`.
- The consent page can't be framed (`X-Frame-Options: DENY`, `frame-ancestors 'none'`).

## Dynamic Client Registration

`POST …/register` with JSON: `redirect_uris` (1 to 20, each checked against `redirectDomains`/`customSchemes`), optional `client_name` (1 to 64 visible characters, names confusable with "Craft", "Craft CMS", the system name or a site name are rejected as phishing look-alikes), `grant_types` within `authorization_code`/`refresh_token`, `response_types: ["code"]`. Registration grants nothing by itself. Clients that are never authorized are deleted by garbage collection.

## Tokens: Lifetimes, Rotation, Revocation

- Defaults: access 1 hour, refresh 30 days, code 10 minutes.
- Each refresh rotates both tokens and revokes the old ones; a refresh can narrow scopes, never add them.
- Every request re-checks the user (active, not suspended or locked) and the resource's required permissions, so suspending a user or removing a permission takes effect immediately.
- Users see and revoke authorized apps (MCP clients included) and personal access tokens on **My Account → Tokens**. There is no admin screen for other users' grants in 5.12.4. [5.12+]
- Tokens, clients and codes live in the `oauth_clients`, `oauth_access_tokens`, `oauth_auth_codes` and `oauth_refresh_tokens` tables, not project config. Garbage collection removes expired and revoked ones. A production database pulled into DDEV brings them along.

## Rate Limits

| Endpoint | Limit | Configurable |
|---|---|---|
| `register`, `authorize`, `token` | 60 requests per 60 s per IP | No (hard-coded in `OauthController`) |
| `register` additionally | `registrationRateLimit` per `registrationRateLimitDuration` (10 per hour) | Yes, `false` disables |

Over the limit the response is 429. Behind a proxy or CDN, set `trustedHosts` and `ipHeaders` or every client shares the proxy's bucket. Counters live in the data cache.

## Common Pitfalls

1. **Committing `storage/oauth-*.key`.** Check `.gitignore` covers `storage/`. Never paste the private key into a chat or a ticket.
2. **Mangled PEM in an env var.** Stripped whitespace and literal `\n` fail with "isn't a valid PEM-encoded key". Paste the multiline value, or replace newlines with spaces.
3. **Different keys or `securityKey` per server in one environment.** Tokens issued by one node fail on another. Share both across nodes.
4. **Durations as integers.** `accessTokenDuration` is a `DateInterval` string (`'PT2H'`), not `7200`.
5. **`redirectDomains` without the loopback origin.** Local clients such as Claude Code redirect to `http://localhost:<port>`; restricting the list without `http://localhost` breaks them.
